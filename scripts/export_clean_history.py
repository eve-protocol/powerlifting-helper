#!/usr/bin/env python3
"""
Clean History Export Script

Outputs:
- outputs/history_clean.md                -> clean session-by-session workout log
- outputs/scorecard_weekly.md             -> weekly family scorecards
- outputs/scorecard_monthly.md            -> monthly family scorecards
- outputs/scorecard_quarterly.md          -> quarterly family scorecards
- outputs/scorecard_yearly.md             -> yearly family scorecards

Notes:
- Uses archived_* fields as source of truth
- Families are squat / bench / deadlift
- Bench family includes incline DB and Spoto
- Deadlift family includes paused deadlift and RDL
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

LBS_TO_KG = 0.453592
WEEK_DAY_RE = re.compile(r'Week\s+(\d+)\s+·\s+Day\s+(\d+)')

EXACT_FAMILY_MAP = {
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
    'Sumo Deadlift (Banded)': 'deadlift',
    'Romanian Deadlift (Barbell)': 'deadlift',
    'Sumo Romanian Deadlift': 'deadlift',
}

MAIN_LIFT_VARIATIONS = {
    'squat': {
        'Squat (Low Bar)', 'Squat (Paused)', 'High Bar Squat (Barbell)',
        'Tempo Squat (Barbell)', 'Tempo Squat High Bar (Barbell)', 'Box Squat (Barbell)'
    },
    'bench': {
        'Bench Press (Barbell)', 'Bench Press (Paused)', 'Bench Press (Close Grip)',
        'Larsen Press (Barbell)', 'Spoto Press', 'Incline Bench Press (Dumbbell)',
        'Incline Bench Press (Smith Machine)', 'Bench Press (Smith Machine)'
    },
    'deadlift': {
        'Deadlift (Barbell)', 'Deadlift (Paused)', 'Deadlift (Deficit)',
        'Block Pull (Barbell)', 'Sumo Deadlift (Barbell)', 'Sumo Deadlift (Paused)',
        'Sumo Deadlift (Banded)', 'Romanian Deadlift (Barbell)', 'Sumo Romanian Deadlift'
    }
}

FAMILY_LABELS = {
    'squat': 'Squat family',
    'bench': 'Bench family',
    'deadlift': 'Deadlift family',
}


def lbs_to_kg(lbs):
    if lbs is None or lbs == 0:
        return 0
    kg = float(lbs) * LBS_TO_KG
    return round(kg * 2) / 2


def parse_week_day(title):
    if not title:
        return None, None
    m = WEEK_DAY_RE.search(title)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def get_family(exercise_name):
    return EXACT_FAMILY_MAP.get(exercise_name)


def fmt_num(x, digits=1):
    if x is None:
        return '-'
    if isinstance(x, int):
        return str(x)
    if round(x, digits).is_integer():
        return str(int(round(x, digits)))
    return f"{x:.{digits}f}"


def fmt_delta(x, digits=1, suffix=''):
    if x is None:
        return 'n/a'
    arrow = '↑' if x > 0 else ('↓' if x < 0 else '→')
    abs_x = abs(x)
    if round(abs_x, digits).is_integer():
        return f"{arrow} {int(round(abs_x, digits))}{suffix}"
    return f"{arrow} {abs_x:.{digits}f}{suffix}"


def format_set(set_data, set_num):
    weight_kg = lbs_to_kg(set_data.get('archived_weight'))
    reps = set_data.get('archived_reps', 0)
    rpe = set_data.get('archived_rpe') or set_data.get('previous_rpe') or '-'

    target_reps = set_data.get('target')
    target_rpe = set_data.get('intensity')

    if set_data.get('skipped', False):
        return None

    parts = [f"  Set {set_num}: {weight_kg}kg x {reps}"]
    if rpe != '-':
        parts.append(f"@ RPE {rpe}")

    target_parts = []
    if target_reps and target_reps != reps:
        target_parts.append(f"target: {target_reps} reps")
    if target_rpe:
        if isinstance(target_rpe, list):
            target_parts.append(f"target RPE: {target_rpe[0]}-{target_rpe[1]}")
        else:
            target_parts.append(f"target RPE: {target_rpe}")
    if target_parts:
        parts.append(f"[{', '.join(target_parts)}]")

    return ' '.join(parts)


def build_workouts(data):
    workouts = []
    for date in sorted(data.get('data', {}).keys(), reverse=True):
        day_obj = datetime.strptime(date, '%Y-%m-%d').date()
        for workout in data['data'][date]:
            title = workout.get('title', workout.get('name', 'Unknown'))
            block_name = workout.get('name', 'Unknown')
            week, day = parse_week_day(title)
            workouts.append({
                'date': date,
                'date_obj': day_obj,
                'title': title,
                'block_name': block_name,
                'week': week,
                'day': day,
                'finished_at': workout.get('finished_at'),
                'records': workout.get('records', []),
            })
    return workouts


def extract_family_entries(workouts):
    entries = []
    for workout in workouts:
        month = workout['date'][:7]
        quarter = f"{workout['date_obj'].year}-Q{((workout['date_obj'].month-1)//3)+1}"
        year = str(workout['date_obj'].year)
        week_label = None
        if workout['week'] is not None:
            week_label = f"{workout['block_name']} / Week {workout['week']}"

        session_key = (workout['date'], workout['title'])
        for record in workout['records']:
            exercise_name = record.get('name', 'Unknown')
            family = get_family(exercise_name)
            if not family:
                continue
            for set_data in record.get('sets', []):
                if set_data.get('skipped', False):
                    continue
                weight_kg = lbs_to_kg(set_data.get('archived_weight'))
                reps = set_data.get('archived_reps', 0)
                rpe = set_data.get('archived_rpe') or set_data.get('previous_rpe')
                if not reps or not weight_kg:
                    continue
                entries.append({
                    'family': family,
                    'exercise': exercise_name,
                    'date': workout['date'],
                    'date_obj': workout['date_obj'],
                    'block_name': workout['block_name'],
                    'week': workout['week'],
                    'day': workout['day'],
                    'week_label': week_label,
                    'month': month,
                    'quarter': quarter,
                    'year': year,
                    'session_key': session_key,
                    'weight_kg': weight_kg,
                    'reps': reps,
                    'rpe': float(rpe) if rpe is not None else None,
                })
    return entries


def summarize_group(arr):
    sessions = len({x['session_key'] for x in arr})
    sets = len(arr)
    avg_sets = round(sets / sessions, 2) if sessions else 0
    rpe_values = [x['rpe'] for x in arr if x['rpe'] is not None]
    avg_rpe = round(sum(rpe_values) / len(rpe_values), 2) if rpe_values else None
    avg_load = round(sum(x['weight_kg'] for x in arr) / len(arr), 1) if arr else None
    tonnage = round(sum(x['weight_kg'] * x['reps'] for x in arr), 1)
    avg_tonnage_per_session = round(tonnage / sessions, 1) if sessions else None

    main_sets = [x for x in arr if x['exercise'] in MAIN_LIFT_VARIATIONS[x['family']]]
    singles = [x for x in main_sets if x['reps'] == 1]
    worksets = [x for x in main_sets if x['reps'] > 1]
    top_single = max(singles, key=lambda x: (x['weight_kg'], -(x['rpe'] or 0))) if singles else None
    top_work = max(worksets, key=lambda x: (x['weight_kg'], x['reps'], -(x['rpe'] or 0))) if worksets else None

    return {
        'sessions': sessions,
        'sets': sets,
        'avg_sets': avg_sets,
        'avg_rpe': avg_rpe,
        'avg_load': avg_load,
        'tonnage': tonnage,
        'avg_tonnage_per_session': avg_tonnage_per_session,
        'top_single': top_single,
        'top_work': top_work,
    }


def compute_period_scorecards(entries, period_key):
    grouped = defaultdict(lambda: defaultdict(list))
    for e in entries:
        period = e.get(period_key)
        if not period:
            continue
        grouped[period][e['family']].append(e)

    result = {}
    for period, fams in grouped.items():
        result[period] = {}
        for family, arr in fams.items():
            result[period][family] = summarize_group(arr)
    return dict(sorted(result.items(), reverse=True))


def add_deltas(scorecards, period_order):
    for idx, period in enumerate(period_order):
        prev = period_order[idx+1] if idx+1 < len(period_order) else None
        for family in ('squat', 'bench', 'deadlift'):
            cur = scorecards.get(period, {}).get(family)
            if not cur:
                continue
            prev_s = scorecards.get(prev, {}).get(family) if prev else None
            cur['delta'] = {
                'avg_sets': (cur['avg_sets'] - prev_s['avg_sets']) if prev_s else None,
                'avg_rpe': (cur['avg_rpe'] - prev_s['avg_rpe']) if prev_s and cur['avg_rpe'] is not None and prev_s['avg_rpe'] is not None else None,
                'avg_load': (cur['avg_load'] - prev_s['avg_load']) if prev_s and cur['avg_load'] is not None and prev_s['avg_load'] is not None else None,
                'tonnage': (cur['tonnage'] - prev_s['tonnage']) if prev_s else None,
                'avg_tonnage_per_session': (cur['avg_tonnage_per_session'] - prev_s['avg_tonnage_per_session']) if prev_s and cur['avg_tonnage_per_session'] is not None and prev_s['avg_tonnage_per_session'] is not None else None,
            }

            if prev_s:
                ts_cur, ts_prev = cur.get('top_single'), prev_s.get('top_single')
                tw_cur, tw_prev = cur.get('top_work'), prev_s.get('top_work')
                cur['delta']['top_single'] = None
                cur['delta']['top_work'] = None
                if ts_cur and ts_prev:
                    cur['delta']['top_single'] = ts_cur['weight_kg'] - ts_prev['weight_kg']
                if tw_cur and tw_prev and tw_cur['reps'] == tw_prev['reps']:
                    cur['delta']['top_work'] = tw_cur['weight_kg'] - tw_prev['weight_kg']
            else:
                cur['delta']['top_single'] = None
                cur['delta']['top_work'] = None


def top_marker_text(marker):
    if not marker:
        return '-'
    return f"{fmt_num(marker['weight_kg'])}kg x {marker['reps']} @ {fmt_num(marker['rpe'], 2)}"


def render_scorecard_file(output_path, title, subtitle, scorecards):
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(subtitle)
    lines.append("")

    periods = list(scorecards.keys())
    add_deltas(scorecards, periods)
    period_label = title.split()[0].lower()

    for idx, period in enumerate(periods):
        prev_period = periods[idx + 1] if idx + 1 < len(periods) else None
        lines.append(f"## {period}")
        lines.append("")
        if prev_period:
            lines.append(f"Comparison baseline: {prev_period}")
            lines.append("")
        for family in ('squat', 'bench', 'deadlift'):
            s = scorecards.get(period, {}).get(family)
            if not s:
                continue
            prev_s = scorecards.get(prev_period, {}).get(family) if prev_period else None
            d = s['delta']
            lines.append(f"### {FAMILY_LABELS[family]}")
            lines.append("")
            lines.append("| Metric | Current | Previous | Delta |")
            lines.append("|---|---:|---:|---:|")
            rows = [
                ("Sessions", fmt_num(s['sessions'], 0), fmt_num(prev_s['sessions'], 0) if prev_s else '-', fmt_delta((s['sessions'] - prev_s['sessions']) if prev_s else None, 0)),
                ("Total sets", fmt_num(s['sets'], 0), fmt_num(prev_s['sets'], 0) if prev_s else '-', fmt_delta((s['sets'] - prev_s['sets']) if prev_s else None, 0)),
                ("Avg sets/session", fmt_num(s['avg_sets'], 2), fmt_num(prev_s['avg_sets'], 2) if prev_s else '-', fmt_delta(d['avg_sets'], 2)),
                ("Avg RPE", fmt_num(s['avg_rpe'], 2), fmt_num(prev_s['avg_rpe'], 2) if prev_s and prev_s['avg_rpe'] is not None else '-', fmt_delta(d['avg_rpe'], 2)),
                ("Avg load", f"{fmt_num(s['avg_load'], 1)}kg", f"{fmt_num(prev_s['avg_load'], 1)}kg" if prev_s and prev_s['avg_load'] is not None else '-', fmt_delta(d['avg_load'], 1, 'kg')),
                ("Tonnage", f"{fmt_num(s['tonnage'], 1)}kg", f"{fmt_num(prev_s['tonnage'], 1)}kg" if prev_s else '-', fmt_delta(d['tonnage'], 1, 'kg')),
                ("Avg tonnage/session", f"{fmt_num(s['avg_tonnage_per_session'], 1)}kg", f"{fmt_num(prev_s['avg_tonnage_per_session'], 1)}kg" if prev_s and prev_s['avg_tonnage_per_session'] is not None else '-', fmt_delta(d['avg_tonnage_per_session'], 1, 'kg')),
            ]
            for metric, cur, prev, delta in rows:
                lines.append(f"| {metric} | {cur} | {prev} | {delta} |")
            lines.append("")
            lines.append(f"- Top single: {top_marker_text(s['top_single'])}")
            if prev_s:
                lines.append(f"- Previous top single: {top_marker_text(prev_s['top_single'])}")
                lines.append(f"- Top single delta: {fmt_delta(d['top_single'], 1, 'kg')} (only meaningful when the variation is comparable)")
            lines.append(f"- Top work set: {top_marker_text(s['top_work'])}")
            if prev_s:
                lines.append(f"- Previous top work set: {top_marker_text(prev_s['top_work'])}")
                lines.append(f"- Top work-set delta: {fmt_delta(d['top_work'], 1, 'kg')} (only meaningful when the rep scheme is comparable)")
            lines.append("")

    output_path.write_text('\n'.join(lines))


def render_clean_history(output_path, workouts):
    lines = []
    lines.append("# Clean Training History")
    lines.append("")
    lines.append("*Auto-generated from history.json - uses archived_* fields only*")
    lines.append("")

    for workout in workouts:
        lines.append(f"## {workout['date']}")
        lines.append("")
        lines.append(f"**{workout['title']}**")
        if workout['finished_at']:
            lines.append(f"Finished: {workout['finished_at']}")
        lines.append("")
        for record in workout['records']:
            exercise_name = record.get('name', 'Unknown')
            lines.append(f"### {exercise_name}")
            lines.append("")
            for i, set_data in enumerate(record.get('sets', []), 1):
                set_str = format_set(set_data, i)
                if set_str:
                    lines.append(set_str)
            lines.append("")

    output_path.write_text('\n'.join(lines))


def generate_exports():
    repo_path = Path(__file__).parent.parent
    history_file = repo_path / 'values' / 'history.json'
    outputs = repo_path / 'outputs'
    outputs.mkdir(parents=True, exist_ok=True)

    with open(history_file, 'r') as f:
        data = json.load(f)

    workouts = build_workouts(data)
    entries = extract_family_entries(workouts)

    render_clean_history(outputs / 'history_clean.md', workouts)

    weekly = compute_period_scorecards(entries, 'week_label')
    monthly = compute_period_scorecards(entries, 'month')
    quarterly = compute_period_scorecards(entries, 'quarter')
    yearly = compute_period_scorecards(entries, 'year')

    render_scorecard_file(
        outputs / 'scorecard_weekly.md',
        'Weekly Scorecards',
        '*Auto-generated from history.json - movement-family scorecards by training week*',
        weekly,
    )
    render_scorecard_file(
        outputs / 'scorecard_monthly.md',
        'Monthly Scorecards',
        '*Auto-generated from history.json - movement-family scorecards by calendar month*',
        monthly,
    )
    render_scorecard_file(
        outputs / 'scorecard_quarterly.md',
        'Quarterly Scorecards',
        '*Auto-generated from history.json - movement-family scorecards by calendar quarter*',
        quarterly,
    )
    render_scorecard_file(
        outputs / 'scorecard_yearly.md',
        'Yearly Scorecards',
        '*Auto-generated from history.json - movement-family scorecards by calendar year*',
        yearly,
    )

    print(f"Generated clean history: {outputs / 'history_clean.md'}")
    print(f"Generated weekly scorecards: {outputs / 'scorecard_weekly.md'}")
    print(f"Generated monthly scorecards: {outputs / 'scorecard_monthly.md'}")
    print(f"Generated quarterly scorecards: {outputs / 'scorecard_quarterly.md'}")
    print(f"Generated yearly scorecards: {outputs / 'scorecard_yearly.md'}")
    print(f"Total workout entries: {len(workouts)}")


if __name__ == '__main__':
    generate_exports()
