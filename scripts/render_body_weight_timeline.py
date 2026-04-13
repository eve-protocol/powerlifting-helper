#!/usr/bin/env python3
"""Render merged bodyweight timeline outputs (Markdown + CSV)."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from health_metrics import load_health_daily


def fmt(x, digits=1):
    if x is None:
        return "-"
    if round(x, digits).is_integer():
        return str(int(round(x, digits)))
    return f"{x:.{digits}f}"


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
    weights = [r["weight_kg"] for r in rows if r.get("weight_kg") is not None]
    if not weights:
        return None
    return {
        "days": len(weights),
        "avg": sum(weights) / len(weights),
        "min": min(weights),
        "max": max(weights),
        "start": weights[0],
        "end": weights[-1],
        "delta": weights[-1] - weights[0],
    }


def main():
    repo = Path(__file__).resolve().parents[1]
    merged = load_health_daily(repo)
    rows = [merged[d] for d in sorted(merged) if merged[d].get("weight_kg") is not None]
    outputs = repo / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    csv_path = outputs / "body_weight_timeline.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "weight_kg", "source", "measured_at"])
        writer.writeheader()
        for row in rows:
            weight = (row.get("sources") or {}).get("weight") or {}
            writer.writerow({
                "date": row["date"],
                "weight_kg": row.get("weight_kg"),
                "source": source_label(row),
                "measured_at": weight.get("time", ""),
            })

    monthly = defaultdict(list)
    for row in rows:
        monthly[row["date"][:7]].append(row)

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
            f"- Lowest bodyweight: {fmt(overall['min'])} kg",
            f"- Highest bodyweight: {fmt(overall['max'])} kg",
            f"- First logged day: {rows[0]['date']} ({fmt(overall['start'])} kg, {source_label(rows[0])})",
            f"- Last logged day: {rows[-1]['date']} ({fmt(overall['end'])} kg, {source_label(rows[-1])})",
            f"- Net change: {fmt(overall['delta'])} kg",
            "",
        ])

    lines.extend([
        "## Month-by-Month Summary",
        "",
        "| Month | Days | Avg | Low | High | Start | End | Delta | Main source |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for month in sorted(monthly):
        s = summarize(monthly[month])
        if not s:
            continue
        sources = defaultdict(int)
        for row in monthly[month]:
            sources[source_label(row)] += 1
        main_source = max(sources.items(), key=lambda kv: kv[1])[0] if sources else "-"
        lines.append(
            f"| {month} | {s['days']} | {fmt(s['avg'])} kg | {fmt(s['min'])} kg | {fmt(s['max'])} kg | {fmt(s['start'])} kg | {fmt(s['end'])} kg | {fmt(s['delta'])} kg | {main_source} |"
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
    lines.append(f"CSV export: `outputs/{csv_path.name}`")
    lines.append("")

    md_path = outputs / "body_weight_timeline.md"
    md_path.write_text("\n".join(lines))
    print(f"Rendered merged bodyweight timeline: {md_path}")
    print(f"Rendered merged bodyweight CSV: {csv_path}")


if __name__ == "__main__":
    main()
