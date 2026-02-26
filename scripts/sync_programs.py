#!/usr/bin/env python3
"""
Sync YAML programs to Boostcamp.
Creates new programs or updates existing ones based on name matching.
"""

import os
import sys
import yaml
import json
import uuid
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' library required")
    sys.exit(1)

BASE_URL = "https://newapi.boostcamp.app/api"
REFRESH_TOKEN = os.environ.get('BOOSTCAMP_REFRESH_TOKEN')
PROGRAMS_DIR = Path("programs")

HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "Accept": "application/json",
    "Origin": "https://www.boostcamp.app",
    "Referer": "https://www.boostcamp.app/"
}

# Video URLs for common exercises
VIDEO_URLS = {
    "Squat (Low Bar)": "https://s3.boostcamp.app/master-exercise/3868392953.mp4",
    "Squat (Tempo)": "https://s3.boostcamp.app/master-exercise/3868392953.mp4",
    "Bench Press (Barbell)": "https://s3.boostcamp.app/master-exercise/2918223457.mp4",
    "Bench Press (Paused)": "https://s3.boostcamp.app/master-exercise/2918223457.mp4",
    "Bench Press (Spoto)": "https://s3.boostcamp.app/master-exercise/2918223457.mp4",
    "Sumo Deadlift (Barbell)": "https://s3.boostcamp.app/master-exercise/3868077957.mp4",
    "Sumo Deadlift (Paused)": "https://s3.boostcamp.app/master-exercise/3868077957.mp4",
    "Incline Bench Press (Dumbbell)": "https://s3.boostcamp.app/master-exercise/2918224257.mp4",
    "Lateral Raise (Dumbbell)": "https://s3.boostcamp.app/master-exercise/2918226357.mp4",
    "Face Pull": "https://s3.boostcamp.app/master-exercise/2918226957.mp4",
    "Cable Crunch": "https://s3.boostcamp.app/master-exercise/2918229357.mp4",
    "Pull-up (Weighted)": "https://s3.boostcamp.app/master-exercise/2918230657.mp4",
    "Romanian Deadlift (Barbell)": "https://s3.boostcamp.app/master-exercise/3868366957.mp4",
    "Leg Extension": "https://s3.boostcamp.app/master-exercise/2918232657.mp4",
    "T-Bar Row": "https://s3.boostcamp.app/master-exercise/2918233557.mp4",
    "Overhead Tricep Extension (Cable)": "https://s3.boostcamp.app/master-exercise/2918235157.mp4",
    "Lying Leg Curl": "https://s3.boostcamp.app/master-exercise/2918235757.mp4",
    "Bicep Curl (EZ Bar)": "https://s3.boostcamp.app/master-exercise/2918237457.mp4",
}


def generate_uuid():
    return str(uuid.uuid4())


def create_set(target_reps, rpe_min, rpe_max):
    return {
        "id": generate_uuid(),
        "from": "app",
        "source": "user created",
        "target": target_reps,
        "intensity": [rpe_min, rpe_max],
        "target_type": "reps",
        "target_unit": "minutes",
        "intensity_unit": "RPE_range"
    }


def create_exercise(name, sets, video=""):
    return {
        "id": generate_uuid(),
        "name": name,
        "type": "Barbell",  # Default, will be inferred if possible
        "muscles": [],  # Not required for API
        "sets": sets,
        "video": video,
        "alternatives": []
    }


def yaml_to_boostcamp_format(yaml_data):
    """Convert YAML to Boostcamp API format"""
    workouts = []
    
    for workout_data in yaml_data.get('workouts', []):
        exercises = []
        
        for ex_data in workout_data.get('exercises', []):
            sets = []
            for set_data in ex_data.get('sets', []):
                target = set_data['target']
                rpe = set_data['rpe']
                sets.append(create_set(target, rpe[0], rpe[1]))
            
            exercises.append(create_exercise(
                name=ex_data['name'],
                sets=sets,
                video=VIDEO_URLS.get(ex_data['name'], "")
            ))
        
        workouts.append({
            "week": workout_data['week'] - 1,
            "day": workout_data['day'] - 1,
            "name": workout_data['name'],
            "exercises": exercises
        })
    
    num_weeks = yaml_data.get('weeks', 3)
    weeks = [{"days": [{}, {}, {}, {}, {}]} for _ in range(num_weeks)]
    
    return {
        "source": "unknown",
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
        "slug": generate_uuid()[:8],
        "tagline": None,
        "variations": [{
            "name": "default",
            "description": None,
            "weeks": weeks,
            "weekdays": [],
            "workouts": workouts
        }]
    }


