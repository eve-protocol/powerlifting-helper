#!/usr/bin/env python3
"""
Boostcamp Program Manager - Working Version

Usage:
    python boostcamp_program_manager.py list
    python boostcamp_program_manager.py update volume_block_v4.yaml
    python boostcamp_program_manager.py create strength_block_v4.yaml
"""

import requests
import yaml
import uuid
import sys
import os
import time
import json
from pathlib import Path

# Configuration
BASE_URL = "https://newapi.boostcamp.app/api"
REFRESH_TOKEN_FILE = ".boostcamp_refresh_token"
FIREBASE_API_KEY = "AIzaSyAEJcoGF-5ueF3bvaujcJm2PUV7RHKQwTw"

# Video URL mapping for common exercises
VIDEO_URLS = {
    "Squat (Low Bar)": "https://s3.boostcamp.app/master-exercise/3868392953.mp4",
    "Squat (Tempo)": "https://s3.boostcamp.app/master-exercise/3868392953.mp4",
    "Bench Press (Barbell)": "https://s3.boostcamp.app/master-exercise/2190025974.mp4",
    "Bench Press (Paused)": "https://s3.boostcamp.app/master-exercise/2190025974.mp4",
    "Bench Press (Spoto)": "https://s3.boostcamp.app/master-exercise/2190025974.mp4",
    "Sumo Deadlift (Barbell)": "https://s3.boostcamp.app/master-exercise/952218791.mp4",
    "Sumo Deadlift (Paused)": "https://s3.boostcamp.app/master-exercise/952218791.mp4",
    "Incline Bench Press (Dumbbell)": "https://s3.boostcamp.app/master-exercise/3546442638.mp4",
    "Lateral Raise (Dumbbell)": "https://s3.boostcamp.app/master-exercise/1333027272.mp4",
    "Face Pull": "https://s3.boostcamp.app/master-exercise/2918226957.mp4",
    "Cable Crunch": "https://s3.boostcamp.app/master-exercise/1971551623.mp4",
    "Pull-up (Weighted)": "https://s3.boostcamp.app/master-exercise/1099260859.mp4",
    "Pull-Up (Weighted)": "https://s3.boostcamp.app/master-exercise/1099260859.mp4",
    "Romanian Deadlift (Barbell)": "https://s3.boostcamp.app/master-exercise/1778268569.mp4",
    "Leg Extension": "https://s3.boostcamp.app/master-exercise/1971551623.mp4",
    "T-Bar Row": "https://s3.boostcamp.app/master-exercise/2918233557.mp4",
    "Overhead Tricep Extension (Cable)": "https://s3.boostcamp.app/master-exercise/2918235157.mp4",
    "Lying Leg Curl": "https://s3.boostcamp.app/master-exercise/466811.mp4",
    "Bicep Curl (EZ Bar)": "https://s3.boostcamp.app/master-exercise/2918237457.mp4",
}


def generate_uuid():
    """Generate a new UUID"""
    return str(uuid.uuid4())


def create_set(target_reps, rpe_min, rpe_max):
    """Create a set object for Boostcamp API"""
    return {
        "id": generate_uuid(),
        "from": "app",
        "source": "user created",
        "target": target_reps if isinstance(target_reps, int) else 5,
        "intensity": [float(rpe_min), float(rpe_max)],
        "target_type": "reps",
        "target_unit": "minutes",
        "intensity_unit": "RPE_range"
    }


