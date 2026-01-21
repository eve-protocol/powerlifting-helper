#!/usr/bin/env python3
"""
Fetches program details from Boostcamp API for all programs in boostcamp_conf.json.
Outputs each program to a JSON file named after the program (snake_case).
Also displays a formatted table of the program structure.

Uses refresh token for automatic authentication - no more manual token copying!
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required.")
    print("Install with: pip install requests")
    sys.exit(1)

from powerlifting import (
    get_access_token,
    fetch_program,
    fetch_user_programs,
    resolve_programs_by_name,
    load_config,
    DEFAULT_CONFIG_FILE,
)

# ANSI color codes
COLORS = {
    'header': '\033[1;36m',    # Cyan bold
    'week': '\033[1;33m',      # Yellow bold  
    'day': '\033[1;32m',       # Green bold
    'exercise': '\033[1;37m',  # White bold
    'intensity': '\033[1;35m', # Magenta bold
    'reset': '\033[0m',
    'dim': '\033[2m',
}


def to_snake_case(name):
    """Convert program name to snake_case filename.
    
    Example: 'Volume Block V3' -> 'volume_block_v3.json'
    """
    s = re.sub(r'[^\w\s]', '', name)
    s = re.sub(r'\s+', '_', s)
    s = s.lower()
    return f"{s}.json"


def format_intensity(intensity, unit):
    """Format intensity with appropriate display."""
    if unit == '%':
        return f"{intensity}%"
    elif unit == 'RPE':
        return f"RPE {intensity}"
    else:
        return str(intensity)


def summarize_sets(sets):
    """Summarize sets into a compact format like '4x3 @83%' or '3x12 @RPE8'."""
    if not sets:
        return "-"
    
    # Group sets by (target, intensity, intensity_unit)
    groups = defaultdict(int)
    for s in sets:
        target = s.get('target', 0)
        intensity = s.get('intensity', 0)
        unit = s.get('intensity_unit', '')
        groups[(target, intensity, unit)] += 1
    
    # Format each group
    parts = []
    for (target, intensity, unit), count in groups.items():
        intensity_str = format_intensity(intensity, unit)
        parts.append(f"{count}x{target} @{intensity_str}")
    
    return ", ".join(parts)


def display_program_compact(data, program_name):
    """Display program with each day in its own block for readability."""
    c = COLORS
    
    title = data.get('data', {}).get('title', program_name)
    
    # Get workouts from variations
    variations = data.get('data', {}).get('variations', [])
    if not variations:
        return
    
    workouts = variations[0].get('workouts', [])
    if not workouts:
        return
    
    # Organize by week and day
    program_structure = defaultdict(lambda: defaultdict(list))
    for workout in workouts:
        week = workout.get('week', 0)
        day = workout.get('day', 0)
        exercises = workout.get('exercises', [])
        program_structure[week][day] = exercises
    
    # Count weeks and days
    num_weeks = len(program_structure)
    num_days = max(len(days) for days in program_structure.values()) if program_structure else 0
    
    print(f"\n{c['header']}{'═' * 70}{c['reset']}")
    print(f"{c['header']}  📋 {title} ({num_weeks} weeks, {num_days} days/week){c['reset']}")
    print(f"{c['header']}{'═' * 70}{c['reset']}")
    
    # For each week
    for week in sorted(program_structure.keys()):
        days = program_structure[week]
        
        print(f"\n{c['week']}┏{'━' * 68}┓{c['reset']}")
        print(f"{c['week']}┃  📅 WEEK {week + 1:<57}┃{c['reset']}")
        print(f"{c['week']}┗{'━' * 68}┛{c['reset']}")
        
        # For each day in the week
        for day in sorted(days.keys()):
            exercises = days[day]
            
            print(f"\n{c['day']}  ▸ Day {day + 1}{c['reset']}")
            print(f"  {'─' * 66}")
            print(f"  {c['dim']}{'#':<3} {'Exercise':<35} {'Sets × Reps':<26}{c['reset']}")
            print(f"  {'─' * 66}")
            
            for i, ex in enumerate(exercises, 1):
                name = ex.get('name', 'Unknown')
                sets = ex.get('sets', [])
                
                # Truncate long names
                if len(name) > 33:
                    name = name[:30] + "..."
                
                sets_summary = summarize_sets(sets)
                
                print(f"  {i:<3} {name:<35} {sets_summary:<26}")
    
    print()


def generate_program_markdown(data, program_name, output_path):
    """Generate markdown file for a program."""
    lines = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    title = data.get('data', {}).get('title', program_name)
    
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"*Generated: {now}*")
    lines.append("")
    
    # Get workouts from variations
    variations = data.get('data', {}).get('variations', [])
    if not variations:
        lines.append("No workout data found.")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return output_path
    
    workouts = variations[0].get('workouts', [])
    if not workouts:
        lines.append("No workouts found.")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return output_path
    
    # Organize by week and day
    program_structure = defaultdict(lambda: defaultdict(list))
    for workout in workouts:
        week = workout.get('week', 0)
        day = workout.get('day', 0)
        exercises = workout.get('exercises', [])
        program_structure[week][day] = exercises
    
    # Count stats
    num_weeks = len(program_structure)
    num_days = max(len(days) for days in program_structure.values()) if program_structure else 0
    total_workouts = sum(len(days) for days in program_structure.values())
    
    # Overview
    lines.append("## Overview")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Weeks | {num_weeks} |")
    lines.append(f"| Days per week | {num_days} |")
    lines.append(f"| Total workouts | {total_workouts} |")
    lines.append("")
    
    # Program structure
    lines.append("## Program Structure")
    lines.append("")
    
    for week in sorted(program_structure.keys()):
        days = program_structure[week]
        lines.append(f"### Week {week + 1}")
        lines.append("")
        
        for day in sorted(days.keys()):
            exercises = days[day]
            lines.append(f"#### Day {day + 1}")
            lines.append("")
            lines.append("| # | Exercise | Sets × Reps | Intensity |")
            lines.append("|---|----------|-------------|-----------|")
            
            for i, ex in enumerate(exercises, 1):
                name = ex.get('name', 'Unknown')
                sets = ex.get('sets', [])
                sets_summary = summarize_sets(sets)
                
                # Extract intensity from first set
                intensity = "-"
                if sets:
                    first_set = sets[0]
                    int_val = first_set.get('intensity', '')
                    int_unit = first_set.get('intensity_unit', '')
                    if int_val and int_unit:
                        if int_unit == '%':
                            intensity = f"{int_val}%"
                        elif int_unit == 'RPE':
                            intensity = f"RPE {int_val}"
                        else:
                            intensity = str(int_val)
                
                lines.append(f"| {i} | {name} | {sets_summary} | {intensity} |")
            
            lines.append("")
    
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return output_path


def main():
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    default_output_dir = os.path.join(project_root, 'values')
    default_markdown_dir = os.path.join(project_root, 'outputs')
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Fetch Boostcamp programs and save as JSON files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_programs.py                    # Output to <project>/values/
  python fetch_programs.py -o ./my-data/      # Output to custom directory
  python fetch_programs.py --no-markdown      # Skip markdown generation
        """
    )
    parser.add_argument('--output-dir', '-o', default=default_output_dir,
                        help=f'Output directory for program JSON files (default: {default_output_dir})')
    parser.add_argument('--markdown-dir', '-m', default=default_markdown_dir,
                        help=f'Output directory for markdown reports (default: {default_markdown_dir})')
    parser.add_argument('--no-markdown', action='store_true',
                        help='Skip markdown report generation')
    args = parser.parse_args()
    
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    
    config_file = os.path.join(script_dir, DEFAULT_CONFIG_FILE)
    
    # Load configuration
    if not os.path.exists(config_file):
        print(f"Error: Config file not found: {config_file}")
        sys.exit(1)
    
    config = load_config(config_file)
    programs_config = config.get('programs', [])
    
    if not programs_config:
        print("Error: No programs found in config file")
        sys.exit(1)
    
    # Get access token (automatically refreshes)
    token = get_access_token(script_dir)
    if not token:
        sys.exit(1)
    
    # Check if we need to resolve program names to IDs
    needs_resolution = False
    program_names = []
    
    for prog in programs_config:
        if isinstance(prog, str):
            program_names.append(prog)
            needs_resolution = True
        elif isinstance(prog, dict):
            if not prog.get('id'):
                program_names.append(prog.get('name', ''))
                needs_resolution = True
    
    if needs_resolution:
        print("📋 Fetching program list to resolve names...")
        try:
            all_programs = fetch_user_programs(token)
            print(f"   Found {len(all_programs)} programs in your account")
            
            programs = resolve_programs_by_name(program_names, all_programs)
            
            if not programs:
                print("❌ No programs could be resolved. Check your config file.")
                print("\nAvailable programs:")
                for p in all_programs:
                    print(f"   - {p.get('title')}")
                sys.exit(1)
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to fetch program list: {e}")
            sys.exit(1)
    else:
        programs = programs_config
    
    print(f"\nFound {len(programs)} programs to fetch")
    print("=" * 50)
    
    # Fetch each program
    for program in programs:
        program_id = program.get('id')
        program_name = program.get('name')
        
        if not program_id or not program_name:
            print(f"⚠️  Skipping invalid program entry: {program}")
            continue
        
        output_file = to_snake_case(program_name)
        output_path = os.path.join(output_dir, output_file)
        
        print(f"\n📥 Fetching: {program_name}")
        print(f"   ID: {program_id}")
        print(f"   Output: {output_file}")
        
        try:
            data = fetch_program(program_id, token)
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"   ✅ Saved successfully")
            
            # Generate markdown
            if not args.no_markdown:
                md_filename = to_snake_case(program_name).replace('.json', '.md')
                md_path = os.path.join(args.markdown_dir, md_filename)
                generate_program_markdown(data, program_name, md_path)
                print(f"   📝 Markdown: {md_filename}")
            
            # Display the program structure
            display_program_compact(data, program_name)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"   ❌ Token invalid. Please update your refresh token.")
                sys.exit(1)
            else:
                print(f"   ❌ HTTP Error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Network error: {e}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Small delay between requests
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("Done!")


if __name__ == '__main__':
    main()