class BoostcampSync:
    def __init__(self):
        self.token = self._get_token()
        self.headers = HEADERS.copy()
        if self.token:
            self.headers["Authorization"] = f"FirebaseIdToken:{self.token}"
    
    def _get_token(self):
        """Get access token"""
        if not REFRESH_TOKEN:
            print("❌ BOOSTCAMP_REFRESH_TOKEN not set")
            sys.exit(1)
        
        # For simplicity, using refresh token directly
        # In production, you'd want to handle token refresh properly
        return REFRESH_TOKEN
    
    def list_programs(self):
        """List all programs"""
        url = f"{BASE_URL}/www/user_programs/list"
        params = {"_": int(time.time() * 1000)}
        
        payload = {
            "sorter": {"order": "desc"},
            "filters": {"search": "", "equipments": [], "difficulties": [], "days_per_week": [], "goals": []},
            "pagination": {"current": 1, "pageSize": 100}
        }
        
        try:
            resp = requests.post(url, headers=self.headers, params=params, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            programs = {}
            rows = data.get('data', {}).get('rows', [])
            for row in rows:
                if isinstance(row, dict) and 'title' in row:
                    programs[row['title']] = row.get('id')
            return programs
        except Exception as e:
            print(f"❌ Error listing programs: {e}")
            return {}
    
    def create_program(self, program_data):
        """Create a new program"""
        url = f"{BASE_URL}/www/programs/user_program/create"
        params = {"_": int(time.time() * 1000)}
        
        try:
            resp = requests.post(url, headers=self.headers, params=params, json=program_data, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"❌ Error creating program: {e}")
            return None
    
    def update_program(self, program_id, program_data):
        """Update an existing program"""
        url = f"{BASE_URL}/www/programs/user_program/update"
        params = {"_": int(time.time() * 1000)}
        
        program_data['id'] = program_id
        
        try:
            resp = requests.post(url, headers=self.headers, params=params, json=program_data, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"❌ Error updating program: {e}")
            return None
    
    def sync_program(self, yaml_file, existing_programs):
        """Sync a single YAML file"""
        try:
            with open(yaml_file, 'r') as f:
                yaml_data = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading {yaml_file}: {e}")
            return False
        
        program_name = yaml_data['name']
        print(f"\n📄 {program_name}")
        
        # Build program data
        program_data = yaml_to_boostcamp_format(yaml_data)
        
        # Check if program exists
        if program_name in existing_programs:
            program_id = existing_programs[program_name]
            print(f"   🔄 Updating existing program (ID: {program_id[:20]}...)")
            result = self.update_program(program_id, program_data)
            if result:
                print(f"   ✅ Updated successfully")
                return True
        else:
            print(f"   🆕 Creating new program")
            result = self.create_program(program_data)
            if result:
                print(f"   ✅ Created successfully (ID: {result.get('id', 'N/A')[:20]}...)")
                return True
        
        return False


def main():
    print("🚀 Syncing Programs to Boostcamp")
    print("=" * 60)
    
    if not REFRESH_TOKEN:
        print("❌ BOOSTCAMP_REFRESH_TOKEN environment variable not set")
        sys.exit(1)
    
    if not PROGRAMS_DIR.exists():
        print("❌ Programs directory not found")
        sys.exit(1)
    
    yaml_files = sorted(PROGRAMS_DIR.glob("*.yaml"))
    
    if not yaml_files:
        print("ℹ️ No YAML files found")
        sys.exit(0)
    
    print(f"\n📊 Found {len(yaml_files)} program file(s)")
    
    # Initialize sync client
    sync = BoostcampSync()
    
    # Get existing programs
    print("\n📥 Fetching existing programs from Boostcamp...")
    existing_programs = sync.list_programs()
    print(f"   Found {len(existing_programs)} existing program(s)")
    
    # Sync each program
    results = []
    for yaml_file in yaml_files:
        success = sync.sync_program(yaml_file, existing_programs)
        results.append((yaml_file.name, success))
    
    # Summary
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