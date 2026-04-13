#!/usr/bin/env python3
"""Extract daily wellness and sleep history from a Garmin GDPR export ZIP."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def load_json_from_zip(zf: zipfile.ZipFile, name: str):
    with zf.open(name) as fp:
        return json.load(fp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata")
    args = parser.parse_args()

    zip_path = Path(args.zip)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    export_meta = {}
    if args.metadata and Path(args.metadata).exists():
        export_meta = json.loads(Path(args.metadata).read_text())

    daily = {}
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        uds_files = sorted(n for n in names if n.startswith("DI_CONNECT/DI-Connect-Aggregator/UDSFile_") and n.endswith(".json"))
        sleep_files = sorted(n for n in names if n.startswith("DI_CONNECT/DI-Connect-Wellness/") and n.endswith("_sleepData.json"))

        for name in uds_files:
            for row in load_json_from_zip(zf, name):
                date_str = row.get("calendarDate")
                if not date_str:
                    continue
                day = daily.setdefault(date_str, {"date": date_str})
                day["steps"] = row.get("totalSteps")
                distance = row.get("totalDistanceMeters")
                day["distance_km"] = round(distance / 1000, 3) if distance is not None else None
                kcal = row.get("wellnessKilocalories")
                if kcal is None:
                    kcal = row.get("totalKilocalories")
                day["total_kcal_burned"] = int(round(kcal)) if kcal is not None else None
                rhr = row.get("restingHeartRate")
                if rhr is None:
                    rhr = row.get("currentDayRestingHeartRate")
                day["resting_hr_bpm"] = rhr
                day.setdefault("sleep", None)
                day.setdefault("weight_kg", None)

        for name in sleep_files:
            for row in load_json_from_zip(zf, name):
                date_str = row.get("calendarDate")
                if not date_str:
                    continue
                day = daily.setdefault(date_str, {"date": date_str})
                deep = row.get("deepSleepSeconds", 0) or 0
                light = row.get("lightSleepSeconds", 0) or 0
                rem = row.get("remSleepSeconds", 0) or 0
                awake = row.get("awakeSleepSeconds", 0) or 0
                day["sleep"] = {
                    "package_name": "com.garmin.android.apps.connectmobile",
                    "app_name": "Garmin Connect (GDPR export)",
                    "sleep_start": row.get("sleepStartTimestampGMT"),
                    "sleep_end": row.get("sleepEndTimestampGMT"),
                    "time_in_bed_minutes": round((deep + light + rem + awake) / 60, 1),
                    "asleep_minutes": round((deep + light + rem) / 60, 1),
                    "awake_minutes": round(awake / 60, 1),
                    "light_minutes": round(light / 60, 1),
                    "deep_minutes": round(deep / 60, 1),
                    "rem_minutes": round(rem / 60, 1),
                }
                day.setdefault("weight_kg", None)

    days = [daily[d] for d in sorted(daily)]
    result = {
        "metadata": {
            "source": "Garmin GDPR export",
            "drive_file_id": export_meta.get("id"),
            "drive_file_name": export_meta.get("name"),
            "export_file_modified_time": export_meta.get("modifiedTime"),
            "earliest_date_in_export": days[0]["date"] if days else None,
            "latest_date_in_export": days[-1]["date"] if days else None,
            "total_days": len(days),
        },
        "days": days,
    }
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result["metadata"], indent=2))


if __name__ == "__main__":
    main()
