#!/usr/bin/env python3
"""Render a simple SVG bodyweight graph with X/Y axes."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


def load_rows(path: Path):
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    return [row for row in payload.get("days", []) if row.get("weight_kg") is not None]


def nice_step(span: float) -> float:
    if span <= 6:
        return 1
    if span <= 15:
        return 2
    return 5


def main():
    repo = Path(__file__).resolve().parents[1]
    rows = load_rows(repo / "values" / "body_weight_history.json")
    if not rows:
        raise SystemExit("No body weight history found")

    dates = [date.fromisoformat(r["date"]) for r in rows]
    weights = [float(r["weight_kg"]) for r in rows]

    width, height = 1200, 520
    left, right, top, bottom = 80, 30, 30, 60
    plot_w = width - left - right
    plot_h = height - top - bottom

    min_w = min(weights)
    max_w = max(weights)
    pad = 1.0
    y_min = int(min_w - pad)
    y_max = int(max_w + pad + 0.9999)
    y_step = nice_step(y_max - y_min)

    start_d = min(dates)
    end_d = max(dates)
    total_days = max((end_d - start_d).days, 1)

    def x_pos(d: date) -> float:
        return left + (((d - start_d).days) / total_days) * plot_w

    def y_pos(w: float) -> float:
        return top + (1 - ((w - y_min) / (y_max - y_min))) * plot_h

    points = " ".join(f"{x_pos(d):.1f},{y_pos(w):.1f}" for d, w in zip(dates, weights))

    month_ticks = []
    seen = set()
    for d in dates:
        key = (d.year, d.month)
        if key in seen:
            continue
        seen.add(key)
        first = date(d.year, d.month, 1)
        month_ticks.append(first)

    y_ticks = []
    tick = y_min - (y_min % y_step)
    while tick <= y_max:
        if tick >= y_min:
            y_ticks.append(tick)
        tick += y_step

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg.append('<style>text{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;fill:#333} .small{font-size:12px} .label{font-size:14px;font-weight:600} .title{font-size:20px;font-weight:700} .grid{stroke:#e5e7eb;stroke-width:1} .axis{stroke:#666;stroke-width:1.5} .line{fill:none;stroke:#2563eb;stroke-width:2.5} .dot{fill:#2563eb}</style>')
    svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="white"/>')
    svg.append(f'<text class="title" x="{left}" y="22">Body Weight History</text>')

    for y in y_ticks:
        yp = y_pos(y)
        svg.append(f'<line class="grid" x1="{left}" y1="{yp:.1f}" x2="{width-right}" y2="{yp:.1f}" />')
        svg.append(f'<text class="small" x="{left-10}" y="{yp+4:.1f}" text-anchor="end">{y} kg</text>')

    for d in month_ticks:
        xp = x_pos(d)
        svg.append(f'<line class="grid" x1="{xp:.1f}" y1="{top}" x2="{xp:.1f}" y2="{height-bottom}" />')
        label = d.strftime('%Y-%m') if d.month == 1 or d == month_ticks[0] else d.strftime('%m')
        svg.append(f'<text class="small" x="{xp:.1f}" y="{height-bottom+20}" text-anchor="middle">{label}</text>')

    svg.append(f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" />')
    svg.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" />')
    svg.append(f'<polyline class="line" points="{points}" />')

    for d, w in zip(dates[::max(len(dates)//60,1)], weights[::max(len(weights)//60,1)]):
        svg.append(f'<circle class="dot" cx="{x_pos(d):.1f}" cy="{y_pos(w):.1f}" r="2.2" />')

    svg.append(f'<text class="label" x="{width/2:.1f}" y="{height-15}" text-anchor="middle">Date</text>')
    svg.append(f'<text class="label" x="22" y="{height/2:.1f}" text-anchor="middle" transform="rotate(-90 22 {height/2:.1f})">Body weight (kg)</text>')
    svg.append('</svg>')

    out = repo / "outputs" / "body_weight_history.svg"
    out.write_text("\n".join(svg))
    print(f"Rendered body weight graph: {out}")


if __name__ == "__main__":
    main()
