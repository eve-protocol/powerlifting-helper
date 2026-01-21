"""Terminal and markdown output generation functions."""

import os
from datetime import datetime

from .constants import BIG3_MAIN, BIG3_VARIATIONS, LIFT_CATEGORIES, COLORS, RTS_RPE_CHART
from .e1rm import calculate_personal_rpe_table, get_best_recent_e1rm
from .parser import calculate_training_volume, analyze_trends
from .visualization import (
    color_date,
    markdown_date_staleness,
    generate_ascii_line_graph,
    generate_volume_bar_chart,
)


def print_color_legend():
    """Print a legend explaining the date colors."""
    r = COLORS['reset']
    print(f"\nLegend: ", end="")
    print(f"🟢 <3mo  ", end="")
    print(f"🟡 3-6mo  ", end="")
    print(f"🟠 6-9mo  ", end="")
    print(f"🔴 9-12mo  ", end="")
    print(f"🟣 >1yr")


def print_summary(stats, workouts):
    """Print summary statistics."""
    c = COLORS
    print(f"\n{c['cyan']}📊 SUMMARY{c['reset']}")
    print("-" * 50)
    print(f"   Date Range: {stats['date_range_start']} → {stats['date_range_end']}")
    print(f"   Training Days: {stats['total_days']}")
    print(f"   Total Sets: {stats['total_sets']}")
    
    # Count Big 3 sets
    big3_sets = [w for w in workouts if any(m in w['name'] for m in BIG3_MAIN)]
    print(f"   Big 3 Sets: {len(big3_sets)}")


def print_e1rm_summary(all_maxes, workouts):
    """Print estimated 1RM summary for Big 3.
    
    Best e1RM is calculated from recent sets (within 2 months) with <= 6 reps.
    """
    c = COLORS
    print(f"\n{c['cyan']}💪 ESTIMATED 1RM (Brzycki Formula){c['reset']}")
    print(f"{c['dim']}Best e1RM from sets ≤6 reps within last 2 months{c['reset']}")
    print("-" * 70)
    print(f"{'Lift':<40} {'Actual 1RM':>12} {'Best e1RM':>12} {'From':>8}")
    print("-" * 70)
    
    for name in sorted(all_maxes.keys()):
        if not any(m in name for m in BIG3_MAIN):
            continue
        
        # Get actual 1RM
        actual_1rm = all_maxes[name].get(1, {}).get('weight', 0)
        
        # Find best e1RM from recent sets with <= 6 reps
        recent_best = get_best_recent_e1rm(workouts, name, max_reps=6, months=2)
        
        best_e1rm = recent_best['e1rm'] if recent_best else 0
        best_reps = recent_best['reps'] if recent_best else 0
        
        actual_str = f"{actual_1rm:.1f}kg" if actual_1rm > 0 else "-"
        e1rm_str = f"{best_e1rm:.1f}kg" if best_e1rm > 0 else "-"
        from_str = f"{best_reps}RM" if best_reps > 0 else "-"
        
        print(f"{name:<40} {actual_str:>12} {e1rm_str:>12} {from_str:>8}")


def print_volume_summary(workouts):
    """Print training volume summary with ASCII bar charts."""
    c = COLORS
    print(f"\n{c['cyan']}📈 WEEKLY TRAINING VOLUME (Last 10 Weeks){c['reset']}")
    
    # Get volume for each category
    squat_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Squat'], 'weekly')
    bench_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Bench'], 'weekly')
    deadlift_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Deadlift'], 'weekly')
    
    # Get all weeks and sort
    all_weeks = set(squat_vol.keys()) | set(bench_vol.keys()) | set(deadlift_vol.keys())
    sorted_weeks = sorted(all_weeks, reverse=True)[:10]  # Last 10 weeks
    
    # Generate and print ASCII chart
    chart_lines = generate_volume_bar_chart(squat_vol, bench_vol, deadlift_vol, sorted_weeks)
    for line in chart_lines:
        print(line)


def print_trends(workouts):
    """Print Big 3 trends with ASCII line graph."""
    c = COLORS
    print(f"\n{c['cyan']}📉 BIG 3 TRENDS (Best e1RM per Week){c['reset']}")
    
    # Get trends for main lifts only
    squat_trends = analyze_trends(workouts, [BIG3_MAIN[0]], 'weekly')
    bench_trends = analyze_trends(workouts, [BIG3_MAIN[1]], 'weekly')
    deadlift_trends = analyze_trends(workouts, [BIG3_MAIN[2]], 'weekly')
    
    all_weeks = set(squat_trends.keys()) | set(bench_trends.keys()) | set(deadlift_trends.keys())
    sorted_weeks = sorted(all_weeks)[-10:]  # Last 10 weeks, oldest to newest
    
    # Prepare data series
    data_series = {
        'Squat': [squat_trends.get(w, 0) for w in sorted_weeks],
        'Bench': [bench_trends.get(w, 0) for w in sorted_weeks],
        'Deadlift': [deadlift_trends.get(w, 0) for w in sorted_weeks]
    }
    
    # Generate and print ASCII graph
    graph_lines = generate_ascii_line_graph(data_series, sorted_weeks)
    for line in graph_lines:
        print(line)


