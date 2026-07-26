#!/usr/bin/env python3
"""
Boostcamp Program Manager - Working Version

Usage:
    python boostcamp_program_manager.py list
    python boostcamp_program_manager.py update volume_block_v4.yaml
    python boostcamp_program_manager.py create strength_block_v4.yaml
"""

import os
import sys
import time
import uuid

import requests

from .api import refresh_access_token
from .constants import BOOSTCAMP_PROGRAM_DETAIL_URL, BOOSTCAMP_PROGRAMS_LIST_URL, DEFAULT_REFRESH_TOKEN_FILE
from .programs import load_program_file

# Configuration
BASE_URL = "https://newapi.boostcamp.app/api"

# Video URL mapping for common exercises
VIDEO_URLS = {
    "Squat (Low Bar)": "https://s3.boostcamp.app/master-exercise/3868392953.mp4",
    "Squat (Tempo)": "https://s3.boostcamp.app/master-exercise/3868392953.mp4",
    "Bench Press (Barbell)": "https://s3.boostcamp.app/master-exercise/2190025974.mp4",
    "Bench Press (Paused)": "https://s3.boostcamp.app/master-exercise/2190025974.mp4",
    "Bench Press (Spoto)": "https://s3.boostcamp.app/master-exercise/2190025974.mp4",
    "Sumo Deadlift (Barbell)": "https://s3.boostcamp.app/master-exercise/952218791.mp4",
    "Sumo Deadlift (Paused)": "https://s3.boostcamp.app/master-exercise/952218791.mp4",
    "Sumo Deadlift (Paused at Knee)": "https://s3.boostcamp.app/master-exercise/952218791.mp4",
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
    "Spoto Press": "https://s3.boostcamp.app/master-exercise/2190025974.mp4",
    "Tempo Squat (Barbell)": "https://s3.boostcamp.app/master-exercise/3868392953.mp4",
    "Standing T Bar Row": "https://s3.boostcamp.app/master-exercise/2918233557.mp4",
    "Pull-Up (Weighted)": "https://s3.boostcamp.app/master-exercise/1099260859.mp4",
    "Leg Curl": "https://s3.boostcamp.app/master-exercise/466811.mp4",
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


def normalize_target_reps(target):
    """Normalize YAML set targets to an integer rep target for Boostcamp."""
    if isinstance(target, str) and 'AMRAP' in target.upper():
        try:
            return int(target.upper().replace('AMRAP', '').replace('-', '').strip() or 5)
        except Exception:
            return 5
    return int(target) if isinstance(target, (int, str)) else 5


def resolve_video_url(exercise_name):
    """Resolve exercise demo video URL with case-insensitive fallback."""
    video_url = VIDEO_URLS.get(exercise_name, "")
    if video_url:
        return video_url

    exercise_name_lower = exercise_name.lower()
    for name, url in VIDEO_URLS.items():
        if name.lower() == exercise_name_lower:
            return url
    return ""


def create_exercise_payload(ex_data):
    """Convert one YAML exercise entry to Boostcamp API payload format."""
    sets = []
    for set_data in ex_data.get('sets', []):
        target = normalize_target_reps(set_data['target'])
        rpe = set_data['rpe']
        sets.append(create_set(target, rpe[0], rpe[1]))

    return {
        "id": generate_uuid(),
        "name": ex_data['name'],
        "type": ex_data.get('type', 'Barbell'),
        "muscles": ex_data.get('muscles', []),
        "sets": sets,
        "video": resolve_video_url(ex_data['name']),
        "alternatives": [],
        "create_from": "web"
    }


def summarize_program_row(row, source):
    """Return a normalized program summary row."""
    return {
        'id': row.get('id'),
        'name': row.get('title', 'Unknown'),
        'description': row.get('description', ''),
        'weeks': len(row.get('weeks', [])),
        'source': source,
    }


def yaml_to_boostcamp_format(yaml_data, existing_id=None, existing_slug=None):
    """Convert YAML program data to Boostcamp API format"""
    
    workouts = []
    max_week = 0
    
    for workout_data in yaml_data.get('workouts', []):
        week_idx = workout_data['week'] - 1  # Boostcamp uses 0-indexed weeks
        day_idx = workout_data['day'] - 1     # Boostcamp uses 0-indexed days
        max_week = max(max_week, workout_data['week'])
        exercises = [create_exercise_payload(ex_data) for ex_data in workout_data.get('exercises', [])]
        
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
        self.refresh_token_path = None
        self.refresh_token_from_env = False
        self.headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "*/*",
            "Origin": "https://www.boostcamp.app",
            "Referer": "https://www.boostcamp.app/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
        }
        
        self.refresh_token = self._load_refresh_token(refresh_token_path)
        self._authenticate()

    def _load_refresh_token(self, refresh_token_path=None):
        """Load refresh token from env first, then from disk."""
        env_token = os.environ.get("BOOSTCAMP_REFRESH_TOKEN", "").strip()
        if env_token:
            self.refresh_token_from_env = True
            return env_token

        if refresh_token_path is None:
            refresh_token_path = DEFAULT_REFRESH_TOKEN_FILE

        self.refresh_token_path = refresh_token_path

        if os.path.exists(refresh_token_path):
            with open(refresh_token_path, 'r') as f:
                return f.read().strip()

        raise Exception(
            "Refresh token not found. Set BOOSTCAMP_REFRESH_TOKEN or create "
            f"{refresh_token_path}"
        )

    def _save_refresh_token(self, refresh_token):
        """Persist a rotated refresh token only when using a file-backed token."""
        if self.refresh_token_from_env or not self.refresh_token_path:
            return
        with open(self.refresh_token_path, 'w') as f:
            f.write(refresh_token)

    @staticmethod
    def _timestamp_params():
        return {"_": int(time.time() * 1000)}

    def _post_json(self, url, payload, timeout=30):
        response = requests.post(
            url,
            headers=self.headers,
            params=self._timestamp_params(),
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def _request_json(self, url, payload, error_message, timeout=30, show_response=False):
        """POST JSON and return parsed response, or None with a friendly error."""
        try:
            return self._post_json(url, payload, timeout=timeout)
        except Exception as e:
            print(f"   {error_message}: {e}")
            if show_response and hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text[:500]}")
            return None
    
    def _authenticate(self):
        """Exchange refresh token for access token"""
        try:
            self.access_token, new_refresh_token = refresh_access_token(self.refresh_token)

            if not self.access_token:
                raise Exception("No access token received from Firebase")

            # Update headers with token
            self.headers["Authorization"] = f"FirebaseIdToken:{self.access_token}"

            # Save new refresh token if rotated
            if new_refresh_token and new_refresh_token != self.refresh_token:
                self._save_refresh_token(new_refresh_token)
                self.refresh_token = new_refresh_token
                print("   (Refresh token updated)")
            
            print("✅ Authentication successful!")
            
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")
    
    def list_programs(self):
        """List all user's programs from both endpoints"""
        all_programs = {}

        endpoints = [
            (
                f"{BASE_URL}/www/user_programs/list",
                {
                    "sorter": {"order": "desc"},
                    "filters": {
                        "search": "",
                        "equipments": [],
                        "difficulties": [],
                        "days_per_week": [],
                        "goals": []
                    },
                    "pagination": {"current": 1, "pageSize": 100}
                },
                "user_programs/list",
            ),
            (
                BOOSTCAMP_PROGRAMS_LIST_URL,
                {"pagination": {"current": 1, "pageSize": 200}},
                "programs/user_programs/list",
            ),
        ]

        for url, payload, source in endpoints:
            data = self._request_json(url, payload, f"Warning: Could not fetch from {source}")
            if not data:
                continue

            rows = data.get('data', {}).get('rows', [])
            print(f"   Found {len(rows)} programs in {source}")

            for row in rows:
                if isinstance(row, dict) and 'title' in row:
                    if row.get('status') == 'deleted':
                        continue
                    all_programs[row.get('id')] = summarize_program_row(row, source)
        
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
        payload = {"program_id": program_id}
        return self._request_json(
            BOOSTCAMP_PROGRAM_DETAIL_URL,
            payload,
            "Error getting program details",
        )
    
    def create_program(self, program_data):
        """Create a new program using new_create endpoint"""
        url = f"{BASE_URL}/www/programs/user_program/new_create"
        return self._request_json(
            url,
            program_data,
            "Error creating program",
            timeout=60,
            show_response=True,
        )
    
    def update_program(self, program_data):
        """Update an existing program"""
        url = f"{BASE_URL}/www/programs/user_program/update"
        return self._request_json(
            url,
            program_data,
            "Error updating program",
            timeout=60,
            show_response=True,
        )
    
    def sync_program(self, yaml_file, force=False):
        """Sync a YAML program to Boostcamp (create or update)"""
        # Load YAML
        yaml_data = load_program_file(yaml_file)
        
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
