#!/usr/bin/env python3
"""Render merged bodyweight timeline output (Markdown only)."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from health_metrics import load_health_daily


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
    lift_map = {
        "Squat (Low Bar)": "squat",
        "Bench Press (Paused)": "bench",
        "Bench Press (Barbell)": "bench",
        "Sumo Deadlift (Barbell)": "deadlift",
        "Sumo Deadlift (Paused)": "deadlift",
    }

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
            current_lift = lift_map.get(line[4:])
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


def build_trend_svg(monthly_bodyweight, monthly_strength, title_suffix):
    months = sorted(m for m in monthly_bodyweight if any(monthly_strength.get(m, {}).values()))
    if not months:
        return None

    first_month = next(iter(monthly_strength))
    squat_label = next(k for k in monthly_strength[first_month] if 'squat' in k.lower())
    bench_label = next(k for k in monthly_strength[first_month] if 'bench' in k.lower())
    deadlift_label = next(k for k in monthly_strength[first_month] if 'deadlift' in k.lower())

    series = {
        "Bodyweight": [monthly_bodyweight[m]["avg"] for m in months],
        squat_label: [monthly_strength.get(m, {}).get(squat_label) for m in months],
        bench_label: [monthly_strength.get(m, {}).get(bench_label) for m in months],
        deadlift_label: [monthly_strength.get(m, {}).get(deadlift_label) for m in months],
    }
    baselines = {name: next((v for v in values if v is not None), None) for name, values in series.items()}
    normalized = {
        name: [None if v is None or baselines[name] in (None, 0) else (v / baselines[name]) * 100 for v in values]
        for name, values in series.items()
    }

    all_vals = [v for values in normalized.values() for v in values if v is not None]
    if not all_vals:
        return None

    width, height = 980, 420
    left, right, top, bottom = 70, 20, 30, 55
    plot_w = width - left - right
    plot_h = height - top - bottom
    y_min = int(min(all_vals) - 3)
    y_max = int(max(all_vals) + 3)
    if y_max <= y_min:
        y_max = y_min + 10

    def x_pos(idx):
        return left + (idx / max(len(months) - 1, 1)) * plot_w

    def y_pos(val):
        return top + (1 - ((val - y_min) / (y_max - y_min))) * plot_h

    colors = {
        "Bodyweight": "#111827",
        squat_label: "#2563eb",
        bench_label: "#16a34a",
        deadlift_label: "#dc2626",
    }

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="980" height="420" viewBox="0 0 980 420">',
        '<style>text{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;fill:#333}.small{font-size:12px}.label{font-size:14px;font-weight:600}.title{font-size:18px;font-weight:700}.grid{stroke:#e5e7eb;stroke-width:1}.axis{stroke:#666;stroke-width:1.5}.bw{stroke:#111827;fill:none;stroke-width:2.5}.sq{stroke:#2563eb;fill:none;stroke-width:2.5}.bp{stroke:#16a34a;fill:none;stroke-width:2.5}.dl{stroke:#dc2626;fill:none;stroke-width:2.5}</style>',
        '<rect x="0" y="0" width="980" height="420" fill="white"/>',
        f'<text class="title" x="{left}" y="20">Bodyweight vs strength trend, monthly, normalized to first available month = 100 ({title_suffix})</text>',
    ]

    for tick in range(y_min, y_max + 1, 2):
        yp = y_pos(tick)
        svg.append(f'<line class="grid" x1="{left}" y1="{yp:.1f}" x2="{width-right}" y2="{yp:.1f}" />')
        svg.append(f'<text class="small" x="{left-8}" y="{yp+4:.1f}" text-anchor="end">{tick}</text>')

    for idx, month in enumerate(months):
        xp = x_pos(idx)
        if month.endswith("-01") or month.endswith("-07") or idx == 0 or idx == len(months) - 1:
            svg.append(f'<line class="grid" x1="{xp:.1f}" y1="{top}" x2="{xp:.1f}" y2="{height-bottom}" />')
            svg.append(f'<text class="small" x="{xp:.1f}" y="{height-bottom+18}" text-anchor="middle">{month}</text>')

    svg.append(f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" />')
    svg.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" />')

    class_map = {"Bodyweight": "bw", squat_label: "sq", bench_label: "bp", deadlift_label: "dl"}
    for name, values in normalized.items():
        pts = [f"{x_pos(i):.1f},{y_pos(v):.1f}" for i, v in enumerate(values) if v is not None]
        if len(pts) >= 2:
            svg.append(f'<polyline class="{class_map[name]}" points="{" ".join(pts)}" />')

    legend_y = 36
    legend_x = left
    for idx, name in enumerate(["Bodyweight", squat_label, bench_label, deadlift_label]):
        x = legend_x + idx * 210
        svg.append(f'<line x1="{x}" y1="{legend_y}" x2="{x+22}" y2="{legend_y}" stroke="{colors[name]}" stroke-width="3" />')
        svg.append(f'<text class="small" x="{x+28}" y="{legend_y+4}">{name}</text>')

    svg.append(f'<text class="label" x="{width/2:.1f}" y="{height-12}" text-anchor="middle">Month</text>')
    svg.append(f'<text class="label" x="22" y="{height/2:.1f}" text-anchor="middle" transform="rotate(-90 22 {height/2:.1f})">Index, first available month = 100</text>')
    svg.append('</svg>')
    return "\n".join(svg)


def render_png_from_svg(svg_text: str, output_path: Path):
    with tempfile.TemporaryDirectory() as tmpdir:
        svg_path = Path(tmpdir) / "trend.svg"
        svg_path.write_text(svg_text)
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(svg_path), str(output_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def chart_block(lines, outputs: Path, monthly_bodyweight, monthly_strength, filename: str, heading: str, description: str, title_suffix: str, legend_labels: dict[str, str]):
    renamed_strength = {
        month: {
            legend_labels["squat"]: values.get("squat"),
            legend_labels["bench"]: values.get("bench"),
            legend_labels["deadlift"]: values.get("deadlift"),
        }
        for month, values in monthly_strength.items()
    }
    svg = build_trend_svg(monthly_bodyweight, renamed_strength, title_suffix)
    if not svg:
        return
    png_path = outputs / filename
    render_png_from_svg(svg, png_path)
    lines.extend([
        heading,
        "",
        description,
        "It is normalized so the first available month for each series = 100, which makes trend comparison easier than mixing kg scales.",
        "",
        f"![{heading.strip('# ').lower()}]({filename})",
        "",
    ])


def main():
    repo = Path(__file__).resolve().parents[1]
    merged = load_health_daily(repo)
    rows = [merged[d] for d in sorted(merged) if merged[d].get("weight_kg") is not None]
    outputs = repo / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    monthly = defaultdict(list)
    for row in rows:
        monthly[row["date"][:7]].append(row)
    monthly_e1rm, monthly_actual = load_monthly_strength(repo)
    monthly_bodyweight = {month: summarize(month_rows) for month, month_rows in monthly.items()}

    lines = [
        "# Merged Body Weight Timeline",
        "",
        "This view merges old Zepp/Xiaomi scale history with newer Health Connect / VeSync weight entries.",
        "",
    ]

    chart_block(
        lines,
        outputs,
        monthly_bodyweight,
        monthly_e1rm,
        "body_weight_timeline_chart_e1rm.png",
        "## Trend Chart, e1RM",
        "This chart compares monthly average bodyweight to monthly best estimated 1RM, e1RM, for squat, bench, and deadlift.",
        "e1RM",
        {"squat": "Squat e1RM", "bench": "Bench e1RM", "deadlift": "Deadlift e1RM"},
    )
    chart_block(
        lines,
        outputs,
        monthly_bodyweight,
        monthly_actual,
        "body_weight_timeline_chart_actual.png",
        "## Trend Chart, actual top singles",
        "This chart compares monthly average bodyweight to monthly best actual single, 1 rep logged weight, for squat, bench, and deadlift.",
        "actual 1RM proxy, top single",
        {"squat": "Squat actual single", "bench": "Bench actual single", "deadlift": "Deadlift actual single"},
    )

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
