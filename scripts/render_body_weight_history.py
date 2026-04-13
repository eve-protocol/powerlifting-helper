#!/usr/bin/env python3
"""Render human-readable Zepp/Health bodyweight summaries to Markdown."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path


def fmt(x, digits=1):
    if x is None:
        return "-"
    if round(x, digits).is_integer():
        return str(int(round(x, digits)))
    return f"{x:.{digits}f}"


def load_days(path: Path):
    if not path.exists():
        return None, []
    payload = json.loads(path.read_text())
    return payload.get("metadata", {}), payload.get("days", [])


def summarize(rows):
    weights = [row.get("weight_kg") for row in rows if row.get("weight_kg") is not None]
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


def render(body_metadata, rows, output_path: Path):
    lines = ["# Body Weight History", ""]
    if body_metadata:
        lines.extend([
            "## Export Metadata",
            "",
            f"- Source: {body_metadata.get('source', '-')}",
            f"- Date range: {body_metadata.get('earliest_date_in_export', '-')} → {body_metadata.get('latest_date_in_export', '-')}",
            f"- Distinct days with bodyweight: {body_metadata.get('total_days', 0)}",
            "",
        ])

    overall = summarize(rows)
    if overall:
        lines.extend([
            "## Overall Summary",
            "",
            f"- Average bodyweight: {fmt(overall['avg'])} kg",
            f"- Lowest bodyweight: {fmt(overall['min'])} kg",
            f"- Highest bodyweight: {fmt(overall['max'])} kg",
            f"- First logged day: {rows[0]['date']} ({fmt(overall['start'])} kg)",
            f"- Last logged day: {rows[-1]['date']} ({fmt(overall['end'])} kg)",
            f"- Net change across export: {fmt(overall['delta'])} kg",
            "",
        ])

    yearly = defaultdict(list)
    monthly = defaultdict(list)
    for row in rows:
        yearly[row["date"][:4]].append(row)
        monthly[row["date"][:7]].append(row)

    lines.extend(["## Yearly Summary", "", "| Year | Days | Avg | Low | High | Start | End | Delta |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for year in sorted(yearly):
        s = summarize(yearly[year])
        if not s:
            continue
        lines.append(f"| {year} | {s['days']} | {fmt(s['avg'])} kg | {fmt(s['min'])} kg | {fmt(s['max'])} kg | {fmt(s['start'])} kg | {fmt(s['end'])} kg | {fmt(s['delta'])} kg |")
    lines.append("")

    lines.extend(["## Month-by-Month Summary", "", "| Month | Days | Avg | Low | High | Start | End | Delta |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for month in sorted(monthly):
        s = summarize(monthly[month])
        if not s:
            continue
        lines.append(f"| {month} | {s['days']} | {fmt(s['avg'])} kg | {fmt(s['min'])} kg | {fmt(s['max'])} kg | {fmt(s['start'])} kg | {fmt(s['end'])} kg | {fmt(s['delta'])} kg |")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    print(f"Rendered body weight summary: {output_path}")


def main():
    repo = Path(__file__).resolve().parents[1]
    body_metadata, rows = load_days(repo / "values" / "body_weight_history.json")
    render(body_metadata, rows, repo / "outputs" / "body_weight_history.md")


if __name__ == "__main__":
    main()
