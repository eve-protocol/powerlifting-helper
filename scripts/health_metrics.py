#!/usr/bin/env python3
"""Shared helpers for Health Connect daily metric export/rendering."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

JST = timezone(timedelta(hours=9))
EPOCH = date(1970, 1, 1)
GARMIN_PACKAGE = "com.garmin.android.apps.connectmobile"
GOOGLE_FIT_PACKAGE = "com.google.android.apps.fitness"

SLEEP_STAGE_LABELS = {
    1: "awake",
    4: "light",
    5: "deep",
    6: "rem",
}


def jst_date_to_day_number(date_str: str) -> int:
    return (date.fromisoformat(date_str) - EPOCH).days


def day_number_to_jst_date(day_number: int) -> str:
    return str(EPOCH + timedelta(days=day_number))


def ms_to_jst_datetime(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(JST)


def ms_to_jst_iso(ms: int) -> str:
    return ms_to_jst_datetime(ms).isoformat()


def period_quarter(date_str: str) -> str:
    d = date.fromisoformat(date_str)
    return f"{d.year}-Q{((d.month - 1) // 3) + 1}"


def period_month(date_str: str) -> str:
    return date_str[:7]


def period_year(date_str: str) -> str:
    return date_str[:4]


def fmt_num(x, digits=1):
    if x is None:
        return "-"
    if isinstance(x, int):
        return str(x)
    if round(x, digits).is_integer():
        return str(int(round(x, digits)))
    return f"{x:.{digits}f}"


def fmt_delta(x, digits=1, suffix=""):
    if x is None:
        return "n/a"
    arrow = "↑" if x > 0 else ("↓" if x < 0 else "→")
    abs_x = abs(x)
    if round(abs_x, digits).is_integer():
        return f"{arrow} {int(round(abs_x, digits))}{suffix}"
    return f"{arrow} {abs_x:.{digits}f}{suffix}"


def load_health_daily(repo_root: Path) -> Dict[str, dict]:
    path = repo_root / "values" / "health_daily.json"
    health_daily = {}
    if path.exists():
        data = json.loads(path.read_text())
        health_daily = {row["date"]: row for row in data.get("days", [])}

    body_path = repo_root / "values" / "body_weight_history.json"
    if body_path.exists():
        body_data = json.loads(body_path.read_text())
        for row in body_data.get("days", []):
            date_str = row["date"]
            if date_str not in health_daily:
                health_daily[date_str] = {
                    "date": date_str,
                    "steps": None,
                    "distance_km": None,
                    "total_kcal_burned": None,
                    "weight_kg": row.get("weight_kg"),
                    "resting_hr_bpm": None,
                    "sleep": None,
                    "sources": {
                        "steps": None,
                        "distance": None,
                        "total_kcal_burned": None,
                        "weight": {
                            "time": row.get("measured_at"),
                            "weight_kg": row.get("weight_kg"),
                            "package_name": "com.xiaomi.hm.health",
                            "app_name": "Zepp Life",
                        },
                        "resting_hr": None,
                        "sleep": None,
                    },
                    "available_sources": {
                        "steps": [],
                        "distance": [],
                        "total_kcal_burned": [],
                    },
                    "freshness": {
                        "latest_date_in_export": body_data.get("metadata", {}).get("latest_date_in_export"),
                        "warning": None,
                    },
                }
            elif health_daily[date_str].get("weight_kg") is None and row.get("weight_kg") is not None:
                health_daily[date_str]["weight_kg"] = row.get("weight_kg")
                health_daily[date_str].setdefault("sources", {})["weight"] = {
                    "time": row.get("measured_at"),
                    "weight_kg": row.get("weight_kg"),
                    "package_name": "com.xiaomi.hm.health",
                    "app_name": "Zepp Life",
                }

    return health_daily


def format_health_summary_block(day: Optional[dict]) -> List[str]:
    if not day:
        return []

    lines = ["### Health / Recovery", ""]
    freshness = day.get("freshness")
    if freshness and freshness.get("warning"):
        lines.append(f"- Warning: {freshness['warning']}")

    if day.get("steps") is not None:
        lines.append(f"- Steps: {day['steps']}")
    if day.get("distance_km") is not None:
        lines.append(f"- Distance: {fmt_num(day['distance_km'], 2)} km")
    if day.get("total_kcal_burned") is not None:
        lines.append(f"- Total kcal burned: {day['total_kcal_burned']}")
    if day.get("weight_kg") is not None:
        lines.append(f"- Weight: {fmt_num(day['weight_kg'], 1)} kg")
    if day.get("resting_hr_bpm") is not None:
        lines.append(f"- Resting heart rate: {day['resting_hr_bpm']} bpm")

    sleep = day.get("sleep")
    if sleep:
        lines.append(
            f"- Sleep: {fmt_num(sleep.get('asleep_minutes', 0) / 60, 2)} h asleep "
            f"({fmt_num(sleep.get('time_in_bed_minutes', 0) / 60, 2)} h in bed, "
            f"deep {fmt_num(sleep.get('deep_minutes', 0) / 60, 2)} h, "
            f"REM {fmt_num(sleep.get('rem_minutes', 0) / 60, 2)} h, "
            f"awake {fmt_num(sleep.get('awake_minutes', 0) / 60, 2)} h)"
        )

    lines.append("")
    return lines


def summarize_health_group(rows: Iterable[dict]) -> Optional[dict]:
    rows = [r for r in rows if r]
    if not rows:
        return None

    def avg(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    steps = [r.get("steps") for r in rows]
    distance = [r.get("distance_km") for r in rows]
    kcal = [r.get("total_kcal_burned") for r in rows]
    weight = [r.get("weight_kg") for r in rows]
    rhr = [r.get("resting_hr_bpm") for r in rows]
    asleep = [r.get("sleep", {}).get("asleep_minutes") for r in rows if r.get("sleep")]
    deep = [r.get("sleep", {}).get("deep_minutes") for r in rows if r.get("sleep")]
    rem = [r.get("sleep", {}).get("rem_minutes") for r in rows if r.get("sleep")]

    latest = max(rows, key=lambda r: r["date"])

    return {
        "days_with_data": len(rows),
        "avg_steps": round(sum(v for v in steps if v is not None) / len([v for v in steps if v is not None]), 0) if any(v is not None for v in steps) else None,
        "avg_distance_km": avg(distance),
        "avg_total_kcal": round(sum(v for v in kcal if v is not None) / len([v for v in kcal if v is not None]), 0) if any(v is not None for v in kcal) else None,
        "avg_weight_kg": avg(weight),
        "avg_resting_hr_bpm": avg(rhr),
        "avg_sleep_hours": round((sum(asleep) / len(asleep)) / 60, 2) if asleep else None,
        "avg_deep_sleep_hours": round((sum(deep) / len(deep)) / 60, 2) if deep else None,
        "avg_rem_sleep_hours": round((sum(rem) / len(rem)) / 60, 2) if rem else None,
        "latest_health_date": latest["date"],
        "freshness_warning": latest.get("freshness", {}).get("warning"),
    }


def add_health_deltas(scorecards: Dict[str, dict], periods: List[str]):
    for idx, period in enumerate(periods):
        cur = scorecards.get(period)
        if not cur:
            continue
        prev = scorecards.get(periods[idx + 1]) if idx + 1 < len(periods) else None
        cur["delta"] = {
            "avg_steps": (cur["avg_steps"] - prev["avg_steps"]) if prev and cur["avg_steps"] is not None and prev["avg_steps"] is not None else None,
            "avg_distance_km": (cur["avg_distance_km"] - prev["avg_distance_km"]) if prev and cur["avg_distance_km"] is not None and prev["avg_distance_km"] is not None else None,
            "avg_total_kcal": (cur["avg_total_kcal"] - prev["avg_total_kcal"]) if prev and cur["avg_total_kcal"] is not None and prev["avg_total_kcal"] is not None else None,
            "avg_weight_kg": (cur["avg_weight_kg"] - prev["avg_weight_kg"]) if prev and cur["avg_weight_kg"] is not None and prev["avg_weight_kg"] is not None else None,
            "avg_resting_hr_bpm": (cur["avg_resting_hr_bpm"] - prev["avg_resting_hr_bpm"]) if prev and cur["avg_resting_hr_bpm"] is not None and prev["avg_resting_hr_bpm"] is not None else None,
            "avg_sleep_hours": (cur["avg_sleep_hours"] - prev["avg_sleep_hours"]) if prev and cur["avg_sleep_hours"] is not None and prev["avg_sleep_hours"] is not None else None,
        }


def render_health_scorecard_section(lines: List[str], summary: Optional[dict], prev_summary: Optional[dict]):
    if not summary:
        return
    delta = summary.get("delta", {})
    lines.append("### Health / Recovery")
    lines.append("")
    lines.append("| Metric | Current | Previous | Delta |")
    lines.append("|---|---:|---:|---:|")
    rows = [
        ("Days with data", fmt_num(summary.get("days_with_data"), 0), fmt_num(prev_summary.get("days_with_data"), 0) if prev_summary else '-', fmt_delta((summary.get("days_with_data") - prev_summary.get("days_with_data")) if prev_summary else None, 0)),
        ("Avg steps/day", fmt_num(summary.get("avg_steps"), 0), fmt_num(prev_summary.get("avg_steps"), 0) if prev_summary else '-', fmt_delta(delta.get("avg_steps"), 0)),
        ("Avg distance/day", f"{fmt_num(summary.get('avg_distance_km'), 2)}km", f"{fmt_num(prev_summary.get('avg_distance_km'), 2)}km" if prev_summary and prev_summary.get('avg_distance_km') is not None else '-', fmt_delta(delta.get("avg_distance_km"), 2, 'km')),
        ("Avg kcal/day", fmt_num(summary.get("avg_total_kcal"), 0), fmt_num(prev_summary.get("avg_total_kcal"), 0) if prev_summary else '-', fmt_delta(delta.get("avg_total_kcal"), 0)),
        ("Avg bodyweight", f"{fmt_num(summary.get('avg_weight_kg'), 1)}kg", f"{fmt_num(prev_summary.get('avg_weight_kg'), 1)}kg" if prev_summary and prev_summary.get('avg_weight_kg') is not None else '-', fmt_delta(delta.get("avg_weight_kg"), 1, 'kg')),
        ("Avg resting HR", f"{fmt_num(summary.get('avg_resting_hr_bpm'), 1)}bpm", f"{fmt_num(prev_summary.get('avg_resting_hr_bpm'), 1)}bpm" if prev_summary and prev_summary.get('avg_resting_hr_bpm') is not None else '-', fmt_delta(delta.get("avg_resting_hr_bpm"), 1, 'bpm')),
        ("Avg sleep", f"{fmt_num(summary.get('avg_sleep_hours'), 2)}h", f"{fmt_num(prev_summary.get('avg_sleep_hours'), 2)}h" if prev_summary and prev_summary.get('avg_sleep_hours') is not None else '-', fmt_delta(delta.get("avg_sleep_hours"), 2, 'h')),
    ]
    for metric, cur, prev, diff in rows:
        lines.append(f"| {metric} | {cur} | {prev} | {diff} |")
    lines.append("")
    lines.append(f"- Latest health date in period: {summary['latest_health_date']}")
    if summary.get("freshness_warning"):
        lines.append(f"- Warning: {summary['freshness_warning']}")
    lines.append("")
