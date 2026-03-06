#!/usr/bin/env python3
"""Generate historical RPE tables from values/history.json.

Creates outputs/rpe_table.md with:
- Main Big 3 tables (Squat/Bench/Deadlift)
- Variation tables (all squat/bench/deadlift exercise names found)

Rows: reps 1..10
Columns: RPE 10..6 (integer only)
Cell value: all-time best and 12-week best for exact reps+RPE.
"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

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


def parse_iso_date(date_str: str):
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def collect_cells(workouts, exercise_name: str, cutoff_date):
    """Return per-cell summary for all-time and recent windows.

    Structure:
    {(reps, rpe): {
      'at_best': float,
      'at_count': int,
      'w12_best': float|None,
      'w12_count': int,
    }}
    """
    grouped = defaultdict(list)

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
        date_obj = parse_iso_date(w["date"])
        grouped[(reps, rpe)].append({"weight": weight, "date": date_obj})

    cells = {}
    for key, samples in grouped.items():
        all_weights = [s["weight"] for s in samples]
        at_best = max(all_weights)
        at_count = sum(1 for s in samples if s["weight"] == at_best)

        recent = [s for s in samples if s["date"] >= cutoff_date]
        if recent:
            w12_best = max(s["weight"] for s in recent)
            w12_count = sum(1 for s in recent if s["weight"] == w12_best)
        else:
            w12_best = None
            w12_count = 0

        cells[key] = {
            "at_best": at_best,
            "at_count": at_count,
            "w12_best": w12_best,
            "w12_count": w12_count,
        }

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

            at_part = f"AT {cell['at_best']:.1f}×{cell['at_count']}"
            if cell["w12_best"] is None:
                w12_part = "12w -"
            else:
                w12_part = f"12w {cell['w12_best']:.1f}×{cell['w12_count']}"

            row.append(f" {at_part} / {w12_part} |")
        lines.append("".join(row))

    lines.append("")
    return lines


def get_reference_date(workouts):
    """Use latest workout date as anchor for the 12-week window."""
    dates = [parse_iso_date(w["date"]) for w in workouts if w.get("date")]
    if not dates:
        return datetime.now(timezone.utc).date()
    return max(dates)


def build_output(workouts):
    lines = []
    lines.append("# Historical RPE Tables")
    lines.append("")

    reference_date = get_reference_date(workouts)
    cutoff_date = reference_date - timedelta(weeks=12)

    lines.append(
        "Source: `values/history.json` parsed workout sets. "
        "Cells show all-time best and 12-week best for exact (reps, integer RPE) as `weight×count`."
    )
    lines.append(f"12-week window: {cutoff_date} → {reference_date}")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    lines.append("## Big 3")
    lines.append("")
    for lift in BIG3_MAIN:
        cells = collect_cells(workouts, lift, cutoff_date)
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
            cells = collect_cells(workouts, name, cutoff_date)
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
