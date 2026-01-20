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

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required.")
    print("Install with: pip install requests")
    sys.exit(1)

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

# Boostcamp API configuration
BOOSTCAMP_API_URL = "https://newapi.boostcamp.app/api/www/programs/user_program/share_detail"
BOOSTCAMP_PROGRAMS_LIST_URL = "https://newapi.boostcamp.app/api/www/programs/user_programs/list"
FIREBASE_API_KEY = "AIzaSyAEJcoGF-5ueF3bvaujcJm2PUV7RHKQwTw"
FIREBASE_REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"

DEFAULT_REFRESH_TOKEN_FILE = ".boostcamp_refresh_token"
DEFAULT_CONFIG_FILE = "boostcamp_conf.json"


def refresh_access_token(refresh_token):
    """Exchange refresh token for a fresh access token.
    
    Args:
        refresh_token: Firebase refresh token
        
    Returns:
        tuple: (access_token, new_refresh_token) or (None, None) on failure
    """
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    
    try:
        response = requests.post(FIREBASE_REFRESH_URL, data=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        return data.get('id_token'), data.get('refresh_token')
    except requests.exceptions.RequestException as e:
        print(f"Error refreshing token: {e}")
        return None, None


def load_refresh_token(token_file):
    """Load the refresh token from file."""
    with open(token_file, 'r') as f:
        return f.read().strip()


def save_refresh_token(token_file, refresh_token):
    """Save the refresh token to file (in case it was rotated)."""
    with open(token_file, 'w') as f:
        f.write(refresh_token)


def to_snake_case(name):
    """Convert program name to snake_case filename.
    
    Example: 'Volume Block V3' -> 'volume_block_v3.json'
    """
    s = re.sub(r'[^\w\s]', '', name)
    s = re.sub(r'\s+', '_', s)
    s = s.lower()
    return f"{s}.json"


def load_config(config_file):
    """Load the boostcamp_conf.json configuration file."""
    with open(config_file, 'r') as f:
        return json.load(f)


def fetch_program(program_id, token):
    """Fetch a single program's details from the Boostcamp API."""
    headers = {
        'Authorization': f'FirebaseIdToken:{token}',
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': 'https://www.boostcamp.app',
        'Referer': 'https://www.boostcamp.app/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
    }
    
    payload = {'program_id': program_id}
    
    timestamp = int(time.time() * 1000)
    url = f"{BOOSTCAMP_API_URL}?_={timestamp}"
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    return response.json()


def fetch_user_programs(token):
    """Fetch list of all user's programs from Boostcamp API.
    
    Fetches from both:
    - /api/www/programs/user_programs/list (created programs)
    - /api/www/programs/continue/list (active programs you're using)
    
    Returns:
        list: List of program dicts with 'id' and 'title' keys
    """
    headers = {
        'Authorization': f'FirebaseIdToken:{token}',
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': 'https://www.boostcamp.app',
        'Referer': 'https://www.boostcamp.app/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
    }
    
    all_programs = {}  # Use dict to dedupe by ID
    timestamp = int(time.time() * 1000)
    
    # Fetch created programs - use correct pagination format
    try:
        payload = {'pagination': {'current': 1, 'pageSize': 200}}
        url = f"{BOOSTCAMP_PROGRAMS_LIST_URL}?_={timestamp}"
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        for prog in data.get('data', {}).get('rows', []):
            all_programs[prog.get('id')] = prog
    except Exception as e:
        print(f"   Warning: Could not fetch created programs: {e}")
    
    # Fetch active/continue programs
    try:
        url = f"https://newapi.boostcamp.app/api/www/programs/continue/list?_={timestamp}"
        response = requests.post(url, headers=headers, json={}, timeout=30)
        response.raise_for_status()
        data = response.json()
        for prog in data.get('data', []):
            all_programs[prog.get('id')] = prog
    except Exception as e:
        print(f"   Warning: Could not fetch active programs: {e}")
    
    return list(all_programs.values())


def resolve_programs_by_name(program_names, all_programs):
    """Resolve program names to IDs using the fetched program list.
    
    Args:
        program_names: List of program names to find
        all_programs: List of all user programs from API
        
    Returns:
        list: List of dicts with 'id' and 'name' for matched programs
    """
    resolved = []
    
    # Create a lowercase lookup map
    name_to_program = {}
    for prog in all_programs:
        title = prog.get('title', '')
        name_to_program[title.lower()] = prog
    
    for name in program_names:
        name_lower = name.lower()
        if name_lower in name_to_program:
            prog = name_to_program[name_lower]
            resolved.append({
                'id': prog.get('id'),
                'name': prog.get('title')
            })
        else:
            # Try partial match
            matched = False
            for title, prog in name_to_program.items():
                if name_lower in title or title in name_lower:
                    resolved.append({
                        'id': prog.get('id'),
                        'name': prog.get('title')
                    })
                    matched = True
                    break
            if not matched:
                print(f"⚠️  Could not find program: '{name}'")
    
    return resolved


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


def display_program(data, program_name):
    """Display program in a nice formatted table."""
    c = COLORS
    
    title = data.get('data', {}).get('title', program_name)
    print(f"\n{c['header']}{'═' * 80}{c['reset']}")
    print(f"{c['header']}  📋 {title}{c['reset']}")
    print(f"{c['header']}{'═' * 80}{c['reset']}")
    
    # Get workouts from variations
    variations = data.get('data', {}).get('variations', [])
    if not variations:
        print("  No workout data found.")
        return
    
    workouts = variations[0].get('workouts', [])
    if not workouts:
        print("  No workouts found.")
        return
    
    # Organize by week and day
    program_structure = defaultdict(lambda: defaultdict(list))
    for workout in workouts:
        week = workout.get('week', 0)
        day = workout.get('day', 0)
        exercises = workout.get('exercises', [])
        program_structure[week][day] = exercises
    
    # Display each week
    for week in sorted(program_structure.keys()):
        print(f"\n{c['week']}┌{'─' * 78}┐{c['reset']}")
        print(f"{c['week']}│ 📅 WEEK {week + 1:<69}│{c['reset']}")
        print(f"{c['week']}├{'─' * 78}┤{c['reset']}")
        
        days = program_structure[week]
        
        for day in sorted(days.keys()):
            exercises = days[day]
            
            print(f"{c['day']}│   Day {day + 1}{c['reset']}")
            print(f"│   {'─' * 74}")
            
            # Table header
            print(f"│   {'Exercise':<35} {'Sets x Reps':<25} {'Notes':<12}")
            print(f"│   {'─' * 35} {'─' * 25} {'─' * 12}")
            
            for ex in exercises:
                name = ex.get('name', 'Unknown')
                sets = ex.get('sets', [])
                
                # Truncate long names
                if len(name) > 33:
                    name = name[:30] + "..."
                
                sets_summary = summarize_sets(sets)
                ex_type = ex.get('type', '')
                
                print(f"│   {name:<35} {sets_summary:<25} {ex_type:<12}")
            
            print(f"│")
        
        print(f"{c['week']}└{'─' * 78}┘{c['reset']}")


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
    """Generate markdown file for a program.
    
    Args:
        data: Program data from API
        program_name: Name of the program
        output_path: Path to save the markdown file
        
    Returns:
        Path to the generated file
    """
    from datetime import datetime
    
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


def get_access_token(script_dir):
    """Get a valid access token, refreshing if necessary.
    
    Returns:
        str: Valid access token or None on failure
    """
    refresh_token_file = os.path.join(script_dir, DEFAULT_REFRESH_TOKEN_FILE)
    
    if not os.path.exists(refresh_token_file):
        print(f"Error: Refresh token file not found: {refresh_token_file}")
        print("\nTo set up authentication:")
        print("1. Open https://www.boostcamp.app in your browser")
        print("2. Login if needed")
        print("3. Open DevTools (F12) → Application → Local Storage")
        print("4. Find the 'refreshToken' in the USER_INFO key")
        print(f"5. Save it to: {refresh_token_file}")
        return None
    
    refresh_token = load_refresh_token(refresh_token_file)
    
    if not refresh_token:
        print(f"Error: Refresh token file is empty: {refresh_token_file}")
        return None
    
    print("🔑 Refreshing access token...")
    access_token, new_refresh_token = refresh_access_token(refresh_token)
    
    if not access_token:
        print("❌ Failed to refresh token. The refresh token may have expired.")
        print("   Please update the refresh token from your browser.")
        return None
    
    # Save new refresh token if it was rotated
    if new_refresh_token and new_refresh_token != refresh_token:
        save_refresh_token(refresh_token_file, new_refresh_token)
        print("   (Refresh token updated)")
    
    print("✅ Token refreshed successfully!")
    return access_token


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
    # Config can be either:
    # 1. List of {"id": "...", "name": "..."} - use directly
    # 2. List of {"name": "..."} - resolve IDs from API
    # 3. List of strings - treat as names, resolve IDs from API
    
    needs_resolution = False
    program_names = []
    
    for prog in programs_config:
        if isinstance(prog, str):
            # Simple string format
            program_names.append(prog)
            needs_resolution = True
        elif isinstance(prog, dict):
            if not prog.get('id'):
                # Has name but no ID
                program_names.append(prog.get('name', ''))
                needs_resolution = True
    
    if needs_resolution:
        print("📋 Fetching program list to resolve names...")
        try:
            all_programs = fetch_user_programs(token)
            print(f"   Found {len(all_programs)} programs in your account")
            
            # Resolve names to IDs
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
        # Use config directly (already has IDs)
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
