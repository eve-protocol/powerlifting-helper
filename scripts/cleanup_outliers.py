#!/usr/bin/env python3
"""
Powerlifting History Outlier Cleanup Script

This script applies hardcoded corrections to history.json data where isCopyLast=True
corrupted the weight field. Run this as part of CI or data processing pipeline.

The CORRECTIONS dict maps (date, lift_name, set_index) -> correct_weight
"""

import json
import sys
from pathlib import Path

# =============================================================================
# HARDCODED CORRECTIONS
# Format: (date, lift_name, set_index_in_record): correct_weight
# =============================================================================
CORRECTIONS = {
    # 2025-11-25 Sumo Deadlift Set 4: 177.5kg x5 @ 7 -> actually 120kg x5 @ 7
    ('2025-11-25', 'Sumo Deadlift (Barbell)', 3): 120.0,
    
    # 2025-08-23 Squat Set 4: 155kg x12 @ 7.5 -> actually 120kg x12 @ 7.5
    ('2025-08-23', 'Squat (Low Bar)', 3): 120.0,
    
    # 2025-08-11 Bench Press Set 5: 115kg x20 @ 10 -> actually 82.5kg x20 @ 10
    ('2025-08-11', 'Bench Press (Barbell)', 4): 82.5,
    
    # 2025-07-21 Bench Press Set 4: 120kg x10 @ 9.5 -> actually 100kg x10 @ 9.5
    ('2025-07-21', 'Bench Press (Barbell)', 3): 100.0,
    
    # Week 2 Day 5 additional corrections from user verification
    # 2026-01-24 Sumo Deadlift Set 2: 180kg x3 @ 6 -> actually 160kg x3 @ 6
    ('2026-01-24', 'Sumo Deadlift (Barbell)', 1): 160.0,
    
    # 2026-01-24 Bench Press Set 2: 115kg x3 @ 6 -> actually 110kg x3 @ 6
    ('2026-01-24', 'Bench Press (Barbell)', 1): 110.0,
    
    # 2025-08-21 Sumo Deadlift (Paused) Set 5: 150kg x8 @ 9 -> actually 130kg x8 @ 9
    ('2025-08-21', 'Sumo Deadlift (Paused)', 4): 130.0,
    
    # 2025-08-10 Squat Set 5: 147kg x10 @ 7.5 -> actually 120kg x10 @ 7.5
    ('2025-08-10', 'Squat (Low Bar)', 4): 120.0,
}


def load_history(filepath):
    """Load the history.json file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def save_history(data, filepath):
    """Save the corrected history.json file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved corrected history to {filepath}")


def apply_corrections(data, corrections):
    """
    Apply hardcoded corrections to the data.
    Returns (fixed_count, list_of_fixes)
    """
    fixed_count = 0
    fixes_log = []
    
    for (date, lift_name, set_idx), correct_weight in corrections.items():
        if date not in data.get('data', {}):
            continue
            
        for workout in data['data'][date]:
            for record in workout.get('records', []):
                if record.get('name') != lift_name:
                    continue
                
                sets = record.get('sets', [])
                if set_idx >= len(sets):
                    continue
                
                set_data = sets[set_idx]
                
                # Skip if not actually wrong
                old_weight = float(set_data.get('value') or 0)
                if abs(old_weight - correct_weight) < 0.1:
                    continue
                
                # Apply correction
                set_data['value'] = str(correct_weight)
                set_data['archived_weight'] = correct_weight * 2.20462  # Convert to lbs
                
                fix_info = {
                    'date': date,
                    'lift': lift_name,
                    'set': set_idx + 1,
                    'old_weight': old_weight,
                    'new_weight': correct_weight,
                    'reps': set_data.get('archived_reps'),
                    'rpe': set_data.get('archived_rpe')
                }
                fixes_log.append(fix_info)
                fixed_count += 1
    
    return fixed_count, fixes_log


def find_remaining_errors(data):
    """
    Find isCopyLast errors that don't have hardcoded corrections yet.
    Returns list of errors for user review.
    """
    errors = []
    
    for date, workouts in data.get('data', {}).items():
        for workout in workouts:
            for record in workout.get('records', []):
                name = record.get('name', '')
                sets = record.get('sets', [])
                
                for i in range(1, len(sets)):
                    curr = sets[i]
                    prev = sets[i-1]
                    
                    if not curr.get('isCopyLast', False):
                        continue
                    
                    prev_weight = float(prev.get('value') or 0) if prev.get('value') else 0
                    curr_weight = float(curr.get('value') or 0) if curr.get('value') else 0
                    
                    if prev_weight == 0 or curr_weight == 0:
                        continue
                    
                    # Same weight but different reps = likely error
                    if abs(prev_weight - curr_weight) < 1:
                        prev_reps = prev.get('archived_reps', 0)
                        curr_reps = curr.get('archived_reps', 0)
                        rpe = curr.get('archived_rpe') or curr.get('previous_rpe') or 0
                        
                        if abs(curr_reps - prev_reps) >= 2:
                            # Check if already in corrections
                            key = (date, name, i)
                            if key not in CORRECTIONS:
                                errors.append({
                                    'date': date,
                                    'lift': name,
                                    'set_idx': i,
                                    'wrong_weight': curr_weight,
                                    'reps': curr_reps,
                                    'rpe': rpe,
                                    'prev': f"{prev_weight}kg x {prev_reps}"
                                })
    
    return errors


def main():
    # Default path
    history_path = Path('/home/heavenlyren/.openclaw/workspace-ai-power/powerlifting-helper/values/history.json')
    
    if len(sys.argv) > 1:
        history_path = Path(sys.argv[1])
    
    if not history_path.exists():
        print(f"Error: File not found: {history_path}")
        sys.exit(1)
    
    print(f"Loading history from {history_path}...")
    data = load_history(history_path)
    
    print(f"\nApplying {len(CORRECTIONS)} hardcoded corrections...")
    fixed_count, fixes = apply_corrections(data, CORRECTIONS)
    
    if fixes:
        print(f"\nApplied {fixed_count} corrections:")
        for fix in fixes:
            print(f"  {fix['date']} | {fix['lift']} Set {fix['set']}: "
                  f"{fix['old_weight']}kg -> {fix['new_weight']}kg "
                  f"x {fix['reps']} @ RPE {fix['rpe']}")
    else:
        print("\nNo corrections needed (all already correct or no matches found)")
    
    # Find remaining errors
    remaining = find_remaining_errors(data)
    if remaining:
        print(f"\n{'='*70}")
        print(f"WARNING: {len(remaining)} isCopyLast errors still need correction:")
        print(f"{'='*70}")
        for err in remaining[:10]:  # Show first 10
            print(f"\n  {err['date']} | {err['lift']} Set {err['set_idx']+1}")
            print(f"    Logged: {err['wrong_weight']}kg x {err['reps']} @ RPE {err['rpe']}")
            print(f"    Prev set: {err['prev']}")
            print(f"    -> Add to CORRECTIONS: ('{err['date']}', '{err['lift']}', {err['set_idx']}): XX.X")
    
    # Save back to same file (CI will overwrite, but this is for local/processing use)
    save_history(data, history_path)
    print(f"\n{fixed_count} corrections applied. File saved.")
    
    # Exit with error code if there are remaining uncorrected errors
    if remaining:
        print(f"\n{len(remaining)} errors still need hardcoded corrections.")
        sys.exit(1)


if __name__ == '__main__':
    main()