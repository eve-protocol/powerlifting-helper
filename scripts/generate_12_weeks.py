#!/usr/bin/env python3
"""
Generates a 12-week training history in an AI-readable markdown format.
Outputs to outputs/12_last_weeks_history.md
"""

import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# Constants for weight conversion
LBS_TO_KG = 0.453592


def load_history(filepath):
    """Load history.json file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def convert_lbs_to_kg(lbs):
    """Convert pounds to kg with proper rounding."""
    if lbs is None or lbs == 0:
        return 0
    kg = float(lbs) * LBS_TO_KG
    # Round to nearest integer (add 0.5 and floor for proper rounding)
    return round(kg)


def get_last_12_weeks_dates():
    """Get date range for last 12 weeks."""
    today = datetime.now()
    # Start from beginning of current week (Monday) and go back 12 weeks
    days_since_monday = today.weekday()
    current_week_start = today - timedelta(days=days_since_monday)
    twelve_weeks_ago = current_week_start - timedelta(weeks=11)
    return twelve_weeks_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')


def get_week_number(date_str):
    """Get ISO week number and year from date string."""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    iso_cal = dt.isocalendar()
    return iso_cal[0], iso_cal[1]


def get_day_name(date_str):
    """Get day name from date string."""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return dt.strftime('%A')


def format_target_info(set_data):
    """Format target info (percentage/RPE/reps)."""
    parts = []
    
    intensity = set_data.get('intensity')
    intensity_unit = set_data.get('intensity_unit', '%')
    target_reps = set_data.get('target')
    target_weight = set_data.get('target_weight')
    
    if target_reps:
        parts.append(f"target_reps={target_reps}")
    
    if intensity:
        if intensity_unit == 'RPE' or intensity_unit == 'rpe':
            parts.append(f"target_rpe={intensity}")
        elif intensity_unit == '%':
            parts.append(f"target_pct={intensity}%")
        else:
            parts.append(f"target_intensity={intensity}{intensity_unit}")
    
    if target_weight:
        target_kg = convert_lbs_to_kg(target_weight)
        if target_kg > 0:
            parts.append(f"target_weight={target_kg}kg")
    
    return ', '.join(parts) if parts else 'no_target'


def generate_markdown(data, start_date, end_date):
    """Generate AI-readable markdown from workout data."""
    lines = []
    lines.append("# Last 12 Weeks Training History")
    lines.append("")
    lines.append(f"**Period:** {start_date} to {end_date}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Format Guide")
    lines.append("- Weights are in **kg** (converted from lb in source)")
    lines.append("- RPE is Rate of Perceived Exertion (6-10 scale, 10 = max effort)")
    lines.append("- Each set shows: `reps × weight_kg @ RPE [target_info]`")
    lines.append("- target_pct = percentage of 1RM programmed")
    lines.append("- target_rpe = RPE target for the set")
    lines.append("- target_reps = programmed number of reps")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Organize data by week
    weeks = defaultdict(lambda: defaultdict(list))
    
    date_data = data.get('data', {})
    
    for date_str, day_workouts in sorted(date_data.items()):
        if not isinstance(date_str, str) or len(date_str) != 10:
            continue
        
        # Check if date is in range
        if date_str < start_date or date_str > end_date:
            continue
        
        year, week_num = get_week_number(date_str)
        week_key = f"{year}-W{week_num:02d}"
        
        for workout in day_workouts:
            records = workout.get('records', [])
            
            for exercise in records:
                exercise_name = exercise.get('name', 'Unknown Exercise')
                sets_data = []
                
                for s in exercise.get('sets', []):
                    if s.get('skipped', False):
                        continue
                    
                    archived_weight = s.get('archived_weight', 0)
                    archived_reps = s.get('archived_reps', s.get('amount', 0))
                    archived_rpe = s.get('archived_rpe')
                    
                    weight_kg = convert_lbs_to_kg(archived_weight)
                    
                    try:
                        reps = int(archived_reps) if archived_reps else 0
                    except (ValueError, TypeError):
                        reps = 0
                    
                    if weight_kg == 0 or reps == 0:
                        continue
                    
                    target_info = format_target_info(s)
                    
                    rpe_str = f"@ RPE {archived_rpe}" if archived_rpe else "@ RPE -"
                    
                    sets_data.append({
                        'reps': reps,
                        'weight_kg': weight_kg,
                        'rpe': archived_rpe,
                        'rpe_str': rpe_str,
                        'target_info': target_info
                    })
                
                if sets_data:
                    weeks[week_key][date_str].append({
                        'exercise': exercise_name,
                        'sets': sets_data
                    })
    
    # Output by week
    for week_key in sorted(weeks.keys(), reverse=True):
        lines.append(f"## {week_key}")
        lines.append("")
        
        week_data = weeks[week_key]
        
        for date_str in sorted(week_data.keys()):
            day_name = get_day_name(date_str)
            lines.append(f"### {date_str} ({day_name})")
            lines.append("")
            
            exercises = week_data[date_str]
            
            for ex in exercises:
                lines.append(f"**{ex['exercise']}**")
                
                for i, s in enumerate(ex['sets'], 1):
                    lines.append(f"- Set {i}: {s['reps']} × {s['weight_kg']}kg {s['rpe_str']} [{s['target_info']}]")
                
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return '\n'.join(lines)


def main():
    # Get paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    history_file = os.path.join(project_root, 'values', 'history.json')
    output_file = os.path.join(project_root, 'outputs', '12_last_weeks_history.md')
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Load data
    print(f"Loading history from: {history_file}")
    try:
        data = load_history(history_file)
    except FileNotFoundError:
        print(f"Error: {history_file} not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}")
        sys.exit(1)
    
    # Get date range
    start_date, end_date = get_last_12_weeks_dates()
    print(f"Date range: {start_date} to {end_date}")
    
    # Generate markdown
    markdown = generate_markdown(data, start_date, end_date)
    
    # Write output
    with open(output_file, 'w') as f:
        f.write(markdown)
    
    print(f"✅ Generated: {output_file}")
    
    # Count stats
    lines = markdown.split('\n')
    week_count = sum(1 for l in lines if l.startswith('## 20'))
    day_count = sum(1 for l in lines if l.startswith('### 20'))
    set_count = sum(1 for l in lines if l.startswith('- Set'))
    
    print(f"   Weeks: {week_count}")
    print(f"   Training days: {day_count}")
    print(f"   Total sets: {set_count}")


if __name__ == '__main__':
    main()
