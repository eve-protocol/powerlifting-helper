#!/usr/bin/env python3
"""Generate historical RPE tables from values/history.json.

Creates outputs/rpe_table.md with:
- Main Big 3 tables (Squat/Bench/Deadlift)
- Variation tables (all squat/bench/deadlift exercise names found)

Rows: reps 1..10
Columns: RPE 10..6 (integer only)
Cell value: best (max) kg achieved for exact reps+RPE, with staleness emoji.
"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from datetime import datetime, timezone

try:
    from common.files import write_text_if_changed
except ModuleNotFoundError:
    from scripts.common.files import write_text_if_changed
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


def staleness_emoji(best_date, reference_date):
    days_old = (reference_date - best_date).days
    if days_old < 90:
        return "🟢"
    if days_old < 180:
        return "🟡"
    if days_old < 270:
        return "🟠"
    if days_old < 365:
        return "🔴"
    return "🟣"


def collect_cells(workouts, exercise_name: str):
    """Return {(reps, rpe): {'best': float, 'best_date': date}}."""
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
        best_weight = max(s["weight"] for s in samples)
        # if same best appears multiple times, keep latest date of that best
        best_dates = [s["date"] for s in samples if s["weight"] == best_weight]
        best_date = max(best_dates)
        cells[key] = {
            "best": best_weight,
            "best_date": best_date,
        }

    return cells


def render_table(exercise_name: str, cells: dict, reference_date) -> list[str]:
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

            emoji = staleness_emoji(cell["best_date"], reference_date)
            row.append(f" {cell['best']:.1f} {emoji} |")
        lines.append("".join(row))

    lines.append("")
    return lines


def get_reference_date(workouts):
    dates = [parse_iso_date(w["date"]) for w in workouts if w.get("date")]
    if not dates:
        return datetime.now(timezone.utc).date()
    return max(dates)


def build_output(workouts):
    lines = []
    lines.append("# Historical RPE Tables")
    lines.append("")

    reference_date = get_reference_date(workouts)

    lines.append(
        "Source: `values/history.json` parsed workout sets. "
        "Cells show best kg for exact (reps, integer RPE), with staleness emoji for the date of that best."
    )
    lines.append(f"Reference date: {reference_date}")
    lines.append("")
    lines.append("> Legend: 🟢 <3mo • 🟡 3-6mo • 🟠 6-9mo • 🔴 9-12mo • 🟣 >1yr")
    lines.append("")

    lines.append("## Big 3")
    lines.append("")
    for lift in BIG3_MAIN:
        cells = collect_cells(workouts, lift)
        lines.extend(render_table(lift, cells, reference_date))

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
            if any(cells.values()):
                lines.extend(render_table(name, cells, reference_date))

    return "\n".join(lines).rstrip() + "\n"


def main():
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(script_dir)

    parser = argparse.ArgumentParser(description="Generate historical RPE markdown tables")
    parser.add_argument("--history", default=os.path.join(project_root, "values", "history.json"))
    parser.add_argument("--output", default=os.path.join(project_root, "outputs", "rpe_table.md"))
    args = parser.parse_args()

    data = load_history(args.history)
    workouts = parse_all_workouts(data)

    content = build_output(workouts)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    changed = write_text_if_changed(args.output, content)

    status = "written" if changed else "unchanged"
    print(f"✅ RPE table {status}: {args.output}")


if __name__ == "__main__":
    main()
