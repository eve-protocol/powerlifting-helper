#!/usr/bin/env python3
"""
Show what changes would be made to Boostcamp programs.
Compares actual workout content (exercises, sets, RPE values).
"""

from pathlib import Path

import yaml

from powerlifting.api import fetch_created_programs, fetch_program, get_access_token


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
    """Extract comparable key from exercise - only name, target reps, and RPE/intensity"""
    sets = []
    for s in exercise.get('sets', []):
        target = s.get('target')

        # Local YAML stores RPE in `rpe`, Boostcamp API uses `intensity`
        rpe = s.get('rpe', s.get('intensity'))

        if isinstance(rpe, (list, tuple)):
            rpe = tuple(rpe)
        elif isinstance(rpe, (int, float)):
            rpe = (rpe, rpe)
        else:
            rpe = None

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
    access_token = get_access_token(Path(__file__).parent)
    if not access_token:
        print("❌ Failed to authenticate")
        return
    print("✅ Authenticated")
    
    print("🔍 Fetching programs from Boostcamp...")
    try:
        remote_list = fetch_created_programs(access_token)
        
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
                remote_detail = fetch_program(remote_prog['id'], access_token).get('data', {})
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
    
    print(f"📋 Summary: {len(creates)} new, {len(updates)} updates, {len(unchanged)} unchanged")


if __name__ == "__main__":
    main()