def yaml_to_boostcamp_format(yaml_data, existing_id=None, existing_slug=None):
    """Convert YAML program data to Boostcamp API format"""
    
    workouts = []
    max_week = 0
    
    for workout_data in yaml_data.get('workouts', []):
        exercises = []
        week_idx = workout_data['week'] - 1  # Boostcamp uses 0-indexed weeks
        day_idx = workout_data['day'] - 1     # Boostcamp uses 0-indexed days
        max_week = max(max_week, workout_data['week'])
        
        for ex_data in workout_data.get('exercises', []):
            sets = []
            for set_data in ex_data.get('sets', []):
                target = set_data['target']
                rpe = set_data['rpe']
                
                if isinstance(target, str) and 'AMRAP' in target.upper():
                    # AMRAP sets - use the number after AMRAP or default to 5
                    try:
                        amrap_target = int(target.upper().replace('AMRAP', '').replace('-', '').strip() or 5)
                    except:
                        amrap_target = 5
                    sets.append(create_set(amrap_target, rpe[0], rpe[1]))
                else:
                    sets.append(create_set(int(target), rpe[0], rpe[1]))
            
            # Get video URL - try exact match first, then case-insensitive
            video_url = VIDEO_URLS.get(ex_data['name'], "")
            if not video_url:
                for name, url in VIDEO_URLS.items():
                    if name.lower() == ex_data['name'].lower():
                        video_url = url
                        break
            
            exercises.append({
                "id": generate_uuid(),
                "name": ex_data['name'],
                "type": ex_data.get('type', 'Barbell'),
                "muscles": ex_data.get('muscles', []),
                "sets": sets,
                "video": video_url,
                "alternatives": [],
                "create_from": "web"
            })
        
        workouts.append({
            "week": week_idx,
            "day": day_idx,
            "name": workout_data.get('name', ''),
            "exercises": exercises
        })
    
    # Build weeks structure - need placeholder day entries for each training day
    num_weeks = yaml_data.get('weeks', max_week)
    days_per_week = yaml_data.get('days_per_week', 5)
    weeks = [{"days": [{} for _ in range(days_per_week)]} for _ in range(num_weeks)]
    
    # Generate slug if not provided
    slug = existing_slug
    if not slug:
        slug_base = yaml_data['name'].lower().replace(' ', '-')
        slug = f"{generate_uuid()[:8]}-{slug_base}"
    
    result = {
        "weeks": weeks,
        "weekdays": [],
        "description": yaml_data.get('description', ''),
        "title": yaml_data['name'],
        "days_per_week": yaml_data.get('days_per_week', 5),
        "status": "published",
        "goals": [],
        "equipments": None,
        "difficulties": [],
        "publish_status": [],
        "slug": slug,
        "tagline": None,
        "variations": [{
            "name": "default",
            "description": None,
            "weeks": weeks,
            "weekdays": [],
            "workouts": workouts
        }]
    }
    
    # Add ID if updating existing program
    if existing_id:
        result["id"] = existing_id
        result["source"] = "unknown"
    
    return result


