#!/usr/bin/env python3
"""
Batch sync all YAML programs in ./programs to Boostcamp.

This script is intentionally thin and reuses the shared BoostcampManager
implementation so the sync logic only lives in one place.
"""

import sys

from powerlifting.boostcamp_program_manager import BoostcampManager
from powerlifting.programs import PROGRAMS_DIR, iter_program_files


def main():
    print("🚀 Syncing Programs to Boostcamp")
    print("=" * 60)

    if not PROGRAMS_DIR.exists():
        print("❌ Programs directory not found")
        sys.exit(1)

    yaml_files = iter_program_files(PROGRAMS_DIR)
    if not yaml_files:
        print("ℹ️ No YAML files found")
        sys.exit(0)

    print(f"\n📊 Found {len(yaml_files)} program file(s)")
    print("🔑 Authenticating...")

    try:
        manager = BoostcampManager()
    except Exception as exc:
        print(f"❌ Failed to authenticate: {exc}")
        sys.exit(1)

    results = []
    for yaml_file in yaml_files:
        success = manager.sync_program(str(yaml_file), force=True)
        results.append((yaml_file.name, success))

    print("\n" + "=" * 60)
    print("📋 SYNC SUMMARY")
    print("=" * 60)

    success_count = sum(1 for _, success in results if success)
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")

    print(f"\nTotal: {success_count}/{len(results)} successful")
    if success_count != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
