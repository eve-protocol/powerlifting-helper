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
from pathlib import Path

try:
    from common.files import write_text_if_changed
except ModuleNotFoundError:
    from scripts.common.files import write_text_if_changed
from health_metrics import load_health_daily, format_health_summary_block
from powerlifting.exercises import classify_family, get_completed_reps, get_logged_weight_kg, is_failed_set, lbs_to_kg
from powerlifting.stress import ActualSingleReferenceResolver, format_stress_score, score_set_stress


def load_history(filepath):
    """Load history.json file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def get_last_12_weeks_dates(data):
    """Get a stable 12-week range anchored to the latest workout date."""
    date_keys = [d for d in data.get('data', {}) if isinstance(d, str) and len(d) == 10]

    if date_keys:
        anchor = datetime.strptime(max(date_keys), '%Y-%m-%d')
    else:
        anchor = datetime.now()

    days_since_monday = anchor.weekday()
    current_week_start = anchor - timedelta(days=days_since_monday)
    twelve_weeks_ago = current_week_start - timedelta(weeks=11)
    return twelve_weeks_ago.strftime('%Y-%m-%d'), anchor.strftime('%Y-%m-%d')


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
        target_kg = lbs_to_kg(target_weight, rounding=1)
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


def build_reference_workouts(data):
    workouts = []
    for date_str, day_workouts in data.get('data', {}).items():
        if not isinstance(date_str, str) or len(date_str) != 10:
            continue
        for workout in day_workouts:
            workouts.append({
                'date': date_str,
                'records': workout.get('records', []),
            })
    return workouts


def parse_workout_data(data, start_date, end_date, reference_resolver):
    """Parse workout data and organize by week."""
    weeks = defaultdict(lambda: {
        'days': defaultdict(list),
        'stats': {
            'squat': {'sets': 0, 'volume': 0, 'estimated_stress': 0, 'real_stress': 0},
            'bench': {'sets': 0, 'volume': 0, 'estimated_stress': 0, 'real_stress': 0},
            'deadlift': {'sets': 0, 'volume': 0, 'estimated_stress': 0, 'real_stress': 0},
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
                    
                    archived_rpe = s.get('archived_rpe')
                    completed_reps = get_completed_reps(s)
                    
                    weight_kg = get_logged_weight_kg(s, rounding=1)
                    
                    try:
                        reps = int(completed_reps) if completed_reps else 0
                    except (ValueError, TypeError):
                        reps = 0
                    
                    if weight_kg == 0 or reps == 0:
                        continue
                    
                    target_info = format_target_info(s)
                    rpe_str = f"@ RPE {archived_rpe}" if archived_rpe else "@ RPE -"
                    
                    failed = is_failed_set(s)
                    family = classify_family(exercise_name)
                    stress = None
                    if family in ('squat', 'bench', 'deadlift'):
                        stress = score_set_stress(s, family, date_str, reference_resolver, rounding=1)
                    sets_data.append({
                        'reps': reps,
                        'weight_kg': weight_kg,
                        'rpe': archived_rpe,
                        'rpe_str': rpe_str,
                        'target_info': target_info,
                        'failed': failed,
                        'estimated_stress': stress['estimated_stress'] if stress else None,
                        'real_stress': stress['real_stress'] if stress else None,
                    })
                    
                    # Track Big 3 stats using successful sets only
                    if not failed:
                        set_volume = weight_kg * reps
                        if family in ('squat', 'bench', 'deadlift'):
                            weeks[week_key]['stats'][family]['sets'] += 1
                            weeks[week_key]['stats'][family]['volume'] += set_volume
                            if stress and stress['estimated_stress'] is not None:
                                weeks[week_key]['stats'][family]['estimated_stress'] += stress['estimated_stress']
                            if stress and stress['real_stress'] is not None:
                                weeks[week_key]['stats'][family]['real_stress'] += stress['real_stress']
                
                if sets_data:
                    weeks[week_key]['days'][date_str].append({
                        'exercise': exercise_name,
                        'sets': sets_data
                    })
    
    return weeks


def generate_markdown(weeks, start_date, end_date, health_daily):
    """Generate AI-readable markdown from parsed workout data."""
    lines = []
    lines.append("# Last 12 Weeks Training History")
    lines.append("")
    lines.append(f"**Period:** {start_date} to {end_date}")

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
    lines.append("- est_stress = planned stress from target reps/RPE and actual or target load")
    lines.append("- real_stress = logged stress from completed reps/load/RPE")
    lines.append("- stress score = reps × weight_kg × intensity² × RPE factor; intensity uses rolling actual-single reference, not e1RM")
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
            'squat_est_stress': format_comparison(round(stats['squat']['estimated_stress']), round(prev_stats['squat']['estimated_stress']) if prev_stats else None),
            'bench_est_stress': format_comparison(round(stats['bench']['estimated_stress']), round(prev_stats['bench']['estimated_stress']) if prev_stats else None),
            'deadlift_est_stress': format_comparison(round(stats['deadlift']['estimated_stress']), round(prev_stats['deadlift']['estimated_stress']) if prev_stats else None),
            'squat_real_stress': format_comparison(round(stats['squat']['real_stress']), round(prev_stats['squat']['real_stress']) if prev_stats else None),
            'bench_real_stress': format_comparison(round(stats['bench']['real_stress']), round(prev_stats['bench']['real_stress']) if prev_stats else None),
            'deadlift_real_stress': format_comparison(round(stats['deadlift']['real_stress']), round(prev_stats['deadlift']['real_stress']) if prev_stats else None),
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

    lines.append("### Estimated Stress with Week-over-Week Change")
    lines.append("")
    lines.append("```")
    lines.append("Week       │ Squat Est Stress │ Bench Est Stress │ Deadlift Est Stress")
    lines.append("───────────┼──────────────────┼──────────────────┼─────────────────────")
    for week_key in display_weeks:
        stats = weeks[week_key]['stats']
        cmp = comparisons[week_key]
        squat_stress = round(stats['squat']['estimated_stress'])
        bench_stress = round(stats['bench']['estimated_stress'])
        deadlift_stress = round(stats['deadlift']['estimated_stress'])
        lines.append(f"{week_key}  │ {squat_stress:>7}{cmp['squat_est_stress']:>8} │ {bench_stress:>7}{cmp['bench_est_stress']:>8} │ {deadlift_stress:>7}{cmp['deadlift_est_stress']:>8}")
    lines.append("```")
    lines.append("")

    lines.append("### Real Stress with Week-over-Week Change")
    lines.append("")
    lines.append("```")
    lines.append("Week       │ Squat Real Stress │ Bench Real Stress │ Deadlift Real Stress")
    lines.append("───────────┼───────────────────┼───────────────────┼──────────────────────")
    for week_key in display_weeks:
        stats = weeks[week_key]['stats']
        cmp = comparisons[week_key]
        squat_stress = round(stats['squat']['real_stress'])
        bench_stress = round(stats['bench']['real_stress'])
        deadlift_stress = round(stats['deadlift']['real_stress'])
        lines.append(f"{week_key}  │ {squat_stress:>7}{cmp['squat_real_stress']:>8} │ {bench_stress:>7}{cmp['bench_real_stress']:>8} │ {deadlift_stress:>7}{cmp['deadlift_real_stress']:>8}")
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
        lines.append(f"**Stress Summary:** Squat est/real: {round(stats['squat']['estimated_stress'])}/{round(stats['squat']['real_stress'])} | "
                    f"Bench est/real: {round(stats['bench']['estimated_stress'])}/{round(stats['bench']['real_stress'])} | "
                    f"Deadlift est/real: {round(stats['deadlift']['estimated_stress'])}/{round(stats['deadlift']['real_stress'])}")
        lines.append("")
        
        for date_str in sorted(week_data['days'].keys()):
            day_name = get_day_name(date_str)
            lines.append(f"### {date_str} ({day_name})")
            lines.append("")
            lines.extend(format_health_summary_block(health_daily.get(date_str)))

            exercises = week_data['days'][date_str]
            
            for ex in exercises:
                lines.append(f"**{ex['exercise']}**")
                
                for i, s in enumerate(ex['sets'], 1):
                    failed_tag = " [failed]" if s.get('failed') else ""
                    lines.append(
                        f"- Set {i}: {s['reps']} × {s['weight_kg']}kg{failed_tag} {s['rpe_str']} "
                        f"[{s['target_info']}; est_stress={format_stress_score(s['estimated_stress'])}; "
                        f"real_stress={format_stress_score(s['real_stress'])}]"
                    )
                
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return '\n'.join(lines)


def main():
    # Get paths
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    start_date, end_date = get_last_12_weeks_dates(data)
    print(f"Date range: {start_date} to {end_date}")
    
    # Parse data
    reference_resolver = ActualSingleReferenceResolver(build_reference_workouts(data))
    weeks = parse_workout_data(data, start_date, end_date, reference_resolver)
    health_daily = load_health_daily(Path(project_root))

    # Generate markdown
    markdown = generate_markdown(weeks, start_date, end_date, health_daily)
    
    # Write output
    changed = write_text_if_changed(output_file, markdown)
    status = 'Generated' if changed else 'Unchanged'
    print(f"✅ {status}: {output_file}")
    
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
