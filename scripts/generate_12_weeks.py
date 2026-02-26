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

# Big 3 lift patterns for matching
SQUAT_PATTERNS = ['squat']
BENCH_PATTERNS = ['bench']
DEADLIFT_PATTERNS = ['deadlift']


def load_history(filepath):
    """Load history.json file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def convert_lbs_to_kg(lbs):
    """Convert pounds to kg with proper rounding."""
    if lbs is None or lbs == 0:
        return 0
    kg = float(lbs) * LBS_TO_KG
    return round(kg)


def get_last_12_weeks_dates():
    """Get date range for last 12 weeks."""
    today = datetime.now()
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


def matches_lift(exercise_name, patterns):
    """Check if exercise name matches any pattern."""
    name_lower = exercise_name.lower()
    return any(p in name_lower for p in patterns)


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


def format_comparison(current, previous):
    """Format comparison with previous week."""
    if previous is None or previous == 0:
        return ""
    diff = current - previous
    if diff > 0:
        return f" (+{diff})"
    elif diff < 0:
        return f" ({diff})"
    return " (=)"


def generate_volume_bar(volume, max_volume, width=30):
    """Generate ASCII bar for volume visualization."""
    if max_volume == 0:
        return ""
    filled = int((volume / max_volume) * width)
    return '█' * filled + '░' * (width - filled)


def parse_workout_data(data, start_date, end_date):
    """Parse workout data and organize by week."""
    weeks = defaultdict(lambda: {
        'days': defaultdict(list),
        'stats': {
            'squat': {'sets': 0, 'volume': 0},
            'bench': {'sets': 0, 'volume': 0},
            'deadlift': {'sets': 0, 'volume': 0},
        }
    })
    
    date_data = data.get('data', {})
    
    for date_str, day_workouts in sorted(date_data.items()):
        if not isinstance(date_str, str) or len(date_str) != 10:
            continue
        
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
                    
                    # Track Big 3 stats
                    set_volume = weight_kg * reps
                    if matches_lift(exercise_name, SQUAT_PATTERNS):
                        weeks[week_key]['stats']['squat']['sets'] += 1
                        weeks[week_key]['stats']['squat']['volume'] += set_volume
                    elif matches_lift(exercise_name, BENCH_PATTERNS):
                        weeks[week_key]['stats']['bench']['sets'] += 1
                        weeks[week_key]['stats']['bench']['volume'] += set_volume
                    elif matches_lift(exercise_name, DEADLIFT_PATTERNS):
                        weeks[week_key]['stats']['deadlift']['sets'] += 1
                        weeks[week_key]['stats']['deadlift']['volume'] += set_volume
                
                if sets_data:
                    weeks[week_key]['days'][date_str].append({
                        'exercise': exercise_name,
                        'sets': sets_data
                    })
    
    return weeks


def generate_markdown(weeks, start_date, end_date):
    """Generate AI-readable markdown from parsed workout data."""
    lines = []
    lines.append("# Last 12 Weeks Training History")
    lines.append("")
    lines.append(f"**Period:** {start_date} to {end_date}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Format Guide
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
    
    # 12-Week Overview
    lines.append("## 📊 12-Week Overview")
    lines.append("")
    
    # Sort weeks chronologically first to calculate comparisons
    chrono_weeks = sorted(weeks.keys())
    display_weeks = sorted(weeks.keys(), reverse=True)  # Most recent first for display
    
    # Pre-calculate comparisons (current vs previous week in chronological order)
    comparisons = {}
    prev_stats = None
    for week_key in chrono_weeks:
        stats = weeks[week_key]['stats']
        comparisons[week_key] = {
            'squat_sets': format_comparison(stats['squat']['sets'], prev_stats['squat']['sets'] if prev_stats else None),
            'bench_sets': format_comparison(stats['bench']['sets'], prev_stats['bench']['sets'] if prev_stats else None),
            'deadlift_sets': format_comparison(stats['deadlift']['sets'], prev_stats['deadlift']['sets'] if prev_stats else None),
            'squat_vol': format_comparison(stats['squat']['volume'], prev_stats['squat']['volume'] if prev_stats else None),
            'bench_vol': format_comparison(stats['bench']['volume'], prev_stats['bench']['volume'] if prev_stats else None),
            'deadlift_vol': format_comparison(stats['deadlift']['volume'], prev_stats['deadlift']['volume'] if prev_stats else None),
        }
        prev_stats = stats
    
    # Find max volumes for scaling bars
    max_squat_vol = max((weeks[w]['stats']['squat']['volume'] for w in display_weeks), default=1)
    max_bench_vol = max((weeks[w]['stats']['bench']['volume'] for w in display_weeks), default=1)
    max_deadlift_vol = max((weeks[w]['stats']['deadlift']['volume'] for w in display_weeks), default=1)
    max_volume = max(max_squat_vol, max_bench_vol, max_deadlift_vol, 1)
    
    # Weekly summary table (most recent first)
    lines.append("### Set Counts (Week over Week)")
    lines.append("")
    lines.append("| Week | Squat Sets | Bench Sets | Deadlift Sets |")
    lines.append("|------|------------|------------|---------------|")
    
    for week_key in display_weeks:
        stats = weeks[week_key]['stats']
        cmp = comparisons[week_key]
        lines.append(f"| {week_key} | {stats['squat']['sets']}{cmp['squat_sets']} | {stats['bench']['sets']}{cmp['bench_sets']} | {stats['deadlift']['sets']}{cmp['deadlift_sets']} |")
    
    lines.append("")
    
    # Volume summary with graphs (most recent first)
    lines.append("### Volume (kg) with Week-over-Week Change")
    lines.append("")
    lines.append("```")
    lines.append("Week       │ Squat Volume      │ Bench Volume      │ Deadlift Volume")
    lines.append("───────────┼───────────────────┼───────────────────┼───────────────────")
    
    for week_key in display_weeks:
        stats = weeks[week_key]['stats']
        cmp = comparisons[week_key]
        
        squat_vol = stats['squat']['volume']
        bench_vol = stats['bench']['volume']
        deadlift_vol = stats['deadlift']['volume']
        
        lines.append(f"{week_key}  │ {squat_vol:>6}kg{cmp['squat_vol']:>8} │ {bench_vol:>6}kg{cmp['bench_vol']:>8} │ {deadlift_vol:>6}kg{cmp['deadlift_vol']:>8}")
    
    lines.append("```")
    lines.append("")
    
    # Volume bar graphs (most recent first)
    lines.append("### Volume Graphs")
    lines.append("")
    lines.append("**Squat Volume (kg)**")
    lines.append("```")
    for week_key in display_weeks:
        vol = weeks[week_key]['stats']['squat']['volume']
        bar = generate_volume_bar(vol, max_volume, 25)
        lines.append(f"{week_key} │{bar}│ {vol:,}kg")
    lines.append("```")
    lines.append("")
    
    lines.append("**Bench Volume (kg)**")
    lines.append("```")
    for week_key in display_weeks:
        vol = weeks[week_key]['stats']['bench']['volume']
        bar = generate_volume_bar(vol, max_volume, 25)
        lines.append(f"{week_key} │{bar}│ {vol:,}kg")
    lines.append("```")
    lines.append("")
    
    lines.append("**Deadlift Volume (kg)**")
    lines.append("```")
    for week_key in display_weeks:
        vol = weeks[week_key]['stats']['deadlift']['volume']
        bar = generate_volume_bar(vol, max_volume, 25)
        lines.append(f"{week_key} │{bar}│ {vol:,}kg")
    lines.append("```")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Detailed week-by-week data
    lines.append("## 📋 Detailed Training Log")
    lines.append("")
    
    for week_key in sorted(weeks.keys(), reverse=True):
        week_data = weeks[week_key]
        stats = week_data['stats']
        
        lines.append(f"## {week_key}")
        lines.append("")
        
        # Week summary
        lines.append(f"**Weekly Summary:** Squat: {stats['squat']['sets']} sets / {stats['squat']['volume']:,}kg | "
                    f"Bench: {stats['bench']['sets']} sets / {stats['bench']['volume']:,}kg | "
                    f"Deadlift: {stats['deadlift']['sets']} sets / {stats['deadlift']['volume']:,}kg")
        lines.append("")
        
        for date_str in sorted(week_data['days'].keys()):
            day_name = get_day_name(date_str)
            lines.append(f"### {date_str} ({day_name})")
            lines.append("")
            
            exercises = week_data['days'][date_str]
            
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
    
    # Parse data
    weeks = parse_workout_data(data, start_date, end_date)
    
    # Generate markdown
    markdown = generate_markdown(weeks, start_date, end_date)
    
    # Write output
    with open(output_file, 'w') as f:
        f.write(markdown)
    
    print(f"✅ Generated: {output_file}")
    
    # Count stats
    lines = markdown.split('\n')
    week_count = len(weeks)
    day_count = sum(len(weeks[w]['days']) for w in weeks)
    set_count = sum(1 for l in lines if l.startswith('- Set'))
    
    print(f"   Weeks: {week_count}")
    print(f"   Training days: {day_count}")
    print(f"   Total sets: {set_count}")


if __name__ == '__main__':
    main()
