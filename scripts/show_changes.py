#!/usr/bin/env python3
"""
Show what changes would be made to Boostcamp programs.
Uses search-by-name approach to find specific programs.
"""

import os
import sys
import yaml
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' library required")
    sys.exit(1)

BASE_URL = "https://newapi.boostcamp.app/api"
TOKEN = os.environ.get('BOOSTCAMP_REFRESH_TOKEN')

HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "Accept": "application/json",
    "Origin": "https://www.boostcamp.app",
    "Referer": "https://www.boostcamp.app/"
}


def find_program_by_name(name, token):
    """Search for a specific program by name"""
    headers = HEADERS.copy()
    headers["Authorization"] = f"FirebaseIdToken:{token.strip()}"
    
    url = f"{BASE_URL}/www/user_programs/list"
    payload = {
        "sorter": {"order": "desc"},
        "filters": {"search": name, "equipments": [], "difficulties": [], "days_per_week": [], "goals": []},
        "pagination": {"current": 1, "pageSize": 20}
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        rows = data.get('data', {}).get('rows', [])
        for row in rows:
            # Match by exact title (case-insensitive) - instructor_id may vary
            if row['title'].lower() == name.lower():
                return {
                    'id': row.get('id'),
                    'title': row.get('title'),
                    'weeks': len(row.get('weeks', [])),
                    'workouts': len(row.get('variations', [{}])[0].get('workouts', []))
                }
        return None
    except Exception as e:
        print(f"⚠️ Error searching for {name}: {e}")
        return None


def get_remote_programs(program_names):
    """Find all programs by searching individually"""
    if not TOKEN:
        print("⚠️ BOOSTCAMP_REFRESH_TOKEN not set")
        return {}
    
    programs = {}
    for name in program_names:
        result = find_program_by_name(name, TOKEN)
        if result:
            programs[name.lower()] = result
    
    return programs


def load_local_programs():
    """Load all local YAML program files"""
    # Check both programs/ and values/ directories
    for programs_dir in [Path("programs"), Path("values")]:
        programs = {}
        
        if not programs_dir.exists():
            continue
        
        for yaml_file in programs_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
                programs[data['name']] = {
                    'file': yaml_file.name,
                    'weeks': data.get('weeks', 0),
                    'workouts': len(data.get('workouts', []))
                }
        except Exception as e:
            print(f"⚠️ Error loading {yaml_file}: {e}")
    
    return programs


def main():
    print("📊 Program Changes Preview")
    print("=" * 60)
    print()
    
    local_programs = load_local_programs()
    
    if not local_programs:
        print("ℹ️ No local program files found")
        return
    
    # Search for each program individually
    print("🔍 Searching for programs on Boostcamp...")
    remote_programs = get_remote_programs(list(local_programs.keys()))
    
    print(f"📋 Found {len(local_programs)} local, {len(remote_programs)} remote user programs")
    print()
    
    # Check each local program
    creates = []
    updates = []
    unchanged = []
    
    for name, local_data in local_programs.items():
        name_lower = name.lower()
        if name_lower in remote_programs:
            remote_data = remote_programs[name_lower]
            if local_data['weeks'] != remote_data['weeks']:
                updates.append((name, f"{local_data['weeks']} weeks (was {remote_data['weeks']})"))
            else:
                unchanged.append((name, f"{local_data['weeks']} weeks"))
        else:
            creates.append((name, f"{local_data['weeks']} weeks"))
    
    # Display results
    if creates:
        print("🆕 NEW PROGRAMS:")
        for name, details in creates:
            print(f"   🆕 {name} ({details})")
        print()
    
    if updates:
        print("🔄 UPDATES:")
        for name, details in updates:
            print(f"   🔄 {name} ({details})")
        print()
    
    if unchanged:
        print("✅ UNCHANGED:")
        for name, details in unchanged:
            print(f"   ✅ {name} ({details})")
        print()
    
    total = len(creates) + len(updates) + len(unchanged)
    print(f"📋 Summary: {len(creates)} new, {len(updates)} updates, {len(unchanged)} unchanged")


if __name__ == "__main__":
    main()