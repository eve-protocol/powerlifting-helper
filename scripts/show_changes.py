#!/usr/bin/env python3
"""
Show what changes would be made to Boostcamp programs.
Uses search-by-name approach to find specific programs.
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
    # Try environment variable first (CI)
    env_token = os.environ.get('BOOSTCAMP_REFRESH_TOKEN')
    if env_token:
        refresh_token = env_token.strip()
    else:
        # Try local file
        token_file = Path(__file__).parent / '.boostcamp_refresh_token'
        if token_file.exists():
            refresh_token = token_file.read_text().strip()
        else:
            return None
    
    # Exchange for access token
    url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
    payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    
    try:
        resp = requests.post(url, data=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get('id_token')
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return None


def fetch_user_programs(access_token):
    """Fetch all user programs"""
    headers = HEADERS.copy()
    headers["Authorization"] = f"FirebaseIdToken:{access_token}"
    
    url = f"{BASE_URL}/www/programs/user_programs/list"
    payload = {"pagination": {"current": 1, "pageSize": 200}}
    
    resp = requests.post(url, headers=headers, params={"_": int(time.time()*1000)},
                       json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json().get('data', {}).get('rows', [])

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
    
    # Get access token (from env or file)
    print("🔑 Authenticating...")
    access_token = get_access_token()
    if not access_token:
        print("❌ Failed to authenticate")
        return
    print("✅ Authenticated")
    
    # Fetch all remote programs
    print("🔍 Fetching programs from Boostcamp...")
    try:
        all_programs = fetch_user_programs(access_token)
        # Build lookup by lowercase name, filtering out deleted programs
        remote_programs = {}
        for prog in all_programs:
            # Skip deleted/archived programs
            if prog.get('status') == 'deleted':
                continue
            name = prog.get('title', '')
            remote_programs[name.lower()] = {
                'id': prog.get('id'),
                'title': prog.get('title'),
                'weeks': len(prog.get('weeks', [])),
                'workouts': len(prog.get('variations', [{}])[0].get('workouts', []))
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
