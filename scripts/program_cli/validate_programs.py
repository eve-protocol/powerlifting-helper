#!/usr/bin/env python3
"""
Validate YAML program files against schema.
Exits with error if any file is invalid.
"""

import sys
import yaml

from powerlifting.programs import PROGRAMS_DIR, iter_program_files, load_program_file

REQUIRED_FIELDS = ['name', 'description', 'weeks', 'days_per_week', 'workouts']
REQUIRED_WORKOUT_FIELDS = ['week', 'day', 'name', 'exercises']
REQUIRED_EXERCISE_FIELDS = ['name', 'sets']
REQUIRED_SET_FIELDS = ['target', 'rpe']


def validate_set(set_data, exercise_name, workout_name):
    """Validate a single set"""
    errors = []
    
    for field in REQUIRED_SET_FIELDS:
        if field not in set_data:
            errors.append(f"  Missing '{field}' in set for {exercise_name}")
    
    # Validate RPE format
    if 'rpe' in set_data:
        rpe = set_data['rpe']
        if not isinstance(rpe, list) or len(rpe) != 2:
            errors.append(f"  Invalid RPE format for {exercise_name}: {rpe} (should be [min, max])")
        else:
            try:
                min_rpe, max_rpe = float(rpe[0]), float(rpe[1])
                if min_rpe < 1 or max_rpe > 10 or min_rpe > max_rpe:
                    errors.append(f"  Invalid RPE values for {exercise_name}: {rpe}")
            except (ValueError, TypeError):
                errors.append(f"  RPE values must be numbers for {exercise_name}: {rpe}")
    
    # Validate target
    if 'target' in set_data:
        target = set_data['target']
        if not isinstance(target, int) or target < 1:
            errors.append(f"  Invalid target reps for {exercise_name}: {target}")
    
    return errors


def validate_exercise(exercise_data, workout_name):
    """Validate a single exercise"""
    errors = []
    exercise_name = exercise_data.get('name', 'Unknown')
    
    for field in REQUIRED_EXERCISE_FIELDS:
        if field not in exercise_data:
            errors.append(f"  Missing '{field}' in exercise '{exercise_name}'")
    
    # Validate sets
    if 'sets' in exercise_data:
        sets = exercise_data['sets']
        if not isinstance(sets, list) or len(sets) == 0:
            errors.append(f"  Exercise '{exercise_name}' must have at least one set")
        else:
            for i, set_data in enumerate(sets):
                set_errors = validate_set(set_data, exercise_name, workout_name)
                errors.extend(set_errors)
    
    return errors


def validate_workout(workout_data):
    """Validate a single workout"""
    errors = []
    workout_name = workout_data.get('name', 'Unknown')
    
    for field in REQUIRED_WORKOUT_FIELDS:
        if field not in workout_data:
            errors.append(f"  Missing '{field}' in workout '{workout_name}'")
    
    # Validate week and day ranges
    if 'week' in workout_data:
        week = workout_data['week']
        if not isinstance(week, int) or week < 1:
            errors.append(f"  Invalid week number in '{workout_name}': {week}")
    
    if 'day' in workout_data:
        day = workout_data['day']
        if not isinstance(day, int) or day < 1:
            errors.append(f"  Invalid day number in '{workout_name}': {day}")
    
    # Validate exercises
    if 'exercises' in workout_data:
        exercises = workout_data['exercises']
        if not isinstance(exercises, list) or len(exercises) == 0:
            errors.append(f"  Workout '{workout_name}' must have at least one exercise")
        else:
            for exercise_data in exercises:
                exercise_errors = validate_exercise(exercise_data, workout_name)
                errors.extend(exercise_errors)
    
    return errors


def validate_program(file_path):
    """Validate a single program file"""
    errors = []
    
    try:
        data = load_program_file(file_path)
    except yaml.YAMLError as e:
        return [f"YAML parsing error: {e}"]
    except Exception as e:
        return [f"File reading error: {e}"]
    
    # Check required top-level fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")
    
    # Validate weeks consistency
    if 'weeks' in data and 'workouts' in data:
        declared_weeks = data['weeks']
        actual_weeks = set(w.get('week', 0) for w in data['workouts'])
        if len(actual_weeks) != declared_weeks:
            errors.append(f"Declared {declared_weeks} weeks but found {len(actual_weeks)} unique week numbers")
    
    # Validate workouts
    if 'workouts' in data:
        workouts = data['workouts']
        if not isinstance(workouts, list) or len(workouts) == 0:
            errors.append("Must have at least one workout")
        else:
            for workout_data in workouts:
                workout_errors = validate_workout(workout_data)
                errors.extend(workout_errors)
    
    return errors


def main():
    programs_dir = PROGRAMS_DIR

    if not programs_dir.exists():
        print("❌ Programs directory not found")
        sys.exit(1)
    
    yaml_files = iter_program_files(programs_dir)
    
    if not yaml_files:
        print("ℹ️ No YAML files found in programs/ directory")
        sys.exit(0)
    
    print(f"🔍 Validating {len(yaml_files)} program file(s)...\n")
    
    all_valid = True
    
    for yaml_file in sorted(yaml_files):
        print(f"📄 {yaml_file.name}")
        errors = validate_program(yaml_file)
        
        if errors:
            all_valid = False
            print(f"  ❌ {len(errors)} error(s):")
            for error in errors:
                print(f"    {error}")
        else:
            print(f"  ✅ Valid")
        print()
    
    if all_valid:
        print("✅ All programs are valid!")
        sys.exit(0)
    else:
        print("❌ Some programs have errors. Please fix them before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()