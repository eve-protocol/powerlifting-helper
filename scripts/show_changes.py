#!/usr/bin/env python3
"""
Show what changes would be made to Boostcamp programs.
Compares local YAML files with remote programs and displays differences.
Filters to show ONLY user's custom programs by instructor_id.
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

# User's instructor ID (found from HAR analysis)
USER_INSTRUCTOR_ID = "XQKPa6AUJSVdgnjqMtAQCMwL7CZ1"


def get_access_token():
    """Get access token"""
    if not TOKEN:
        print("⚠️ BOOSTCAMP_REFRESH_TOKEN not set, skipping remote comparison")
        return None
    return TOKEN.strip()


def get_remote_programs():
    """Fetch list of USER'S programs from Boostcamp (paginated)"""
    token = get_access_token()
    if not token:
        return {}
    
    headers = HEADERS.copy()
    headers["Authorization"] = f"FirebaseIdToken:{token}"
    
    url = f"{BASE_URL}/www/user_programs/list"
    
    # Fetch all pages to find user's programs
    all_user_programs = {}
    page = 1
    max_pages = 5  # Safety limit
    
    while page <= max_pages:
        params = {"_": int(time.time() * 1000) + page}
        payload = {
            "sorter": {"order": "desc"},
            "filters": {"search": "", "equipments": [], "difficulties": [], "days_per_week": [], "goals": []},
            "pagination": {"current": page, "pageSize": 100}
        }
        
        try:
            resp = requests.post(url, headers=headers, params=params, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            rows = data.get('data', {}).get('rows', [])
            if not rows:
                break
            
            for row in rows:
                if row.get('instructor_id') == USER_INSTRUCTOR_ID:
                    all_user_programs[row['title'].lower()] = {
                        'id': row.get('id'),
                        'title': row.get('title'),
                        'weeks': len(row.get('weeks', [])),
                        'workouts': len(row.get('variations', [{}])[0].get('workouts', []))
                    }
            
            # Stop if we got less than page size
            if len(rows) < 100:
                break
            
            page += 1
            
        except Exception as e:
            print(f"⚠️ Could not fetch remote programs: {e}")
            break
    
    return all_user_programs


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
    
    print(f"📋 Summary: {len(local_programs)} local, {len(remote_programs)} remote user programs")
    print()
    
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