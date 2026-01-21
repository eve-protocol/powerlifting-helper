"""Data parsing and analysis functions."""

from collections import defaultdict
from datetime import datetime

from .e1rm import calculate_e1rm_brzycki, calculate_e1rm_rpe_adjusted


def parse_all_workouts(data, use_personal_rpe=True):
    """Parse ALL workout data from Boostcamp format (no time filter).
    
    Args:
        data: Boostcamp history data
        use_personal_rpe: If True, build personal RPE tables and use them for e1RM
        
    Returns:
        List of workout dicts with e1RM calculated using personal data when available
    """
    workouts = []
    date_data = data.get('data', {})
    
    # First pass: collect all sets to build personal RPE tables
    raw_sets = []
    for date_str, day_workouts in date_data.items():
        if not isinstance(date_str, str) or len(date_str) != 10:
            continue
        
        for workout in day_workouts:
            records = workout.get('records', [])
            
            for exercise in records:
                name = exercise.get('name', '')
                
                for s in exercise.get('sets', []):
                    if s.get('skipped', False):
                        continue
                    
                    archived_weight_lbs = s.get('archived_weight', 0)
                    archived_reps = s.get('archived_reps', s.get('amount', 0))
                    rpe = s.get('archived_rpe', s.get('rpe', None))
                    
                    try:
                        weight = float(archived_weight_lbs) / 2.20462
                        reps = int(archived_reps) if archived_reps else 0
                    except (ValueError, TypeError):
                        continue
                    
                    if weight > 0 and reps > 0:
                        raw_sets.append({
                            'date': date_str,
                            'name': name,
                            'weight': round(weight, 1),
                            'reps': reps,
                            'rpe': rpe
                        })
    
    # Build personal RPE tables per exercise if enabled
    personal_tables = {}
    if use_personal_rpe:
        # Group by exercise name
        exercises = set(s['name'] for s in raw_sets)
        for exercise_name in exercises:
            # Calculate reference e1RM using standard method first
            best_e1rm = 0
            for s in raw_sets:
                if s['name'] == exercise_name and s['reps'] <= 8:
                    e1rm = calculate_e1rm_brzycki(s['weight'], s['reps'])
                    if e1rm > best_e1rm:
                        best_e1rm = e1rm
            
            if best_e1rm > 0:
                # Build personal table for this exercise
                data_points = defaultdict(list)
                
                for s in raw_sets:
                    if s['name'] != exercise_name:
                        continue
                    if s['rpe'] is None or s['reps'] > 12:
                        continue
                    
                    rpe_rounded = round(s['rpe'] * 2) / 2
                    if rpe_rounded < 6 or rpe_rounded > 10:
                        continue
                    
                    percentage = (s['weight'] / best_e1rm) * 100
                    data_points[(s['reps'], rpe_rounded)].append(percentage)
                
                # Average percentages (require at least 2 data points)
                table = {}
                for (reps, rpe), percentages in data_points.items():
                    if len(percentages) >= 2:
                        if reps not in table:
                            table[reps] = {}
                        table[reps][rpe] = sum(percentages) / len(percentages)
                
                if table:
                    personal_tables[exercise_name] = table
    
    # Second pass: calculate e1RM using personal tables when available
    for s in raw_sets:
        personal_table = personal_tables.get(s['name'])
        e1rm, rpe_adjusted = calculate_e1rm_rpe_adjusted(
            s['weight'], s['reps'], s['rpe'], personal_table
        )
        workouts.append({
            'date': s['date'],
            'name': s['name'],
            'weight': s['weight'],
            'reps': s['reps'],
            'rpe': s['rpe'],
            'e1rm': round(e1rm, 1),
            'rpe_adjusted': rpe_adjusted
        })
    
    return workouts


def find_all_rep_maxes(workouts, exercise_filter=None):
    """Find best weight for each exercise at each rep count (all reps, not hardcoded)."""
    maxes = defaultdict(lambda: defaultdict(lambda: {'weight': 0, 'date': '', 'rpe': None, 'e1rm': 0}))
    
    for w in workouts:
        name = w['name']
        
        # Filter if specified
        if exercise_filter and not any(f.lower() in name.lower() for f in exercise_filter):
            continue
            
        reps = w['reps']
        
        if w['weight'] > maxes[name][reps]['weight']:
            maxes[name][reps] = {
                'weight': w['weight'],
                'date': w['date'],
                'rpe': w['rpe'],
                'e1rm': w['e1rm']
            }
    
    return maxes


def calculate_training_volume(workouts, exercise_filters, period='weekly'):
    """Calculate training volume (kg, reps, sets) for filtered exercises.
    
    Args:
        workouts: List of workout dicts
        exercise_filters: List of exercise name substrings to filter
        period: 'weekly' or 'monthly'
        
    Returns:
        dict: {period_key: {'total_kg': X, 'total_reps': Y, 'total_sets': Z}}
    """
    volume = defaultdict(lambda: {'total_kg': 0, 'total_reps': 0, 'total_sets': 0})
    
    for w in workouts:
        name = w['name']
        
        # Filter
        if not any(f.lower() in name.lower() for f in exercise_filters):
            continue
        
        try:
            date = datetime.strptime(w['date'], '%Y-%m-%d')
        except ValueError:
            continue
        
        if period == 'weekly':
            # ISO week number
            key = f"{date.isocalendar()[0]}-W{date.isocalendar()[1]:02d}"
        else:  # monthly
            key = f"{date.year}-{date.month:02d}"
        
        volume[key]['total_kg'] += w['weight'] * w['reps']
        volume[key]['total_reps'] += w['reps']
        volume[key]['total_sets'] += 1
    
    return dict(volume)


def analyze_trends(workouts, exercise_filters, period='weekly'):
    """Analyze progression trends for exercises.
    
    Tracks best estimated 1RM per period.
    
    Args:
        workouts: List of workout dicts
        exercise_filters: List of exercise name substrings to filter
        period: 'weekly' or 'monthly'
        
    Returns:
        dict: {period_key: best_e1rm}
    """
    trends = defaultdict(lambda: 0)
    
    for w in workouts:
        name = w['name']
        
        # Filter
        if not any(f.lower() in name.lower() for f in exercise_filters):
            continue
        
        try:
            date = datetime.strptime(w['date'], '%Y-%m-%d')
        except ValueError:
            continue
        
        if period == 'weekly':
            key = f"{date.isocalendar()[0]}-W{date.isocalendar()[1]:02d}"
        else:  # monthly
            key = f"{date.year}-{date.month:02d}"
        
        if w['e1rm'] > trends[key]:
            trends[key] = w['e1rm']
    
    return dict(trends)


def get_summary_stats(workouts, data):
    """Get summary statistics from workout data."""
    if not workouts:
        return {}
    
    dates = [w['date'] for w in workouts]
    date_set = set(dates)
    
    return {
        'total_sets': len(workouts),
        'total_days': len(date_set),
        'date_range_start': min(dates),
        'date_range_end': max(dates),
        'total_days_in_data': len(data.get('data', {}))
    }
