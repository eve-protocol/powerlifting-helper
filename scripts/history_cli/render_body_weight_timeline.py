#!/usr/bin/env python3
"""Render merged bodyweight timeline output (Markdown only)."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from health_metrics import load_health_daily
from powerlifting.exercises import TRACKED_BODYWEIGHT_TIMELINE_EXERCISES, get_exercise_family


def fmt(x, digits=1):
    if x is None:
        return "-"
    if round(x, digits).is_integer():
        return str(int(round(x, digits)))
    return f"{x:.{digits}f}"


def fmt_signed(x, digits=1):
    if x is None:
        return "-"
    sign = "+" if x > 0 else ""
    return f"{sign}{fmt(x, digits)}"


def source_label(row: dict) -> str:
    weight = (row.get("sources") or {}).get("weight") or {}
    app = weight.get("app_name")
    if app:
        return app
    pkg = weight.get("package_name")
    if pkg:
        return pkg.rsplit(".", 1)[-1]
    return "-"


def summarize(rows):
    valid_rows = [r for r in rows if r.get("weight_kg") is not None]
    weights = [r["weight_kg"] for r in valid_rows]
    if not valid_rows:
        return None
    low_row = min(valid_rows, key=lambda r: r["weight_kg"])
    high_row = max(valid_rows, key=lambda r: r["weight_kg"])
    return {
        "days": len(weights),
        "avg": sum(weights) / len(weights),
        "min": low_row["weight_kg"],
        "min_date": low_row["date"],
        "max": high_row["weight_kg"],
        "max_date": high_row["date"],
        "start": weights[0],
        "end": weights[-1],
        "delta": weights[-1] - weights[0],
    }


def estimate_1rm(weight, reps, rpe):
    equivalent_reps = reps + max(0, 10 - rpe)
    return weight * (1 + equivalent_reps / 30)


def load_monthly_strength(repo: Path):
    lines = (repo / "outputs" / "history_clean.md").read_text().splitlines()
    current_date = None
    current_lift = None
    monthly_best_e1rm = defaultdict(lambda: {"squat": None, "bench": None, "deadlift": None})
    monthly_best_actual = defaultdict(lambda: {"squat": None, "bench": None, "deadlift": None})

    for raw in lines:
        line = raw.strip()
        m = re.match(r"^## (\d{4}-\d{2}-\d{2})$", line)
        if m:
            current_date = m.group(1)
            current_lift = None
            continue
        if not current_date:
            continue
        if line.startswith("### "):
            exercise_name = line[4:]
            current_lift = None
            if exercise_name in TRACKED_BODYWEIGHT_TIMELINE_EXERCISES:
                current_lift = get_exercise_family(exercise_name)
            continue
        if current_lift and line.startswith("Set "):
            m = re.search(r": ([\d.]+)kg x (\d+)(?: @ RPE ([\d.]+))?", line)
            if not m:
                continue
            weight = float(m.group(1))
            reps = int(m.group(2))
            rpe = float(m.group(3)) if m.group(3) else None
            month = current_date[:7]
            if reps == 1:
                cur_actual = monthly_best_actual[month][current_lift]
                monthly_best_actual[month][current_lift] = weight if cur_actual is None or weight > cur_actual else cur_actual
            if rpe is not None:
                value = estimate_1rm(weight, reps, rpe)
                cur = monthly_best_e1rm[month][current_lift]
                monthly_best_e1rm[month][current_lift] = value if cur is None or value > cur else cur

    return monthly_best_e1rm, monthly_best_actual


def main():
    repo = Path(__file__).resolve().parents[2]
    merged = load_health_daily(repo)
    rows = [merged[d] for d in sorted(merged) if merged[d].get("weight_kg") is not None]
    outputs = repo / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    monthly = defaultdict(list)
    for row in rows:
        monthly[row["date"][:7]].append(row)
    monthly_e1rm, monthly_actual = load_monthly_strength(repo)

    lines = [
        "# Merged Body Weight Timeline",
        "",
        "This view merges old Zepp/Xiaomi scale history with newer Health Connect / VeSync weight entries.",
        "",
    ]

    overall = summarize(rows)
    if overall:
        lines.extend([
            "## Overall Summary",
            "",
            f"- Logged days: {overall['days']}",
            f"- Average bodyweight: {fmt(overall['avg'])} kg",
            f"- Lowest bodyweight: {fmt(overall['min'])} kg on {overall['min_date']}",
            f"- Highest bodyweight: {fmt(overall['max'])} kg on {overall['max_date']}",
            f"- First logged day: {rows[0]['date']} ({fmt(overall['start'])} kg, {source_label(rows[0])})",
            f"- Last logged day: {rows[-1]['date']} ({fmt(overall['end'])} kg, {source_label(rows[-1])})",
            f"- Net change: {fmt(overall['delta'])} kg",
            "",
        ])

    lines.extend([
        "## Month-by-Month Summary",
        "",
        "| Month | Days | Avg | Low | High | Start | End | Delta | Main source | Best squat single | Best squat e1RM | Best bench single | Best bench e1RM | Best deadlift single | Best deadlift e1RM |",
        "|---|---:|---:|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|",
    ])
    for month in sorted(monthly):
        s = summarize(monthly[month])
        if not s:
            continue
        sources = defaultdict(int)
        for row in monthly[month]:
            sources[source_label(row)] += 1
        main_source = max(sources.items(), key=lambda kv: kv[1])[0] if sources else "-"
        e1 = monthly_e1rm.get(month, {})
        actual = monthly_actual.get(month, {})
        lines.append(
            f"| {month} | {s['days']} | {fmt(s['avg'])} kg | {fmt(s['min'])} kg ({s['min_date']}) | {fmt(s['max'])} kg ({s['max_date']}) | {fmt(s['start'])} kg | {fmt(s['end'])} kg | {fmt_signed(s['delta'])} kg | {main_source} | {fmt(actual.get('squat'))} kg | {fmt(e1.get('squat'))} kg | {fmt(actual.get('bench'))} kg | {fmt(e1.get('bench'))} kg | {fmt(actual.get('deadlift'))} kg | {fmt(e1.get('deadlift'))} kg |"
        )
    lines.extend([
        "",
        "## Recent Daily Entries",
        "",
        "| Date | Weight | Source |",
        "|---|---:|---|",
    ])
    for row in rows[-30:]:
        lines.append(f"| {row['date']} | {fmt(row['weight_kg'])} kg | {source_label(row)} |")
    lines.append("")

    md_path = outputs / "body_weight_timeline.md"
    md_path.write_text("\n".join(lines))
    print(f"Rendered merged bodyweight timeline: {md_path}")


if __name__ == "__main__":
    main()
