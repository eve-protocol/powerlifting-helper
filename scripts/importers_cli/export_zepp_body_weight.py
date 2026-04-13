#!/usr/bin/env python3
"""Extract daily Zepp/Xiaomi body-weight history from a password-protected ZIP export."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path

import pyzipper

from health_metrics import JST


def maybe_float(value):
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata")
    args = parser.parse_args()

    zip_path = Path(args.zip)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    export_meta = {}
    if args.metadata and Path(args.metadata).exists():
        export_meta = json.loads(Path(args.metadata).read_text())

    with pyzipper.AESZipFile(zip_path) as zf:
        zf.setpassword(args.password.encode())
        body_name = next((name for name in zf.namelist() if name.startswith("BODY/") and name.endswith(".csv")), None)
        if not body_name:
            raise SystemExit("Could not find BODY/*.csv inside the Zepp export ZIP")

        with zf.open(body_name) as body_fp:
            reader = csv.DictReader(TextIOWrapper(body_fp, encoding="utf-8-sig", newline=""))
            latest_by_day = {}
            for row in reader:
                ts = datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S%z")
                date_jst = ts.astimezone(JST).date().isoformat()
                payload = {
                    "date": date_jst,
                    "measured_at": ts.astimezone(JST).isoformat(),
                    "weight_kg": maybe_float(row.get("weight")),
                    "bmi": maybe_float(row.get("bmi")),
                    "fat_rate": maybe_float(row.get("fatRate")),
                    "body_water_rate": maybe_float(row.get("bodyWaterRate")),
                    "bone_mass_kg": maybe_float(row.get("boneMass")),
                    "basal_metabolism_kcal": maybe_float(row.get("metabolism")),
                    "muscle_rate": maybe_float(row.get("muscleRate")),
                    "visceral_fat": maybe_float(row.get("visceralFat")),
                    "source": {
                        "platform": "Zepp Life",
                        "export_member": body_name,
                    },
                }
                current = latest_by_day.get(date_jst)
                if current is None or payload["measured_at"] > current["measured_at"]:
                    latest_by_day[date_jst] = payload

    days = [latest_by_day[date] for date in sorted(latest_by_day)]
    result = {
        "metadata": {
            "source": "Zepp Life body export",
            "drive_file_id": export_meta.get("id"),
            "drive_file_name": export_meta.get("name"),
            "export_file_modified_time": export_meta.get("modifiedTime"),
            "zip_member": body_name,
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
