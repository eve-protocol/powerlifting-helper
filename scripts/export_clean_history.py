#!/usr/bin/env python3
"""
Clean History Export Script

Converts history.json to a clean markdown file with:
- LBS converted to KG
- Only archived_* fields (source of truth)
- Target vs Actual comparison when available
- Easy to read format for AI analysis
"""

import json
from pathlib import Path
from datetime import datetime

LBS_TO_KG = 0.453592

def lbs_to_kg(lbs):
    """Convert lbs to kg, round to nearest 0.5kg"""
    if lbs is None or lbs == 0:
        return 0
    kg = float(lbs) * LBS_TO_KG
    return round(kg * 2) / 2

def format_set(set_data, set_num):
    """Format a single set for output"""
    # Get actual data (source of truth)
    weight_kg = lbs_to_kg(set_data.get('archived_weight'))
    reps = set_data.get('archived_reps', 0)
    rpe = set_data.get('archived_rpe') or set_data.get('previous_rpe') or '-'
    
    # Get target data (if available)
    target_reps = set_data.get('target')
    target_rpe = set_data.get('intensity')  # Usually [min, max] or single value
    
    # Skip skipped sets
    if set_data.get('skipped', False):
        return None
    
    # Build output string
    parts = [f"  Set {set_num}: {weight_kg}kg x {reps}"]
    
    if rpe != '-':
        parts.append(f"@ RPE {rpe}")
    
    # Add target comparison
    target_parts = []
    if target_reps and target_reps != reps:
        target_parts.append(f"target: {target_reps} reps")
    if target_rpe:
        if isinstance(target_rpe, list):
            target_parts.append(f"target RPE: {target_rpe[0]}-{target_rpe[1]}")
        else:
            target_parts.append(f"target RPE: {target_rpe}")
    
    if target_parts:
        parts.append(f"[{', '.join(target_parts)}]")
    
    return ' '.join(parts)

def generate_clean_history():
    """Generate clean markdown from history.json"""
    
    repo_path = Path('/home/heavenlyren/.openclaw/workspace-ai-power/powerlifting-helper')
    history_file = repo_path / 'values' / 'history.json'
    output_file = repo_path / 'outputs' / 'history_clean.md'
    
    with open(history_file, 'r') as f:
        data = json.load(f)
    
    lines = []
    lines.append("# Clean Training History")
    lines.append("")
    lines.append("*Auto-generated from history.json - uses archived_* fields only*")
    lines.append("")
    
    # Sort dates
    dates = sorted(data.get('data', {}).keys(), reverse=True)
    
    for date in dates:
        workouts = data['data'][date]
        
        for workout in workouts:
            # Header
            lines.append(f"## {date}")
            lines.append("")
            
            # Workout info
            title = workout.get('title', workout.get('name', 'Unknown'))
            lines.append(f"**{title}**")
            if workout.get('finished_at'):
                lines.append(f"Finished: {workout.get('finished_at')}")
            if workout.get('week'):
                lines.append(f"Week {workout.get('week')}, Day {workout.get('day')}")
            lines.append("")
            
            # Exercises
            for record in workout.get('records', []):
                exercise_name = record.get('name', 'Unknown')
                lines.append(f"### {exercise_name}")
                lines.append("")
                
                # Sets
                for i, set_data in enumerate(record.get('sets', []), 1):
                    set_str = format_set(set_data, i)
                    if set_str:
                        lines.append(set_str)
                
                lines.append("")
    
    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Generated clean history: {output_file}")
    print(f"Total workouts: {len(dates)}")

if __name__ == '__main__':
    generate_clean_history()