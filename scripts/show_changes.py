#!/usr/bin/env python3
"""
Show what changes would be made to Boostcamp programs.
Compares actual workout content (exercises, sets, RPE values).
"""

import os
import sys
import requests
import yaml
import time
from pathlib import Path

BASE_URL = "https://newapi.boostcamp.app/api"
FIREBASE_API_KEY = "AIzaSyAEJcoGF-5ueF3bvaujcJm2PUV7RHKQwTw"

HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "Accept": "application/json",
    "Origin": "https://www.boostcamp.app",
    "Referer": "https://www.boostcamp.app/"
}


def get_access_token():
    """Get access token from environment or file"""
    env_token = os.environ.get('BOOSTCAMP_REFRESH_TOKEN')
    if env_token:
        refresh_token = env_token.strip()
    else:
        token_file = Path(__file__).parent / '.boostcamp_refresh_token'
        if token_file.exists():
            refresh_token = token_file.read_text().strip()
        else:
            return None
    
    url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
    payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    
    try:
        resp = requests.post(url, data=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get('id_token')
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return None


def fetch_program_list(access_token):
    """Fetch list of user programs"""
    headers = HEADERS.copy()
    headers["Authorization"] = f"FirebaseIdToken:{access_token}"
    
    url = f"{BASE_URL}/www/programs/user_programs/list"
    payload = {"pagination": {"current": 1, "pageSize": 200}}
    
    resp = requests.post(url, headers=headers, params={"_": int(time.time()*1000)},
                       json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json().get('data', {}).get('rows', [])


def fetch_program_detail(access_token, program_id):
    """Fetch full program details"""
    headers = HEADERS.copy()
    headers["Authorization"] = f"FirebaseIdToken:{access_token}"
    
    url = f"{BASE_URL}/www/programs/user_program/share_detail"
    payload = {"program_id": program_id}
    
    resp = requests.post(url, headers=headers, params={"_": int(time.time()*1000)},
                       json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json().get('data', {})


def load_local_programs():
    """Load all local YAML program files with full content"""
    programs_dir = Path("programs")
    programs = {}
    
    if not programs_dir.exists():
        return programs
    
    for yaml_file in programs_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
                programs[data['name']] = data
        except Exception as e:
            print(f"⚠️ Error loading {yaml_file}: {e}")
    
    return programs


def extract_exercise_key(exercise):
    """Extract comparable key from exercise - only name, target reps, and RPE"""
    sets = []
    for s in exercise.get('sets', []):
        target = s.get('target')
        # Handle RPE - can be list [min, max] or single value
        rpe = s.get('rpe')
        if isinstance(rpe, (list, tuple)):
            rpe = tuple(rpe)
        elif isinstance(rpe, (int, float)):
            rpe = (rpe, rpe)
        else:
            rpe = (0, 0)
        sets.append((target, rpe))
    return (exercise.get('name', '').lower(), tuple(sorted(sets)))


def compare_programs(yaml_data, remote_data):
    """Compare YAML program with remote program - only compare exercise name, reps, and RPE"""
    # Get workouts from both
    yaml_workouts = yaml_data.get('workouts', [])
    remote_workouts = remote_data.get('variations', [{}])[0].get('workouts', [])
    
    # Build lookup by week-day
    yaml_by_key = {}
    for w in yaml_workouts:
        key = f"{w['week']}-{w['day']}"
        exercises = tuple(sorted([extract_exercise_key(ex) for ex in w.get('exercises', [])]))
        yaml_by_key[key] = exercises
    
    remote_by_key = {}
    for w in remote_workouts:
        key = f"{w['week']+1}-{w['day']+1}"  # API uses 0-indexed
        exercises = tuple(sorted([extract_exercise_key(ex) for ex in w.get('exercises', [])]))
        remote_by_key[key] = exercises
    
    # Check for differences
    differences = []
    
    for key in yaml_by_key:
        if key not in remote_by_key:
            differences.append(f"Workout {key} missing in remote")
        elif yaml_by_key[key] != remote_by_key[key]:
            differences.append(f"Workout {key} differs")
    
    for key in remote_by_key:
        if key not in yaml_by_key:
            differences.append(f"Workout {key} extra in remote")
    
    return differences


def main():
    print("📊 Program Changes Preview")
    print("=" * 60)
    print()
    
    local_programs = load_local_programs()
    
    if not local_programs:
        print("ℹ️ No local program files found")
        return
    
    print("🔑 Authenticating...")
    access_token = get_access_token()
    if not access_token:
        print("❌ Failed to authenticate")
        return
    print("✅ Authenticated")
    
    print("🔍 Fetching programs from Boostcamp...")
    try:
        remote_list = fetch_program_list(access_token)
        
        # Build lookup of non-deleted programs
        remote_programs = {}
        for prog in remote_list:
            if prog.get('status') == 'deleted':
                continue
            name = prog.get('title', '')
            remote_programs[name.lower()] = {
                'id': prog.get('id'),
                'title': prog.get('title'),
                'data': None  # Will fetch details if needed
            }
    except Exception as e:
        print(f"⚠️ Error fetching programs: {e}")
        return
    
    print(f"📋 Found {len(local_programs)} local, {len(remote_programs)} remote user programs")
    print()
    
    # Check each local program
    creates = []
    updates = []
    unchanged = []
    
    for name, yaml_data in local_programs.items():
        name_lower = name.lower()
        if name_lower in remote_programs:
            remote_prog = remote_programs[name_lower]
            
            # Fetch full remote details for comparison
            try:
                remote_detail = fetch_program_detail(access_token, remote_prog['id'])
                differences = compare_programs(yaml_data, remote_detail)
                
                if differences:
                    updates.append((name, differences))
                else:
                    unchanged.append(name)
            except Exception as e:
                print(f"⚠️ Error comparing {name}: {e}")
                updates.append((name, ["Could not compare"]))
        else:
            creates.append(name)
    
    # Display results
    if creates:
        print("🆕 NEW PROGRAMS:")
        for name in creates:
            print(f"   🆕 {name}")
        print()
    
    if updates:
        print("🔄 UPDATES:")
        for name, diffs in updates:
            print(f"   🔄 {name}")
            for diff in diffs[:5]:  # Show max 5 differences
                print(f"      - {diff}")
            if len(diffs) > 5:
                print(f"      ... and {len(diffs) - 5} more")
        print()
    
    if unchanged:
        print("✅ UNCHANGED:")
        for name in unchanged:
            print(f"   ✅ {name}")
        print()
    
    total = len(creates) + len(updates) + len(unchanged)
    print(f"📋 Summary: {len(creates)} new, {len(updates)} updates, {len(unchanged)} unchanged")


if __name__ == "__main__":
    main()