class BoostcampManager:
    def __init__(self, refresh_token_path=None):
        self.access_token = None
        self.refresh_token = None
        self.headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "*/*",
            "Origin": "https://www.boostcamp.app",
            "Referer": "https://www.boostcamp.app/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
        }
        
        # Load refresh token
        if refresh_token_path is None:
            refresh_token_path = REFRESH_TOKEN_FILE
        
        if os.path.exists(refresh_token_path):
            with open(refresh_token_path, 'r') as f:
                self.refresh_token = f.read().strip()
        else:
            raise Exception(f"Refresh token file not found: {refresh_token_path}")
        
        # Authenticate
        self._authenticate()
    
    def _authenticate(self):
        """Exchange refresh token for access token"""
        url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        try:
            resp = requests.post(url, data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            self.access_token = data.get('id_token')
            new_refresh_token = data.get('refresh_token')
            
            if not self.access_token:
                raise Exception("No access token received from Firebase")
            
            # Update headers with token
            self.headers["Authorization"] = f"FirebaseIdToken:{self.access_token}"
            
            # Save new refresh token if rotated
            if new_refresh_token and new_refresh_token != self.refresh_token:
                with open(REFRESH_TOKEN_FILE, 'w') as f:
                    f.write(new_refresh_token)
                self.refresh_token = new_refresh_token
                print("   (Refresh token updated)")
            
            print("✅ Authentication successful!")
            
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")
    
    def list_programs(self):
        """List all user's programs from both endpoints"""
        all_programs = {}
        timestamp = int(time.time() * 1000)
        
        # Fetch created programs from user_programs/list
        url = f"{BASE_URL}/www/user_programs/list"
        payload = {
            "sorter": {"order": "desc"},
            "filters": {
                "search": "",
                "equipments": [],
                "difficulties": [],
                "days_per_week": [],
                "goals": []
            },
            "pagination": {"current": 1, "pageSize": 100}
        }
        
        try:
            resp = requests.post(url, headers=self.headers, params={"_": timestamp}, 
                               json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            rows = data.get('data', {}).get('rows', [])
            print(f"   Found {len(rows)} programs in user_programs/list")
            
            for row in rows:
                if isinstance(row, dict) and 'title' in row:
                    all_programs[row.get('id')] = {
                        'id': row.get('id'),
                        'name': row.get('title', 'Unknown'),
                        'description': row.get('description', ''),
                        'weeks': len(row.get('weeks', [])),
                        'source': 'user_programs/list'
                    }
        except Exception as e:
            print(f"   Warning: Could not fetch from user_programs/list: {e}")
        
        # Fetch from programs/user_programs/list
        url2 = f"{BASE_URL}/www/programs/user_programs/list"
        payload2 = {"pagination": {"current": 1, "pageSize": 200}}
        
        try:
            resp = requests.post(url2, headers=self.headers, params={"_": timestamp}, 
                               json=payload2, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            rows = data.get('data', {}).get('rows', [])
            print(f"   Found {len(rows)} programs in programs/user_programs/list")
            
            for row in rows:
                if isinstance(row, dict) and 'title' in row:
                    all_programs[row.get('id')] = {
                        'id': row.get('id'),
                        'name': row.get('title', 'Unknown'),
                        'description': row.get('description', ''),
                        'weeks': len(row.get('weeks', [])),
                        'source': 'programs/user_programs/list'
                    }
        except Exception as e:
            print(f"   Warning: Could not fetch from programs/user_programs/list: {e}")
        
        return list(all_programs.values())
    
    def find_program_by_name(self, name, exact_only=False):
        """Find a program by name (exact or partial match)
        
        Args:
            name: Program name to search for
            exact_only: If True, only return exact matches
        """
        programs = self.list_programs()
        name_lower = name.lower()
        
        # First try exact match
        for prog in programs:
            if prog['name'].lower() == name_lower:
                return prog
        
        # Then try partial match (only if exact_only is False)
        if not exact_only:
            for prog in programs:
                if name_lower in prog['name'].lower():
                    return prog
        
        return None
    
    def get_program_details(self, program_id):
        """Get full program details"""
        url = f"{BASE_URL}/www/programs/user_program/share_detail"
        timestamp = int(time.time() * 1000)
        payload = {"program_id": program_id}
        
        try:
            resp = requests.post(url, headers=self.headers, params={"_": timestamp}, 
                               json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"   Error getting program details: {e}")
            return None
    
    def create_program(self, program_data):
        """Create a new program using new_create endpoint"""
        url = f"{BASE_URL}/www/programs/user_program/new_create"
        timestamp = int(time.time() * 1000)
        
        try:
            resp = requests.post(url, headers=self.headers, params={"_": timestamp}, 
                               json=program_data, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"   Error creating program: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text[:500]}")
            return None
    
    def update_program(self, program_data):
        """Update an existing program"""
        url = f"{BASE_URL}/www/programs/user_program/update"
        timestamp = int(time.time() * 1000)
        
        try:
            resp = requests.post(url, headers=self.headers, params={"_": timestamp}, 
                               json=program_data, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"   Error updating program: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text[:500]}")
            return None
    
    def sync_program(self, yaml_file, force=False):
        """Sync a YAML program to Boostcamp (create or update)"""
        # Load YAML
        with open(yaml_file, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        program_name = yaml_data['name']
        print(f"\n🔄 Syncing program: {program_name}")
        print("=" * 60)
        
        # Check if program exists
        existing = self.find_program_by_name(program_name)
        
        if existing:
            print(f"✓ Found existing program: {existing['name']}")
            print(f"   ID: {existing['id']}")
            
            if not force:
                action = input("Update existing program? (yes/no): ")
                if action.lower() != 'yes':
                    print("❌ Cancelled")
                    return False
            
            # Get full details
            print("📥 Fetching full program details...")
            details_resp = self.get_program_details(existing['id'])
            
            if not details_resp or 'data' not in details_resp:
                print("❌ Failed to fetch program details")
                return False
            
            full_program = details_resp['data']
            existing_slug = full_program.get('slug')
            
            # Build new program data from YAML
            print("🏗️  Building program from YAML...")
            new_program = yaml_to_boostcamp_format(yaml_data, 
                                                   existing_id=existing['id'],
                                                   existing_slug=existing_slug)
            
            # Preserve variations description if exists
            if 'variations' in full_program and full_program['variations']:
                new_program['variations'][0]['description'] = full_program['variations'][0].get('description')
            
            workout_count = len(new_program['variations'][0]['workouts'])
            print(f"📤 Updating program with {workout_count} workouts...")
            result = self.update_program(new_program)
            
            if result:
                print("✅ Program updated successfully!")
                return True
            else:
                print("❌ Failed to update program")
                return False
        
        else:
            print(f"✗ No existing program found with name '{program_name}'")
            
            if not force:
                action = input("Create new program? (yes/no): ")
                if action.lower() != 'yes':
                    print("❌ Cancelled")
                    return False
            
            # Build program from YAML
            print("🏗️  Building program from YAML...")
            program = yaml_to_boostcamp_format(yaml_data)
            
            workout_count = len(program['variations'][0]['workouts'])
            print(f"📤 Creating program with {workout_count} workouts...")
            result = self.create_program(program)
            
            if result:
                print("✅ Program created successfully!")
                if 'data' in result and 'id' in result['data']:
                    print(f"   Program ID: {result['data']['id']}")
                return True
            else:
                print("❌ Failed to create program")
                return False


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python boostcamp_program_manager.py list")
        print("  python boostcamp_program_manager.py update <yaml_file> [--force]")
        print("  python boostcamp_program_manager.py create <yaml_file> [--force]")
        print("\nExamples:")
        print("  python boostcamp_program_manager.py list")
        print("  python boostcamp_program_manager.py update volume_block_v4.yaml")
        print("  python boostcamp_program_manager.py create strength_block_v4.yaml --force")
        sys.exit(1)
    
    command = sys.argv[1]
    force = "--force" in sys.argv
    
    try:
        manager = BoostcampManager()
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    if command == "list":
        print("\n📋 Your Boostcamp Programs:")
        print("=" * 60)
        programs = manager.list_programs()
        
        if not programs:
            print("No programs found.")
        else:
            print(f"\nTotal: {len(programs)} programs\n")
            for i, prog in enumerate(sorted(programs, key=lambda x: x['name']), 1):
                print(f"{i}. {prog['name']}")
                print(f"   ID: {prog['id']}")
                print(f"   Weeks: {prog.get('weeks', 'N/A')}")
                if prog.get('description'):
                    desc = prog['description'][:60]
                    if len(prog['description']) > 60:
                        desc += "..."
                    print(f"   Description: {desc}")
                print()
    
    elif command in ("update", "create") and len(sys.argv) >= 3:
        yaml_file = sys.argv[2]
        if not os.path.exists(yaml_file):
            print(f"❌ File not found: {yaml_file}")
            sys.exit(1)
        
        success = manager.sync_program(yaml_file, force=force)
        sys.exit(0 if success else 1)
    
    else:
        print("Unknown command")
        print("Use: list | update <yaml_file> | create <yaml_file>")
        sys.exit(1)


if __name__ == "__main__":
    main()
