#!/usr/bin/env python3
"""
Validate YAML program files against schema.
Exits with error if any file is invalid.
"""

import math
import sys
import yaml

from powerlifting.programs import PROGRAMS_DIR, iter_program_files, load_program_file
from powerlifting.program_workload import FAMILIES

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

    if 'target_weight_kg' in set_data:
        target_weight = set_data['target_weight_kg']
        if (
            isinstance(target_weight, bool)
            or not isinstance(target_weight, (int, float))
            or not math.isfinite(target_weight)
            or target_weight <= 0
        ):
            errors.append(
                f"  Invalid target_weight_kg for {exercise_name}: {target_weight}"
            )

    if 'target_weight_range_kg' in set_data:
        weight_range = set_data['target_weight_range_kg']
        if not isinstance(weight_range, list) or len(weight_range) != 2:
            errors.append(
                f"  Invalid target_weight_range_kg for {exercise_name}: {weight_range} "
                "(should be [min, max])"
            )
        elif any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
            for value in weight_range
        ) or weight_range[0] > weight_range[1]:
            errors.append(
                f"  Invalid target_weight_range_kg for {exercise_name}: {weight_range} "
                "(requires positive finite numbers in ascending order)"
            )
        else:
            target_weight = set_data.get('target_weight_kg')
            if (
                isinstance(target_weight, (int, float))
                and not isinstance(target_weight, bool)
                and not weight_range[0] <= target_weight <= weight_range[1]
            ):
                errors.append(
                    f"  target_weight_kg outside target_weight_range_kg for {exercise_name}"
                )
    
    if 'load_percent' in set_data:
        load_percent = set_data['load_percent']
        values = load_percent if isinstance(load_percent, list) else [load_percent]
        invalid_shape = isinstance(load_percent, list) and len(load_percent) != 2
        invalid_values = any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
            for value in values
        )
        if invalid_shape or invalid_values or (len(values) == 2 and values[0] > values[1]):
            errors.append(
                f"  Invalid load_percent for {exercise_name}: {load_percent} "
                "(requires a positive finite percentage or ordered [min, max])"
            )
        basis = set_data.get('load_percent_of')
        if not isinstance(basis, str) or not basis.strip():
            errors.append(f"  Missing or invalid load_percent_of for {exercise_name}")
    elif 'load_percent_of' in set_data:
        errors.append(f"  load_percent_of without load_percent for {exercise_name}")

    return errors


def validate_exercise(exercise_data, workout_name):
    """Validate a single exercise"""
    errors = []
    exercise_name = exercise_data.get('name', 'Unknown')
    
    for field in REQUIRED_EXERCISE_FIELDS:
        if field not in exercise_data:
            errors.append(f"  Missing '{field}' in exercise '{exercise_name}'")

    if 'intent' in exercise_data:
        intent = exercise_data['intent']
        if not isinstance(intent, str) or not intent.strip():
            errors.append(f"  Invalid intent for exercise '{exercise_name}'")
    
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


def validate_workload_summary(config, workouts):
    """Reject ambiguous family membership, invalid rounding and invalid exclusions."""
    if not isinstance(config, dict):
        return ["Invalid workload_summary: expected a mapping"]
    errors = []
    families = config.get('families')
    if not isinstance(families, dict) or set(families) != set(FAMILIES):
        return ["Invalid workload_summary.families: require Squat, Bench and Deadlift"]
    names = []
    for family, exercises in families.items():
        if (not isinstance(exercises, list) or not exercises
                or any(not isinstance(name, str) or not name.strip() for name in exercises)):
            errors.append(f"Invalid workload_summary.families.{family}: require exact exercise names")
        else:
            names.extend(exercises)
    if len(names) != len(set(names)):
        errors.append("Invalid workload_summary.families: duplicate exercise membership")
    known_names = {e['name'] for workout in workouts for e in workout.get('exercises', [])}
    if set(names) - known_names:
        errors.append("Invalid workload_summary.families: unknown exercise names")
    increment = config.get('plate_increment_kg', 2.5)
    if (isinstance(increment, bool) or not isinstance(increment, (int, float))
            or not math.isfinite(increment) or increment <= 0):
        errors.append("Invalid workload_summary.plate_increment_kg")
    exclusions = config.get('exclude_workouts', [])
    if not isinstance(exclusions, list):
        errors.append("Invalid workload_summary.exclude_workouts: require a list")
    else:
        known_workouts = {(workout['week'], workout['day']) for workout in workouts}
        seen = set()
        for exclusion in exclusions:
            if not isinstance(exclusion, dict):
                errors.append("Invalid workload_summary.exclude_workouts entry")
                continue
            key = (exclusion.get('week'), exclusion.get('day'))
            if (any(isinstance(n, bool) or not isinstance(n, int) for n in key)
                    or key not in known_workouts or key in seen):
                errors.append("Invalid workload_summary.exclude_workouts: unknown or duplicate workout")
            else:
                seen.add(key)
            reason = exclusion.get('reason')
            if not isinstance(reason, str) or not reason.strip():
                errors.append("Invalid workload_summary.exclude_workouts: require an explicit reason")
    if 'scope_note' in config and (not isinstance(config['scope_note'], str) or not config['scope_note'].strip()):
        errors.append("Invalid workload_summary.scope_note")
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

    if 'workload_summary' in data:
        errors.extend(validate_workload_summary(data['workload_summary'], data.get('workouts', [])))

    # Anchor-based programs are coaching documents as well as Boostcamp inputs.
    # Require the context that prevents a target weight from becoming rigid.
    if data.get('load_policy') and isinstance(data.get('workouts'), list):
        for workout_data in data['workouts']:
            workout_name = workout_data.get('name', 'Unknown')
            if not str(workout_data.get('intent', '')).strip():
                errors.append(f"  Missing workout intent in '{workout_name}'")
            for exercise_data in workout_data.get('exercises', []):
                exercise_name = exercise_data.get('name', 'Unknown')
                if not str(exercise_data.get('intent', '')).strip():
                    errors.append(
                        f"  Missing exercise intent for '{exercise_name}' in '{workout_name}'"
                    )
                for set_index, set_data in enumerate(exercise_data.get('sets', []), start=1):
                    if 'target_weight_kg' not in set_data:
                        errors.append(
                            f"  Missing target_weight_kg for set {set_index} of "
                            f"'{exercise_name}' in '{workout_name}'"
                        )
    
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