def print_rep_maxes(maxes, title):
    """Print rep maxes in a nice format with color-coded dates."""
    print(f"\n{'='*70}")
    print(title)
    print('='*70)
    
    for name in sorted(maxes.keys()):
        print(f"\n📊 {name}")
        print("-" * 50)
        
        # Sort by reps
        for reps in sorted(maxes[name].keys()):
            w = maxes[name][reps]
            rpe_str = f"@RPE {w['rpe']}" if w['rpe'] else ""
            e1rm_str = f"(e1RM: {w['e1rm']:.1f}kg)" if reps > 1 else ""
            colored_date = color_date(w['date'])
            print(f"    {reps:2}RM: {w['weight']:6.1f}kg {rpe_str:12} {e1rm_str:18} ({colored_date})")


def print_personal_rpe_table(workouts):
    """Print personalized RPE tables for Big 3 lifts."""
    c = COLORS
    print(f"\n{c['cyan']}📋 PERSONAL RPE TABLES{c['reset']}")
    print(f"{c['dim']}Calculated from your actual training data (min 2 data points per cell){c['reset']}")
    
    for lift_name in BIG3_MAIN:
        result = calculate_personal_rpe_table(workouts, lift_name)
        table = result['table']
        ref_e1rm = result['reference_e1rm']
        
        if not table:
            continue
        
        print(f"\n  {lift_name}")
        print(f"  Reference e1RM: {ref_e1rm:.1f}kg")
        print("-" * 60)
        
        # Header
        rpe_values = [10, 9.5, 9, 8.5, 8, 7.5, 7, 6.5, 6]
        header = f"{'Reps':>6}"
        for rpe in rpe_values:
            header += f"  {rpe:>5}"
        print(header)
        print("-" * 60)
        
        # Rows
        for reps in sorted(table.keys()):
            row = f"{reps:>4}RM"
            for rpe in rpe_values:
                if rpe in table[reps]:
                    pct = table[reps][rpe]
                    row += f"  {pct:5.1f}%"
                else:
                    row += f"      -"
            print(row)


def generate_markdown_rpe_table(workouts):
    """Generate markdown content for personalized RPE tables."""
    lines = []
    lines.append("## 📋 Personal RPE Tables")
    lines.append("")
    lines.append("*Calculated from your actual training data (minimum 2 data points per cell)*")
    lines.append("")
    
    rpe_values = [10, 9.5, 9, 8.5, 8, 7.5, 7, 6.5, 6]
    
    for lift_name in BIG3_MAIN:
        result = calculate_personal_rpe_table(workouts, lift_name)
        table = result['table']
        ref_e1rm = result['reference_e1rm']
        data_counts = result['data_counts']
        
        if not table:
            continue
        
        lines.append(f"### {lift_name}")
        lines.append(f"*Reference e1RM: {ref_e1rm:.1f}kg*")
        lines.append("")
        
        # Header
        header = "| Reps |"
        separator = "|------|"
        for rpe in rpe_values:
            header += f" @{rpe} |"
            separator += "------|"
        lines.append(header)
        lines.append(separator)
        
        # Rows
        for reps in sorted(table.keys()):
            row = f"| {reps}RM |"
            for rpe in rpe_values:
                if rpe in table[reps]:
                    pct = table[reps][rpe]
                    count = data_counts[reps].get(rpe, 0)
                    row += f" {pct:.0f}% |"
                else:
                    row += " - |"
            lines.append(row)
        
        lines.append("")
    
    # Compare to standard RTS chart (extended to 10RM and @6 RPE)
    lines.append("### Standard RTS Chart (for comparison)")
    lines.append("")
    lines.append("| Reps | @10 | @9.5 | @9 | @8.5 | @8 | @7.5 | @7 | @6.5 | @6 |")
    lines.append("|------|-----|------|-----|------|-----|------|-----|------|-----|")
    for reps in range(1, 11):
        if reps in RTS_RPE_CHART:
            rpe_dict = RTS_RPE_CHART[reps]
            row = f"| {reps}RM |"
            for rpe in [10, 9.5, 9, 8.5, 8, 7.5, 7, 6.5, 6]:
                if rpe in rpe_dict:
                    row += f" {rpe_dict[rpe]*100:.0f}% |"
                else:
                    row += " - |"
            lines.append(row)
    lines.append("")
    
    return lines


