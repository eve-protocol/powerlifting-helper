#!/usr/bin/env python3
"""Download Health Connect export ZIP from Google Drive via service-account secrets."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DRIVE_FILE_URL = "https://www.googleapis.com/drive/v3/files/{file_id}"


def build_credentials_from_env():
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(raw)
    if "private_key" in info and isinstance(info["private_key"], str):
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(Request())
    return creds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file-id", default=os.environ.get("HEALTH_CONNECT_DRIVE_FILE_ID"), required=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata-output")
    args = parser.parse_args()

    if not args.file_id:
        raise SystemExit("Missing --file-id or HEALTH_CONNECT_DRIVE_FILE_ID")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    creds = build_credentials_from_env()
    headers = {"Authorization": f"Bearer {creds.token}"}

    meta_resp = requests.get(
        DRIVE_FILE_URL.format(file_id=args.file_id),
        headers=headers,
        params={"fields": "id,name,mimeType,size,modifiedTime"},
        timeout=60,
    )
    meta_resp.raise_for_status()
    metadata = meta_resp.json()

    file_resp = requests.get(
        DRIVE_FILE_URL.format(file_id=args.file_id),
        headers=headers,
        params={"alt": "media"},
        stream=True,
        timeout=300,
    )
    file_resp.raise_for_status()
    with output_path.open("wb") as f:
        for chunk in file_resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    if args.metadata_output:
        metadata_path = Path(args.metadata_output)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, indent=2))

    print(json.dumps({
        "status": "ok",
        "saved_file": str(output_path),
        "metadata": metadata,
    }, indent=2))


if __name__ == "__main__":
    main()
