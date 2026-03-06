#!/usr/bin/env python3
"""Generate historical RPE tables from values/history.json.

Creates outputs/rpe_table.md with:
- Main Big 3 tables (Squat/Bench/Deadlift)
- Variation tables (all squat/bench/deadlift exercise names found)

Rows: reps 1..10
Columns: RPE 10..6 (integer only)
Cell value: best (max) kg achieved for exact reps+RPE, plus count and latest.
"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from datetime import datetime, timezone

from powerlifting import BIG3_MAIN, load_history, parse_all_workouts

RPE_COLUMNS = [10, 9, 8, 7, 6]
REP_ROWS = list(range(1, 11))


def round_to_2_5(weight: float) -> float:
    return round(weight / 2.5) * 2.5


def normalize_rpe(value):
    if value is None:
        return None
    try:
        r = float(value)
    except (TypeError, ValueError):
        return None
    if r < 6 or r > 10:
        return None
    # Boostcamp can store half steps; this table is integer-only 10..6.
    return int(round(r))


def collect_cells(workouts, exercise_name: str):
    """Return {(reps, rpe): {'best': float, 'count': int, 'latest': (date, kg)}}."""
    cells = {}

    for w in workouts:
        if w["name"] != exercise_name:
            continue

        reps = int(w.get("reps") or 0)
        if reps not in REP_ROWS:
            continue

        rpe = normalize_rpe(w.get("rpe"))
        if rpe not in RPE_COLUMNS:
            continue

        weight = round_to_2_5(float(w["weight"]))
        date = w["date"]
        key = (reps, rpe)

        if key not in cells:
            cells[key] = {
                "best": weight,
                "count": 1,
                "latest_date": date,
                "latest_weight": weight,
            }
            continue

        cell = cells[key]
        cell["count"] += 1
        if weight > cell["best"]:
            cell["best"] = weight

        # Keep latest occurrence metadata
        if date >= cell["latest_date"]:
            cell["latest_date"] = date
            cell["latest_weight"] = weight

    return cells


def render_table(exercise_name: str, cells: dict) -> list[str]:
    lines = []
    lines.append(f"### {exercise_name}")
    lines.append("")
    lines.append("| Reps \\ RPE | @10 | @9 | @8 | @7 | @6 |")
    lines.append("|---|---|---|---|---|---|")

    for reps in REP_ROWS:
        row = [f"| {reps} |"]
        for rpe in RPE_COLUMNS:
            cell = cells.get((reps, rpe))
            if not cell:
                row.append(" - |")
                continue
            best = f"{cell['best']:.1f}"
            latest = f"{cell['latest_weight']:.1f}"
            date = cell["latest_date"]
            count = cell["count"]
            # Keep compact but informative in markdown.
            row.append(f" {best}kg (n={count}, latest {latest}kg {date}) |")
        lines.append("".join(row))

    lines.append("")
    return lines


def build_output(workouts):
    lines = []
    lines.append("# Historical RPE Tables")
    lines.append("")
    lines.append(
        "Source: `values/history.json` parsed workout sets. "
        "Cells show best kg for exact (reps, integer RPE) with occurrence count and latest entry."
    )
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    lines.append("## Big 3")
    lines.append("")
    for lift in BIG3_MAIN:
        cells = collect_cells(workouts, lift)
        lines.extend(render_table(lift, cells))

    # Variation discovery: all S/B/D-like exercise names excluding exact Big 3 names
    keywords = ("squat", "bench", "deadlift")
    variation_names = sorted(
        {
            w["name"]
            for w in workouts
            if w["name"] not in BIG3_MAIN and any(k in w["name"].lower() for k in keywords)
        }
    )

    lines.append("## Variations")
    lines.append("")
    if not variation_names:
        lines.append("No variations found in history.")
        lines.append("")
    else:
        for name in variation_names:
            cells = collect_cells(workouts, name)
            # Skip empty tables (e.g. no valid reps/rpe range)
            if any(cells.values()):
                lines.extend(render_table(name, cells))

    return "\n".join(lines).rstrip() + "\n"


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    parser = argparse.ArgumentParser(description="Generate historical RPE markdown tables")
    parser.add_argument("--history", default=os.path.join(project_root, "values", "history.json"))
    parser.add_argument("--output", default=os.path.join(project_root, "outputs", "rpe_table.md"))
    args = parser.parse_args()

    data = load_history(args.history)
    workouts = parse_all_workouts(data)

    content = build_output(workouts)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ RPE table written: {args.output}")


if __name__ == "__main__":
    main()