def generate_markdown_report(workouts, all_maxes, stats, output_path):
    """Generate comprehensive markdown report."""
    lines = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    lines.append("# Workout History Analysis")
    lines.append(f"")
    lines.append(f"*Generated: {now}*")
    lines.append("")
    
    # Summary
    lines.append("## 📊 Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Date Range | {stats['date_range_start']} → {stats['date_range_end']} |")
    lines.append(f"| Training Days | {stats['total_days']} |")
    lines.append(f"| Total Sets | {stats['total_sets']} |")
    lines.append("")
    
    # Staleness Legend
    lines.append("> **PR Freshness Legend:** 🟢 <3 months • 🟡 3-6 months • 🟠 6-9 months • 🔴 9-12 months • 🟣 >1 year")
    lines.append("")
    
    # Big 3 Performance Summary - show actual 1RM with date
    lines.append("## 💪 Big 3 Actual 1RM")
    lines.append("")
    lines.append("| Lift | 1RM | RPE | Date |")
    lines.append("|------|-----|-----|------|")
    
    for name in sorted(all_maxes.keys()):
        if not any(m in name for m in BIG3_MAIN):
            continue
        
        actual_1rm_data = all_maxes[name].get(1, {})
        actual_1rm = actual_1rm_data.get('weight', 0)
        actual_date = actual_1rm_data.get('date', '-')
        actual_rpe = actual_1rm_data.get('rpe')
        
        weight_str = f"{actual_1rm:.1f}kg" if actual_1rm > 0 else "-"
        rpe_str = str(actual_rpe) if actual_rpe else "-"
        date_display = markdown_date_staleness(actual_date) if actual_date != '-' else '-'
        
        lines.append(f"| {name} | {weight_str} | {rpe_str} | {date_display} |")
    
    lines.append("")
    
    # Trends
    lines.append("## 📈 Trends (Best e1RM per Week)")
    lines.append("")
    
    squat_trends = analyze_trends(workouts, [BIG3_MAIN[0]], 'weekly')
    bench_trends = analyze_trends(workouts, [BIG3_MAIN[1]], 'weekly')
    deadlift_trends = analyze_trends(workouts, [BIG3_MAIN[2]], 'weekly')
    
    all_weeks = set(squat_trends.keys()) | set(bench_trends.keys()) | set(deadlift_trends.keys())
    sorted_weeks = sorted(all_weeks)[-10:]  # Last 10 weeks, oldest to newest
    
    # Generate ASCII graph data
    data_series = {
        'Squat': [squat_trends.get(w, 0) for w in sorted_weeks],
        'Bench': [bench_trends.get(w, 0) for w in sorted_weeks],
        'Deadlift': [deadlift_trends.get(w, 0) for w in sorted_weeks]
    }
    
    lines.append("```")
    graph_lines = generate_ascii_line_graph(data_series, sorted_weeks)
    lines.extend(graph_lines)
    lines.append("```")
    lines.append("")
    
    # Training Volume
    lines.append("## 🏋️ Weekly Training Volume")
    lines.append("")
    
    squat_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Squat'], 'weekly')
    bench_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Bench'], 'weekly')
    deadlift_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Deadlift'], 'weekly')
    
    all_vol_weeks = set(squat_vol.keys()) | set(bench_vol.keys()) | set(deadlift_vol.keys())
    sorted_vol_weeks = sorted(all_vol_weeks, reverse=True)[:10]
    
    lines.append("```")
    vol_chart_lines = generate_volume_bar_chart(squat_vol, bench_vol, deadlift_vol, sorted_vol_weeks)
    lines.extend(vol_chart_lines)
    lines.append("```")
    lines.append("")
    
    # All-Time PRs
    lines.append("## 🏆 All-Time PRs")
    lines.append("")
    
    # Big 3 Main Lifts
    lines.append("### Big 3 - Main Lifts")
    lines.append("")
    
    for name in sorted(all_maxes.keys()):
        if not any(m in name for m in BIG3_MAIN):
            continue
        
        lines.append(f"#### {name}")
        lines.append("")
        lines.append("| Reps | Weight | e1RM | RPE | Date |")
        lines.append("|------|--------|------|-----|------|")
        
        for reps in sorted(all_maxes[name].keys()):
            w = all_maxes[name][reps]
            rpe_str = str(w['rpe']) if w['rpe'] else "-"
            e1rm_str = f"{w['e1rm']:.1f}kg" if reps > 1 else "-"
            date_display = markdown_date_staleness(w['date'])
            lines.append(f"| {reps}RM | {w['weight']:.1f}kg | {e1rm_str} | {rpe_str} | {date_display} |")
        
        lines.append("")
    
    # Big 3 Variations
    lines.append("### Big 3 - Variations")
    lines.append("")
    
    for name in sorted(all_maxes.keys()):
        if not any(v.lower() in name.lower() for v in BIG3_VARIATIONS):
            continue
        if any(m in name for m in BIG3_MAIN):  # Skip main lifts
            continue
        
        lines.append(f"#### {name}")
        lines.append("")
        lines.append("| Reps | Weight | e1RM | RPE | Date |")
        lines.append("|------|--------|------|-----|------|")
        
        for reps in sorted(all_maxes[name].keys()):
            w = all_maxes[name][reps]
            rpe_str = str(w['rpe']) if w['rpe'] else "-"
            e1rm_str = f"{w['e1rm']:.1f}kg" if reps > 1 else "-"
            date_display = markdown_date_staleness(w['date'])
            lines.append(f"| {reps}RM | {w['weight']:.1f}kg | {e1rm_str} | {rpe_str} | {date_display} |")
        
        lines.append("")
    
    # Personal RPE Tables
    rpe_table_lines = generate_markdown_rpe_table(workouts)
    lines.extend(rpe_table_lines)
    
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return output_path
