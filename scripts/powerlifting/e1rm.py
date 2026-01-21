"""Estimated 1RM calculation functions."""

from datetime import datetime, timedelta
from collections import defaultdict

from .constants import RTS_RPE_CHART


def calculate_e1rm_brzycki(weight, reps):
    """Calculate estimated 1RM using Brzycki formula.
    
    Brzycki formula: 1RM = weight / (1.0278 - 0.0278 × reps)
    
    Args:
        weight: Weight lifted in kg
        reps: Number of reps performed
        
    Returns:
        Estimated 1RM in kg, or the actual weight if reps=1
    """
    if reps <= 0:
        return 0
    if reps == 1:
        return weight
    if reps >= 37:  # Brzycki formula becomes unreliable at very high reps
        return weight * 2  # Rough estimate
    
    return weight / (1.0278 - 0.0278 * reps)


def calculate_e1rm_rpe_adjusted(weight, reps, rpe=None, personal_rpe_table=None):
    """Calculate estimated 1RM using RPE-adjusted formula.
    
    Uses personal RPE table if available (most accurate), then falls back to
    the standard RTS RPE chart, then to Brzycki formula.
    
    Args:
        weight: Weight lifted in kg
        reps: Number of reps performed
        rpe: Rate of Perceived Exertion (6-10 scale, optional)
        personal_rpe_table: Dict of {reps: {rpe: percentage}} from personal data
        
    Returns:
        tuple: (e1rm_value, is_rpe_adjusted) where is_rpe_adjusted indicates
               whether RPE was used in the calculation
    """
    if reps <= 0:
        return 0, False
    if reps == 1 and rpe == 10:
        return weight, True
    
    # Try to use personal RPE table first (most accurate)
    if rpe is not None and personal_rpe_table is not None:
        rpe_rounded = round(rpe * 2) / 2  # Round to nearest 0.5
        if reps in personal_rpe_table and rpe_rounded in personal_rpe_table[reps]:
            percentage = personal_rpe_table[reps][rpe_rounded] / 100  # Convert from % to decimal
            if percentage > 0:
                return weight / percentage, True
    
    # Fall back to standard RTS RPE chart
    if rpe is not None:
        reps_key = min(reps, 12)  # Cap at 12 reps for chart lookup
        if reps_key in RTS_RPE_CHART:
            rpe_dict = RTS_RPE_CHART[reps_key]
            if rpe in rpe_dict:
                percentage = rpe_dict[rpe]
                return weight / percentage, True
            # Try to find closest RPE
            rpe_values = sorted(rpe_dict.keys())
            for rpe_val in reversed(rpe_values):
                if rpe >= rpe_val:
                    percentage = rpe_dict[rpe_val]
                    return weight / percentage, True
    
    # Fall back to Brzycki formula
    return calculate_e1rm_brzycki(weight, reps), False


def calculate_personal_rpe_table(workouts, exercise_name, reference_e1rm=None, min_data_points=2):
    """Calculate a personalized RPE table based on actual training data.
    
    For each (reps, RPE) combination logged, calculates what percentage of the
    reference e1RM that weight represents. This creates a custom RPE chart
    tailored to the individual lifter.
    
    Args:
        workouts: List of workout dicts
        exercise_name: Name of exercise to analyze (e.g., 'Squat (Low Bar)')
        reference_e1rm: Reference 1RM to calculate percentages against (auto-calculated if None)
        min_data_points: Minimum data points needed to include a cell in the table
        
    Returns:
        dict: {
            'table': {reps: {rpe: average_percentage}},
            'data_counts': {reps: {rpe: count}},
            'reference_e1rm': float
        }
    """
    # Collect all data points
    data_points = defaultdict(list)  # (reps, rpe) -> list of percentages
    
    # If no reference e1RM provided, calculate from the data
    if reference_e1rm is None:
        # Find the best e1RM from recent sets
        best_e1rm = 0
        for w in workouts:
            if w['name'] == exercise_name:
                if w.get('reps', 0) <= 8 and w.get('e1rm', 0) > best_e1rm:
                    best_e1rm = w['e1rm']
        reference_e1rm = best_e1rm if best_e1rm > 0 else 100  # Default to 100 if no data
    
    # Collect percentage data for each (reps, RPE) combo
    for w in workouts:
        if w['name'] != exercise_name:
            continue
        
        reps = w.get('reps', 0)
        rpe = w.get('rpe')
        weight = w.get('weight', 0)
        
        if reps <= 0 or reps > 12 or rpe is None or weight <= 0:
            continue
        
        # Round RPE to nearest 0.5
        rpe = round(rpe * 2) / 2
        if rpe < 6 or rpe > 10:
            continue
        
        # Calculate percentage of reference e1RM
        percentage = (weight / reference_e1rm) * 100
        data_points[(reps, rpe)].append(percentage)
    
    # Build the table
    table = {}
    data_counts = {}
    
    for (reps, rpe), percentages in data_points.items():
        if len(percentages) >= min_data_points:
            if reps not in table:
                table[reps] = {}
                data_counts[reps] = {}
            table[reps][rpe] = sum(percentages) / len(percentages)
            data_counts[reps][rpe] = len(percentages)
    
    return {
        'table': table,
        'data_counts': data_counts,
        'reference_e1rm': reference_e1rm
    }


def get_best_recent_e1rm(workouts, exercise_name, max_reps=6, months=2):
    """Find the best e1RM from recent sets with limited rep ranges.
    
    Args:
        workouts: List of workout dicts
        exercise_name: Exact name of the exercise to filter
        max_reps: Only consider sets with reps <= this value (default: 6)
        months: Only consider sets within this many months (default: 2)
        
    Returns:
        dict: {'e1rm': float, 'reps': int, 'date': str, 'weight': float} or None
    """
    cutoff_date = datetime.now() - timedelta(days=months * 30)
    
    best_e1rm = 0
    best_data = None
    
    for w in workouts:
        if w['name'] != exercise_name:
            continue
        
        # Filter by reps
        if w['reps'] > max_reps:
            continue
        
        # Filter by date
        try:
            workout_date = datetime.strptime(w['date'], '%Y-%m-%d')
            if workout_date < cutoff_date:
                continue
        except ValueError:
            continue
        
        if w['e1rm'] > best_e1rm:
            best_e1rm = w['e1rm']
            best_data = {
                'e1rm': w['e1rm'],
                'reps': w['reps'],
                'date': w['date'],
                'weight': w['weight']
            }
    
    return best_data
