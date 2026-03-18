#!/usr/bin/env python3
"""
Clean History Export Script

Converts history.json to a clean markdown file with:
- LBS converted to KG
- Only archived_* fields (source of truth)
- Target vs Actual comparison when available
- Weekly family scorecards for squat / bench / deadlift
- Easy to read format for AI analysis
"""

import json
import re
from pathlib import Path
from collections import defaultdict

LBS_TO_KG = 0.453592


def lbs_to_kg(lbs):
    """Convert lbs to kg, round to nearest 0.5kg"""
    if lbs is None or lbs == 0:
        return 0
    kg = float(lbs) * LBS_TO_KG
    return round(kg * 2) / 2


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


def get_family(exercise_name):
    if exercise_name in EXACT_FAMILY_MAP:
        return EXACT_FAMILY_MAP[exercise_name]
    return None


WEEK_DAY_RE = re.compile(r'Week\s+(\d+)\s+·\s+Day\s+(\d+)')


def parse_week_day(title):
    if not title:
        return None, None
    m = WEEK_DAY_RE.search(title)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def format_set(set_data, set_num):
    """Format a single set for output"""
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


def build_workout_records(data):
    records = []
    for date in sorted(data.get('data', {}).keys(), reverse=True):
        workouts = data['data'][date]
        for workout in workouts:
            title = workout.get('title', workout.get('name', 'Unknown'))
            block_name = workout.get('name', 'Unknown')
            week, day = parse_week_day(title)
            records.append({
                'date': date,
                'title': title,
                'block_name': block_name,
                'week': week,
                'day': day,
                'finished_at': workout.get('finished_at'),
                'records': workout.get('records', [])
            })
    return records


def collect_scorecards(workouts):
    grouped = defaultdict(list)

    for workout in workouts:
        if workout['week'] is None or workout['day'] is None:
            continue
        key = (workout['block_name'], workout['week'])
        grouped[key].append(workout)

    scorecards = {}

    for key, items in grouped.items():
        family_entries = defaultdict(list)
        family_sessions = defaultdict(set)

        for workout in items:
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
                    family_sessions[family].add(session_key)
                    family_entries[family].append({
                        'exercise': exercise_name,
                        'weight_kg': weight_kg,
                        'reps': reps,
                        'rpe': float(rpe) if rpe is not None else None,
                        'date': workout['date'],
                        'week': workout['week'],
                        'day': workout['day'],
                    })

        scorecards[key] = {}
        for family in ('squat', 'bench', 'deadlift'):
            arr = family_entries.get(family, [])
            if not arr:
                continue
            sessions = len(family_sessions[family])
            sets = len(arr)
            avg_sets = round(sets / sessions, 2) if sessions else 0
            rpe_values = [x['rpe'] for x in arr if x['rpe'] is not None]
            avg_rpe = round(sum(rpe_values) / len(rpe_values), 2) if rpe_values else None
            avg_load = round(sum(x['weight_kg'] for x in arr) / len(arr), 1)
            tonnage = round(sum(x['weight_kg'] * x['reps'] for x in arr), 1)

            main_sets = [x for x in arr if x['exercise'] in MAIN_LIFT_VARIATIONS[family]]
            singles = [x for x in main_sets if x['reps'] == 1]
            nonsingles = [x for x in main_sets if x['reps'] > 1]
            top_single = max(singles, key=lambda x: (x['weight_kg'], -(x['rpe'] or 0))) if singles else None
            top_work = max(nonsingles, key=lambda x: (x['weight_kg'], x['reps'], -(x['rpe'] or 0))) if nonsingles else None

            progress_bits = []
            if top_single:
                progress_bits.append(f"single {top_single['weight_kg']}x1 @ {top_single['rpe']}")
            if top_work:
                progress_bits.append(f"work {top_work['weight_kg']}x{top_work['reps']} @ {top_work['rpe']}")
            progress = '; '.join(progress_bits) if progress_bits else 'no clear main-lift marker'

            scorecards[key][family] = {
                'sessions': sessions,
                'sets': sets,
                'avg_sets': avg_sets,
                'avg_rpe': avg_rpe,
                'avg_load': avg_load,
                'tonnage': tonnage,
                'progress': progress,
            }

    return scorecards


def append_scorecard(lines, block_name, week, scorecard):
    lines.append(f"## Scorecard — {block_name} / Week {week}")
    lines.append("")
    lines.append("- Uses movement families. Bench family includes incline DB bench and Spoto; deadlift family includes paused deadlift and RDL.")
    lines.append("")

    family_labels = {
        'squat': 'Squat family',
        'bench': 'Bench family',
        'deadlift': 'Deadlift family',
    }

    for family in ('squat', 'bench', 'deadlift'):
        s = scorecard.get(family)
        if not s:
            continue
        lines.append(f"### {family_labels[family]}")
        lines.append("")
        lines.append(f"- Sessions: {s['sessions']}")
        lines.append(f"- Total sets: {s['sets']}")
        lines.append(f"- Avg sets/session: {s['avg_sets']}")
        if s['avg_rpe'] is not None:
            lines.append(f"- Avg RPE: {s['avg_rpe']}")
        lines.append(f"- Avg load: {s['avg_load']}kg")
        lines.append(f"- Tonnage: {s['tonnage']}kg")
        lines.append(f"- Progress marker: {s['progress']}")
        lines.append("")


def generate_clean_history():
    repo_path = Path(__file__).parent.parent
    history_file = repo_path / 'values' / 'history.json'
    output_file = repo_path / 'outputs' / 'history_clean.md'

    with open(history_file, 'r') as f:
        data = json.load(f)

    workouts = build_workout_records(data)
    scorecards = collect_scorecards(workouts)

    lines = []
    lines.append("# Clean Training History")
    lines.append("")
    lines.append("*Auto-generated from history.json - uses archived_* fields only*")
    lines.append("")

    printed_scorecards = set()

    for workout in workouts:
        scorecard_key = None
        if workout['week'] is not None and workout['day'] is not None:
            scorecard_key = (workout['block_name'], workout['week'])
        if scorecard_key and scorecard_key not in printed_scorecards:
            sc = scorecards.get(scorecard_key)
            if sc:
                append_scorecard(lines, workout['block_name'], workout['week'], sc)
                printed_scorecards.add(scorecard_key)

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

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))

    print(f"Generated clean history: {output_file}")
    print(f"Total workout entries: {len(workouts)}")
    print(f"Scorecards generated: {len(scorecards)}")


if __name__ == '__main__':
    generate_clean_history()
