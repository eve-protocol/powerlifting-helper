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


def get_all_programs(token):
    """Fetch all user programs from the working endpoint"""
    headers = HEADERS.copy()
    headers["Authorization"] = f"FirebaseIdToken:{token.strip()}"
    
    url = f"{BASE_URL}/www/programs/user_programs/list"
    payload = {"pagination": {"current": 1, "pageSize": 200}}
    
    try:
        resp = requests.post(url, headers=headers, params={"_": int(time.time()*1000)}, 
                           json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        rows = data.get('data', {}).get('rows', [])
        # Build lookup by lowercase name
        programs = {}
        for row in rows:
            name = row.get('title', '')
            programs[name.lower()] = {
                'id': row.get('id'),
                'title': row.get('title'),
                'weeks': len(row.get('weeks', [])),
                'workouts': len(row.get('variations', [{}])[0].get('workouts', []))
            }
        return programs
    except Exception as e:
        print(f"⚠️ Error fetching programs: {e}")
        return {}


def load_local_programs():
    """Load all local YAML program files"""
    programs_dir = Path("programs")
    programs = {}
    
    if not programs_dir.exists():
        return programs
    
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
    
    if not TOKEN:
        print("⚠️ BOOSTCAMP_REFRESH_TOKEN not set")
        return
    
    # Fetch all remote programs at once
    print("🔍 Fetching programs from Boostcamp...")
    remote_programs = get_all_programs(TOKEN)
    
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
