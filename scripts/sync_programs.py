#!/usr/bin/env python3
"""
Sync YAML programs to Boostcamp.
Creates new programs or updates existing ones based on name matching.
"""

import os
import sys
import yaml
import uuid
import time
import requests
from pathlib import Path

# Configuration
BASE_URL = "https://newapi.boostcamp.app/api"
FIREBASE_API_KEY = "AIzaSyAEJcoGF-5ueF3bvaujcJm2PUV7RHKQwTw"
PROGRAMS_DIR = Path("programs")

HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "Accept": "application/json",
    "Origin": "https://www.boostcamp.app",
    "Referer": "https://www.boostcamp.app/"
}

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
    "Romanian Deadlift (Barbell)": "https://s3.boostcamp.app/master-exercise/1778268569.mp4",
    "Leg Extension": "https://s3.boostcamp.app/master-exercise/2918232657.mp4",
    "T-Bar Row": "https://s3.boostcamp.app/master-exercise/2918233557.mp4",
    "Overhead Tricep Extension (Cable)": "https://s3.boostcamp.app/master-exercise/2918235157.mp4",
    "Lying Leg Curl": "https://s3.boostcamp.app/master-exercise/466811.mp4",
    "Bicep Curl (EZ Bar)": "https://s3.boostcamp.app/master-exercise/2918237457.mp4",
    "Spoto Press": "https://s3.boostcamp.app/master-exercise/2190025974.mp4",
    "Tempo Squat (Barbell)": "https://s3.boostcamp.app/master-exercise/3868392953.mp4",
    "Standing T Bar Row": "https://s3.boostcamp.app/master-exercise/2918233557.mp4",
    "Pull-Up (Weighted)": "https://s3.boostcamp.app/master-exercise/1099260859.mp4",
    "Leg Curl": "https://s3.boostcamp.app/master-exercise/466811.mp4",
}


def generate_uuid():
    return str(uuid.uuid4())


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


def create_set(target_reps, rpe_min, rpe_max):
    return {
        "id": generate_uuid(),
        "from": "app",
        "source": "user created",
        "target": target_reps,
        "intensity": [float(rpe_min), float(rpe_max)],
        "target_type": "reps",
        "target_unit": "minutes",
        "intensity_unit": "RPE_range"
    }


def create_exercise(name, exercise_type, muscles, sets, video=""):
    ex = {
        "id": generate_uuid(),
        "name": name,
        "sets": sets,
        "alternatives": []
    }
    if exercise_type:
        ex["type"] = exercise_type
    if muscles:
        ex["muscles"] = muscles
    if video:
        ex["video"] = video
    return ex


def yaml_to_boostcamp_format(yaml_data):
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
                exercise_type=ex_data.get('type'),
                muscles=ex_data.get('muscles'),
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
    days_per_week = yaml_data.get('days_per_week', 5)
    weeks = [{"days": [{} for _ in range(days_per_week)]} for _ in range(num_weeks)]
    
    return {
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
    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = HEADERS.copy()
        self.headers["Authorization"] = f"FirebaseIdToken:{access_token}"
    
    def find_program_by_name(self, name):
        """Search for a specific program by name"""
        url = f"{BASE_URL}/www/programs/user_programs/list"
        payload = {"pagination": {"current": 1, "pageSize": 200}}
        
        try:
            resp = requests.post(url, headers=self.headers, params={"_": int(time.time()*1000)},
                               json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            rows = data.get('data', {}).get('rows', [])
            for row in rows:
                # Skip deleted programs
                if row.get('status') == 'deleted':
                    continue
                if row['title'].lower() == name.lower():
                    return row.get('id')
            return None
        except Exception as e:
            print(f"❌ Error searching for {name}: {e}")
            return None
    
    def create_program(self, program_data):
        url = f"{BASE_URL}/www/programs/user_program/new_create"
        params = {"_": int(time.time() * 1000)}
        
        try:
            resp = requests.post(url, headers=self.headers, params=params, 
                               json=program_data, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"❌ Error creating program: {e}")
            return None
    
    def update_program(self, program_id, program_data):
        url = f"{BASE_URL}/www/programs/user_program/update"
        params = {"_": int(time.time() * 1000)}
        
        program_data['id'] = program_id
        
        try:
            resp = requests.post(url, headers=self.headers, params=params, 
                               json=program_data, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"❌ Error updating program: {e}")
            return None
    
    def sync_program(self, yaml_file):
        try:
            with open(yaml_file, 'r') as f:
                yaml_data = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading {yaml_file}: {e}")
            return False
        
        program_name = yaml_data['name']
        print(f"\n📄 {program_name}")
        
        program = yaml_to_boostcamp_format(yaml_data)
        existing_id = self.find_program_by_name(program_name)
        
        if existing_id:
            print(f"   🔄 Updating existing program")
            result = self.update_program(existing_id, program)
            if result:
                print(f"   ✅ Updated successfully")
                return True
        else:
            print(f"   🆕 Creating new program")
            result = self.create_program(program)
            if result:
                print(f"   ✅ Created successfully")
                return True
        
        return False


def main():
    print("🚀 Syncing Programs to Boostcamp")
    print("=" * 60)
    
    if not PROGRAMS_DIR.exists():
        print("❌ Programs directory not found")
        sys.exit(1)
    
    yaml_files = sorted(PROGRAMS_DIR.glob("*.yaml"))
    
    if not yaml_files:
        print("ℹ️ No YAML files found")
        sys.exit(0)
    
    print(f"\n📊 Found {len(yaml_files)} program file(s)")
    
    # Get access token (from env or file)
    print("🔑 Authenticating...")
    access_token = get_access_token()
    if not access_token:
        print("❌ Failed to authenticate")
        sys.exit(1)
    print("✅ Authenticated")
    
    sync = BoostcampSync(access_token)
    
    results = []
    for yaml_file in yaml_files:
        success = sync.sync_program(yaml_file)
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
