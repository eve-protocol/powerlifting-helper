#!/usr/bin/env python3
"""
Show what changes would be made to Boostcamp programs.
Compares local YAML files with remote programs and displays differences.
"""

import os
import sys
import yaml
import json
import time
from pathlib import Path
from difflib import unified_diff

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


def get_access_token():
    """Get access token using refresh token"""
    if not TOKEN:
        print("⚠️ BOOSTCAMP_REFRESH_TOKEN not set, skipping remote comparison")
        return None
    
    # Try to get token from existing file or use refresh token directly
    # For now, assume we have the token file created elsewhere
    token_file = Path(__file__).parent / ".boostcamp_token"
    if token_file.exists():
        return token_file.read_text().strip()
    
    # If no token file, we'll need to use refresh token
    # This is simplified - the actual implementation would refresh the token
    return TOKEN.strip()


def get_remote_programs():
    """Fetch list of programs from Boostcamp"""
    token = get_access_token()
    if not token:
        return {}
    
    headers = HEADERS.copy()
    headers["Authorization"] = f"FirebaseIdToken:{token}"
    
    url = f"{BASE_URL}/www/user_programs/list"
    params = {"_": int(time.time() * 1000)}
    
    # Fetch single page with 200 items (should be enough)
    payload = {
        "sorter": {"order": "desc"},
        "filters": {"search": "", "equipments": [], "difficulties": [], "days_per_week": [], "goals": []},
        "pagination": {"current": 1, "pageSize": 200}
    }
    
    try:
        resp = requests.post(url, headers=headers, params=params, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        programs = {}
        rows = data.get('data', {}).get('rows', [])
        print(f"   DEBUG: API returned {len(rows)} programs")
        
        for row in rows:
            if isinstance(row, dict) and 'title' in row:
                programs[row['title'].lower()] = {
                    'id': row.get('id'),
                    'title': row.get('title'),
                    'weeks': len(row.get('weeks', [])),
                    'workouts': len(row.get('variations', [{}])[0].get('workouts', []))
                }
        return programs
    except Exception as e:
        print(f"⚠️ Could not fetch remote programs: {e}")
        import traceback
        traceback.print_exc()
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


def format_change(action, program_name, details=""):
    """Format a change for display"""
    icons = {
        'create': '🆕',
        'update': '🔄',
        'delete': '🗑️',
        'unchanged': '✅'
    }
    print(f"{icons.get(action, '❓')} {action.upper()}: {program_name}")
    if details:
        print(f"   {details}")


def main():
    print("📊 Program Changes Preview")
    print("=" * 60)
    print()
    
    # Load local and remote programs
    local_programs = load_local_programs()
    remote_programs = get_remote_programs()
    
    if not local_programs:
        print("ℹ️ No local program files found")
        return
    
    print(f"   Found {len(remote_programs)} remote program(s)")
    
    # Analyze changes with case-insensitive matching
    changes = []
    
    for name, local_data in local_programs.items():
        name_lower = name.lower()
        if name_lower in remote_programs:
            remote_data = remote_programs[name_lower]
            if local_data['weeks'] != remote_data['weeks'] or \
               local_data['workouts'] != remote_data['workouts']:
                changes.append(('update', name, 
                    f"{local_data['weeks']} weeks, {local_data['workouts']} workouts (was {remote_data['weeks']} weeks, {remote_data['workouts']} workouts)"))
            else:
                changes.append(('unchanged', name, 
                    f"{local_data['weeks']} weeks, {local_data['workouts']} workouts"))
        else:
            changes.append(('create', name, 
                f"{local_data['weeks']} weeks, {local_data['workouts']} workouts"))
    
    # Display changes
    if not changes:
        print("ℹ️ No programs to compare")
        return
    
    # Group by action
    creates = [c for c in changes if c[0] == 'create']
    updates = [c for c in changes if c[0] == 'update']
    unchanged = [c for c in changes if c[0] == 'unchanged']
    
    if creates:
        print("🆕 NEW PROGRAMS:")
        for action, name, details in creates:
            format_change(action, name, details)
        print()
    
    if updates:
        print("🔄 UPDATES:")
        for action, name, details in updates:
            format_change(action, name, details)
        print()
    
    if unchanged:
        print("✅ UNCHANGED:")
        for action, name, details in unchanged:
            format_change(action, name, details)
        print()
    
    # Summary
    total = len(changes)
    print(f"📋 Summary: {len(creates)} new, {len(updates)} updates, {len(unchanged)} unchanged")
    
    if creates or updates:
        print("\n⚠️  These changes will be applied when the PR is merged to main.")


if __name__ == "__main__":
    main()