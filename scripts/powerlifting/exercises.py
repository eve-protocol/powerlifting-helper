"""Shared exercise taxonomy and unit helpers."""

LBS_TO_KG = 0.453592


def is_failed_set(set_data):
    """Return True when Boostcamp marks the set as a failed attempt."""
    return set_data.get('setStatus') == 'failure'


def get_completed_reps(set_data):
    """Return completed reps for a set.

    Boostcamp can mark partial attempts with ``setStatus='failure'`` while still
    storing the actually completed reps in ``archived_reps``. We use that field
    for display so failed attempts can still show the actual bar weight/reps that
    happened, while success-based analytics can exclude those sets separately.
    """
    archived_reps = set_data.get('archived_reps')
    if archived_reps not in (None, ''):
        return archived_reps
    return set_data.get('amount', 0)


def get_logged_rpe(set_data):
    """Return the RPE actually logged for this set.

    Important: do not fall back to ``previous_rpe``.
    Boostcamp carries that field forward as UI convenience/history, but it is not
    evidence that the current set was rated. We only surface a set RPE when the
    set itself has an explicit non-zero RPE entry.
    """
    for key in ('archived_rpe', 'rpe'):
        value = set_data.get(key)
        if value in (None, '', 0, '0'):
            continue
        return value
    return None


def get_logged_weight_kg(set_data, rounding=0.5):
    """Return the logged set weight in kg from archived source-of-truth data."""
    return lbs_to_kg(set_data.get('archived_weight'), rounding=rounding)

EXERCISE_FAMILY_MAP = {
    # squat family
    'Squat (Low Bar)': 'squat',
    'Squat (Paused)': 'squat',
    'High Bar Squat (Barbell)': 'squat',
    'Tempo Squat (Barbell)': 'squat',
    'Tempo Squat High Bar (Barbell)': 'squat',
    'Box Squat (Barbell)': 'squat',
    # bench family
    'Bench Press (Barbell)': 'bench',
    'Bench Press (Paused)': 'bench',
    'Bench Press (Close Grip)': 'bench',
    'Bench Press (Smith Machine)': 'bench',
    'Larsen Press (Barbell)': 'bench',
    'Spoto Press': 'bench',
    'Incline Bench Press (Dumbbell)': 'bench',
    'Incline Bench Press (Smith Machine)': 'bench',
    # deadlift family
    'Deadlift (Barbell)': 'deadlift',
    'Deadlift (Paused)': 'deadlift',
    'Deadlift (Deficit)': 'deadlift',
    'Block Pull (Barbell)': 'deadlift',
    'Sumo Deadlift (Barbell)': 'deadlift',
    'Sumo Deadlift (Paused)': 'deadlift',
    'Sumo Deadlift (Paused at Knee)': 'deadlift',
    'Sumo Deadlift (Banded)': 'deadlift',
    'Romanian Deadlift (Barbell)': 'deadlift',
    'Sumo Romanian Deadlift': 'deadlift',
}

MAIN_LIFT_VARIATIONS = {
    'squat': {
        'Squat (Low Bar)', 'Squat (Paused)', 'High Bar Squat (Barbell)',
        'Tempo Squat (Barbell)', 'Tempo Squat High Bar (Barbell)', 'Box Squat (Barbell)',
    },
    'bench': {
        'Bench Press (Barbell)', 'Bench Press (Paused)', 'Bench Press (Close Grip)',
        'Larsen Press (Barbell)', 'Spoto Press', 'Incline Bench Press (Dumbbell)',
        'Incline Bench Press (Smith Machine)', 'Bench Press (Smith Machine)',
    },
    'deadlift': {
        'Deadlift (Barbell)', 'Deadlift (Paused)', 'Deadlift (Deficit)',
        'Block Pull (Barbell)', 'Sumo Deadlift (Barbell)', 'Sumo Deadlift (Paused)',
        'Sumo Deadlift (Paused at Knee)', 'Sumo Deadlift (Banded)',
        'Romanian Deadlift (Barbell)', 'Sumo Romanian Deadlift',
    },
}

TRACKED_BODYWEIGHT_TIMELINE_EXERCISES = {
    'Squat (Low Bar)',
    'Bench Press (Barbell)',
    'Bench Press (Paused)',
    'Sumo Deadlift (Barbell)',
    'Sumo Deadlift (Paused)',
    'Sumo Deadlift (Paused at Knee)',
}

FAMILY_PATTERN_HINTS = {
    'squat': ('squat',),
    'bench': ('bench',),
    'deadlift': ('deadlift',),
}


def lbs_to_kg(lbs, rounding=0.5):
    """Convert pounds to kg, rounded to the nearest increment."""
    if lbs is None or lbs == 0:
        return 0
    kg = float(lbs) * LBS_TO_KG
    if not rounding:
        return kg
    return round(kg / rounding) * rounding


def get_exercise_family(exercise_name):
    """Return the canonical family for an exercise name, if known."""
    return EXERCISE_FAMILY_MAP.get(exercise_name)


def classify_family(exercise_name):
    """Return a family using exact matches first, then simple substring fallbacks."""
    family = get_exercise_family(exercise_name)
    if family:
        return family

    name_lower = exercise_name.lower()
    for candidate, patterns in FAMILY_PATTERN_HINTS.items():
        if any(pattern in name_lower for pattern in patterns):
            return candidate
    return None
