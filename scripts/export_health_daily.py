#!/usr/bin/env python3
"""Parse Health Connect SQLite export into normalized daily Garmin-first metrics."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from health_metrics import (
    GARMIN_PACKAGE,
    GOOGLE_FIT_PACKAGE,
    JST,
    SLEEP_STAGE_LABELS,
    day_number_to_jst_date,
    ms_to_jst_datetime,
    ms_to_jst_iso,
)


def pick_preferred(rows):
    if not rows:
        return None
    for row in rows:
        if row["package_name"] == GARMIN_PACKAGE:
            return row
    non_fit = [r for r in rows if r["package_name"] != GOOGLE_FIT_PACKAGE]
    if non_fit:
        return non_fit[0]
    return rows[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata")
    parser.add_argument("--timezone", default="Asia/Tokyo")
    parser.add_argument("--max-staleness-days", type=int, default=2)
    args = parser.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    export_meta = {}
    if args.metadata and Path(args.metadata).exists():
        export_meta = json.loads(Path(args.metadata).read_text())

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    app_by_id = {r["row_id"]: dict(r) for r in cur.execute("SELECT row_id, package_name, app_name FROM application_info_table")}

    rows_by_day = defaultdict(lambda: {
        "steps_candidates": [],
        "distance_candidates": [],
        "kcal_candidates": [],
        "weight_entries": [],
        "resting_hr_entries": [],
        "sleep_candidates": [],
    })

    for row in cur.execute("SELECT local_date, app_info_id, SUM(count) total_steps FROM steps_record_table GROUP BY local_date, app_info_id"):
        app = app_by_id.get(row["app_info_id"], {})
        rows_by_day[row["local_date"]]["steps_candidates"].append({
            "package_name": app.get("package_name"),
            "app_name": app.get("app_name"),
            "steps": int(row["total_steps"] or 0),
        })

    for row in cur.execute("SELECT local_date, app_info_id, SUM(distance) total_distance FROM distance_record_table GROUP BY local_date, app_info_id"):
        app = app_by_id.get(row["app_info_id"], {})
        rows_by_day[row["local_date"]]["distance_candidates"].append({
            "package_name": app.get("package_name"),
            "app_name": app.get("app_name"),
            "distance_km": round(float(row["total_distance"] or 0) / 1000, 3),
        })

    for row in cur.execute("SELECT local_date, app_info_id, SUM(energy) total_energy FROM total_calories_burned_record_table GROUP BY local_date, app_info_id"):
        app = app_by_id.get(row["app_info_id"], {})
        rows_by_day[row["local_date"]]["kcal_candidates"].append({
            "package_name": app.get("package_name"),
            "app_name": app.get("app_name"),
            "total_kcal_burned": int(round(float(row["total_energy"] or 0) / 1000)),
        })

    for row in cur.execute("SELECT local_date, time, weight, app_info_id FROM weight_record_table ORDER BY time"):
        app = app_by_id.get(row["app_info_id"], {})
        rows_by_day[row["local_date"]]["weight_entries"].append({
            "time": ms_to_jst_iso(row["time"]),
            "weight_kg": round(float(row["weight"] or 0) / 1000, 1),
            "package_name": app.get("package_name"),
            "app_name": app.get("app_name"),
        })

    for row in cur.execute("SELECT local_date, time, beats_per_minute, app_info_id FROM resting_heart_rate_record_table ORDER BY time"):
        app = app_by_id.get(row["app_info_id"], {})
        rows_by_day[row["local_date"]]["resting_hr_entries"].append({
            "time": ms_to_jst_iso(row["time"]),
            "resting_hr_bpm": int(row["beats_per_minute"]),
            "package_name": app.get("package_name"),
            "app_name": app.get("app_name"),
        })

    sleep_rows = cur.execute("SELECT row_id, local_date, start_time, end_time, app_info_id FROM sleep_session_record_table ORDER BY end_time").fetchall()
    for row in sleep_rows:
        wake_date = ms_to_jst_datetime(row["end_time"]).date().isoformat()
        wake_day_number = (ms_to_jst_datetime(row["end_time"]).date() - datetime(1970, 1, 1).date()).days
        app = app_by_id.get(row["app_info_id"], {})
        stage_rows = cur.execute("SELECT stage_start_time, stage_end_time, stage_type FROM sleep_stages_table WHERE parent_key=? ORDER BY stage_start_time", (row["row_id"],)).fetchall()
        stage_minutes = defaultdict(float)
        for st in stage_rows:
            stage_minutes[st["stage_type"]] += (st["stage_end_time"] - st["stage_start_time"]) / 1000 / 60
        asleep = stage_minutes.get(4, 0) + stage_minutes.get(5, 0) + stage_minutes.get(6, 0)
        rows_by_day[wake_day_number]["sleep_candidates"].append({
            "wake_date": wake_date,
            "package_name": app.get("package_name"),
            "app_name": app.get("app_name"),
            "sleep_start": ms_to_jst_iso(row["start_time"]),
            "sleep_end": ms_to_jst_iso(row["end_time"]),
            "time_in_bed_minutes": round((row["end_time"] - row["start_time"]) / 1000 / 60, 1),
            "asleep_minutes": round(asleep, 1),
            "awake_minutes": round(stage_minutes.get(1, 0), 1),
            "light_minutes": round(stage_minutes.get(4, 0), 1),
            "deep_minutes": round(stage_minutes.get(5, 0), 1),
            "rem_minutes": round(stage_minutes.get(6, 0), 1),
            "sleep_stages_minutes": {SLEEP_STAGE_LABELS.get(k, str(k)): round(v, 1) for k, v in stage_minutes.items()},
        })

    latest_day = max(rows_by_day.keys()) if rows_by_day else None
    latest_date = day_number_to_jst_date(latest_day) if latest_day is not None else None
    export_stale_warning = None
    if latest_date:
        today_jst = datetime.now(JST).date()
        latest_export_date = datetime.fromisoformat(latest_date).date()
        staleness_days = (today_jst - latest_export_date).days
        if staleness_days > args.max_staleness_days:
            export_stale_warning = f"Health data looks stale, latest available date is {latest_date}."

    days = []
    for day_number in sorted(rows_by_day.keys()):
        payload = rows_by_day[day_number]
        date_str = day_number_to_jst_date(day_number)
        selected_steps = pick_preferred(payload["steps_candidates"])
        selected_distance = pick_preferred(payload["distance_candidates"])
        selected_kcal = pick_preferred(payload["kcal_candidates"])
        selected_sleep = pick_preferred(payload["sleep_candidates"])
        latest_weight = payload["weight_entries"][-1] if payload["weight_entries"] else None
        latest_rhr = payload["resting_hr_entries"][-1] if payload["resting_hr_entries"] else None

        days.append({
            "date": date_str,
            "steps": selected_steps.get("steps") if selected_steps else None,
            "distance_km": selected_distance.get("distance_km") if selected_distance else None,
            "total_kcal_burned": selected_kcal.get("total_kcal_burned") if selected_kcal else None,
            "weight_kg": latest_weight.get("weight_kg") if latest_weight else None,
            "resting_hr_bpm": latest_rhr.get("resting_hr_bpm") if latest_rhr else None,
            "sleep": selected_sleep,
            "sources": {
                "steps": selected_steps,
                "distance": selected_distance,
                "total_kcal_burned": selected_kcal,
                "weight": latest_weight,
                "resting_hr": latest_rhr,
                "sleep": selected_sleep,
            },
            "available_sources": {
                "steps": payload["steps_candidates"],
                "distance": payload["distance_candidates"],
                "total_kcal_burned": payload["kcal_candidates"],
            },
            "freshness": {
                "latest_date_in_export": latest_date,
                "warning": export_stale_warning,
            },
        })

    result = {
        "metadata": {
            "source": "Health Connect export",
            "preferred_package": GARMIN_PACKAGE,
            "ignored_when_garmin_present": [GOOGLE_FIT_PACKAGE],
            "export_file_modified_time": export_meta.get("modifiedTime"),
            "drive_file_id": export_meta.get("id"),
            "drive_file_name": export_meta.get("name"),
            "latest_date_in_export": latest_date,
            "stale_warning": export_stale_warning,
            "total_days": len(days),
        },
        "days": days,
    }
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result["metadata"], indent=2))


if __name__ == "__main__":
    main()
