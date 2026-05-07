"""Training stress score helpers.

The stress score is intentionally a trend metric, not a physiological truth:

    reps * weight_kg * intensity^2 * rpe_factor

Intensity is based on actual successful singles, not e1RM.
"""

from bisect import bisect_right
from collections import defaultdict

from .exercises import (
    MAIN_LIFT_VARIATIONS,
    get_completed_reps,
    get_exercise_family,
    get_logged_rpe,
    get_logged_weight_kg,
    is_failed_set,
    lbs_to_kg,
)

RPE_FACTOR_POINTS = (
    (5.0, 0.50),
    (6.0, 0.65),
    (7.0, 0.80),
    (8.0, 1.00),
    (9.0, 1.20),
    (10.0, 1.50),
)


def as_float(value):
    if value in (None, '', '-', 0, '0'):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rpe_factor(rpe):
    """Return the RPE multiplier, interpolating between anchor points."""
    value = as_float(rpe)
    if value is None:
        return None

    if value <= RPE_FACTOR_POINTS[0][0]:
        return RPE_FACTOR_POINTS[0][1]
    if value >= RPE_FACTOR_POINTS[-1][0]:
        return RPE_FACTOR_POINTS[-1][1]

    for (low_rpe, low_factor), (high_rpe, high_factor) in zip(RPE_FACTOR_POINTS, RPE_FACTOR_POINTS[1:]):
        if low_rpe <= value <= high_rpe:
            span = high_rpe - low_rpe
            progress = (value - low_rpe) / span
            return low_factor + progress * (high_factor - low_factor)

    return None


def target_rpe_value(set_data):
    """Return the intended RPE for a set, using the midpoint for a target range."""
    intensity = set_data.get('intensity')
    unit = str(set_data.get('intensity_unit') or '').lower()
    if 'rpe' not in unit:
        return None

    if isinstance(intensity, (list, tuple)) and intensity:
        values = [as_float(v) for v in intensity]
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else None

    return as_float(intensity)


def target_reps_value(set_data):
    reps = set_data.get('target')
    if reps in (None, ''):
        reps = get_completed_reps(set_data)
    try:
        return int(float(reps))
    except (TypeError, ValueError):
        return None


def target_weight_kg(set_data, fallback_weight_kg):
    target_weight = set_data.get('target_weight')
    if target_weight:
        converted = lbs_to_kg(target_weight, rounding=0.5)
        if converted:
            return converted
    return fallback_weight_kg


def compute_stress_score(weight_kg, reps, rpe, reference_max_kg):
    weight = as_float(weight_kg)
    reps_value = as_float(reps)
    ref = as_float(reference_max_kg)
    factor = rpe_factor(rpe)
    if not weight or not reps_value or not ref or not factor:
        return None

    intensity = weight / ref
    return weight * reps_value * (intensity ** 2) * factor


def format_stress_score(score):
    if score is None:
        return '-'
    return str(int(round(score)))


class ActualSingleReferenceResolver:
    """Resolve rolling family reference maxes from successful actual singles."""

    def __init__(self, workouts):
        dated_singles = defaultdict(list)
        all_time_best = defaultdict(float)

        for workout in workouts:
            date = workout.get('date')
            if not date:
                continue
            for record in workout.get('records', []):
                exercise_name = record.get('name', 'Unknown')
                family = get_exercise_family(exercise_name)
                if not family or exercise_name not in MAIN_LIFT_VARIATIONS[family]:
                    continue
                for set_data in record.get('sets', []):
                    if set_data.get('skipped', False) or is_failed_set(set_data):
                        continue
                    reps = target_reps_value({'target': get_completed_reps(set_data)})
                    if reps != 1:
                        continue
                    weight_kg = get_logged_weight_kg(set_data, rounding=0.5)
                    if not weight_kg:
                        continue
                    dated_singles[family].append((date, weight_kg))
                    all_time_best[family] = max(all_time_best[family], weight_kg)

        self._dates = {}
        self._bests = {}
        self._fallback = dict(all_time_best)
        for family, singles in dated_singles.items():
            current_best = 0
            dates = []
            bests = []
            for date, weight_kg in sorted(singles):
                current_best = max(current_best, weight_kg)
                dates.append(date)
                bests.append(current_best)
            self._dates[family] = dates
            self._bests[family] = bests

    def get(self, family, date):
        dates = self._dates.get(family, [])
        bests = self._bests.get(family, [])
        idx = bisect_right(dates, date) - 1
        if idx >= 0:
            return bests[idx]
        return self._fallback.get(family)


def score_set_stress(set_data, family, date, reference_resolver, rounding=0.5):
    reference_max_kg = reference_resolver.get(family, date)
    actual_weight_kg = get_logged_weight_kg(set_data, rounding=rounding)
    actual_reps = get_completed_reps(set_data)
    actual_rpe = get_logged_rpe(set_data)

    planned_weight_kg = target_weight_kg(set_data, actual_weight_kg)
    planned_reps = target_reps_value(set_data)
    planned_rpe = target_rpe_value(set_data)

    return {
        'reference_max_kg': reference_max_kg,
        'estimated_stress': compute_stress_score(planned_weight_kg, planned_reps, planned_rpe, reference_max_kg),
        'real_stress': compute_stress_score(actual_weight_kg, actual_reps, actual_rpe, reference_max_kg),
    }
