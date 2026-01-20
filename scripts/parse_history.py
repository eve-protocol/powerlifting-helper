#!/usr/bin/env python3
"""
Parses history.json from Boostcamp.
Outputs all-time PRs for Big 3 and variations.
Supports fetching fresh data from Boostcamp API.
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

try:
    import requests
except ImportError:
    requests = None  # Will error only if --fetch is used

# Boostcamp API configuration
BOOSTCAMP_API_URL = "https://newapi.boostcamp.app/api/www/programs/history"
DEFAULT_TOKEN_FILE = ".boostcamp_token"


def fetch_history(token_file=DEFAULT_TOKEN_FILE, output_file='history.json', timezone_offset=9):
    """Fetch workout history from Boostcamp API and save to file.
    
    Args:
        token_file: Path to file containing Firebase ID token
        output_file: Path to save the history JSON
        timezone_offset: Your timezone offset from UTC (default: 9 for JST)
    
    Returns:
        True if successful, False otherwise
    """
    if requests is None:
        print("Error: 'requests' library is required for --fetch.")
        print("Install with: pip install requests")
        return False
    
    # Read token from file
    if not os.path.exists(token_file):
        print(f"Error: Token file not found: {token_file}")
        print(f"Create the file with your Firebase ID token from the browser.")
        print("(Login to Boostcamp web, press F12 → Network tab, copy the token)")
        return False
    
    with open(token_file, 'r') as f:
        token = f.read().strip()
    
    if not token:
        print(f"Error: Token file is empty: {token_file}")
        return False
    
    # Make API request
    headers = {
        'Authorization': f'FirebaseIdToken:{token}',
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': 'https://www.boostcamp.app',
        'Referer': 'https://www.boostcamp.app/',
    }
    
    payload = {'timezone_offset': timezone_offset}
    
    print(f"Fetching history from Boostcamp API...")
    
    try:
        response = requests.post(BOOSTCAMP_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print("Error: Token expired or invalid. Get a fresh token from the browser.")
        else:
            print(f"Error: HTTP {response.status_code} - {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error: Network request failed - {e}")
        return False
    
    # Save to file
    try:
        data = response.json()
        with open(output_file, 'w') as f:
            json.dump(data, f)
        print(f"✓ History saved to {output_file} ({len(data.get('data', {}))} days)")
        return True
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error: Failed to save history - {e}")
        return False


def load_history(filepath='history.json'):
    """Load history JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def parse_all_workouts(data):
    """Parse ALL workout data from Boostcamp format (no time filter)."""
    workouts = []
    date_data = data.get('data', {})
    
    for date_str, day_workouts in date_data.items():
        if not isinstance(date_str, str) or len(date_str) != 10:
            continue
        
        for workout in day_workouts:
            records = workout.get('records', [])
            
            for exercise in records:
                name = exercise.get('name', '')
                
                for s in exercise.get('sets', []):
                    if s.get('skipped', False):
                        continue
                    
                    archived_weight_lbs = s.get('archived_weight', 0)
                    archived_reps = s.get('archived_reps', s.get('amount', 0))
                    rpe = s.get('archived_rpe', s.get('rpe', None))
                    
                    try:
                        weight = float(archived_weight_lbs) / 2.20462
                        reps = int(archived_reps) if archived_reps else 0
                    except (ValueError, TypeError):
                        continue
                    
                    if weight > 0 and reps > 0:
                        workouts.append({
                            'date': date_str,
                            'name': name,
                            'weight': round(weight, 1),
                            'reps': reps,
                            'rpe': rpe
                        })
    
    return workouts

def find_all_rep_maxes(workouts, exercise_filter=None):
    """Find best weight for each exercise at each rep count (all reps, not hardcoded)."""
    maxes = defaultdict(lambda: defaultdict(lambda: {'weight': 0, 'date': '', 'rpe': None}))
    
    for w in workouts:
        name = w['name']
        
        # Filter if specified
        if exercise_filter and not any(f.lower() in name.lower() for f in exercise_filter):
            continue
            
        reps = w['reps']
        
        if w['weight'] > maxes[name][reps]['weight']:
            maxes[name][reps] = {
                'weight': w['weight'],
                'date': w['date'],
                'rpe': w['rpe']
            }
    
    return maxes

# ANSI color codes for terminal output (with bold for better visibility)
# Using emoji indicators as fallback for terminals with non-standard color themes
COLORS = {
    'green': '\033[1;32m',      # Bold green - < 3 months (fresh PRs)
    'yellow': '\033[1;33m',     # Bold yellow - 3-6 months
    'orange': '\033[1;38;5;214m',  # Bold orange - 6-9 months
    'red': '\033[1;31m',        # Bold red - 9-12 months
    'purple': '\033[1;35m',     # Bold purple/magenta - > 1 year (stale)
    'reset': '\033[0m',
    'dim': '\033[2m',           # Dim for legend
}

# Emoji indicators for each age bracket
AGE_INDICATORS = {
    'fresh': '🟢',      # < 3 months
    'recent': '🟡',     # 3-6 months  
    'aging': '🟠',      # 6-9 months
    'old': '🔴',        # 9-12 months
    'stale': '🟣',      # > 1 year
}


def color_date(date_str, reference_date=None):
    """Return colored date string with emoji indicator based on how old the PR is.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        reference_date: Reference date for comparison (default: today)
    
    Returns:
        Colored date string with emoji indicator
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    try:
        pr_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return date_str  # Return uncolored if parsing fails
    
    days_old = (reference_date - pr_date).days
    
    if days_old < 90:  # < 3 months
        color = COLORS['green']
        emoji = AGE_INDICATORS['fresh']
    elif days_old < 180:  # 3-6 months
        color = COLORS['yellow']
        emoji = AGE_INDICATORS['recent']
    elif days_old < 270:  # 6-9 months
        color = COLORS['orange']
        emoji = AGE_INDICATORS['aging']
    elif days_old < 365:  # 9-12 months
        color = COLORS['red']
        emoji = AGE_INDICATORS['old']
    else:  # > 1 year
        color = COLORS['purple']
        emoji = AGE_INDICATORS['stale']
    
    return f"{emoji} {color}{date_str}{COLORS['reset']}"


def print_color_legend():
    """Print a legend explaining the date colors."""
    r = COLORS['reset']
    print(f"\nLegend: ", end="")
    print(f"🟢 <3mo  ", end="")
    print(f"🟡 3-6mo  ", end="")
    print(f"🟠 6-9mo  ", end="")
    print(f"🔴 9-12mo  ", end="")
    print(f"🟣 >1yr")


def print_rep_maxes(maxes, title):
    """Print rep maxes in a nice format with color-coded dates."""
    print(f"\n{'='*70}")
    print(title)
    print('='*70)
    
    for name in sorted(maxes.keys()):
        print(f"\n📊 {name}")
        print("-" * 50)
        
        # Sort by reps
        for reps in sorted(maxes[name].keys()):
            w = maxes[name][reps]
            rpe_str = f"@RPE {w['rpe']}" if w['rpe'] else ""
            colored_date = color_date(w['date'])
            print(f"    {reps:2}RM: {w['weight']:6.1f}kg {rpe_str:12} ({colored_date})")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Parse Boostcamp workout history and display PRs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parse_history.py                     # Parse existing history.json
  python parse_history.py --fetch             # Fetch fresh data, then parse
  python parse_history.py --fetch --token ~/.mytoken  # Use custom token file
        """
    )
    parser.add_argument('--fetch', action='store_true',
                        help='Fetch fresh data from Boostcamp API before parsing')
    parser.add_argument('--token', default=DEFAULT_TOKEN_FILE,
                        help=f'Path to token file (default: {DEFAULT_TOKEN_FILE})')
    parser.add_argument('--history', default='history.json',
                        help='Path to history.json file (default: history.json)')
    args = parser.parse_args()
    
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    history_file = os.path.join(script_dir, args.history)
    token_file = os.path.join(script_dir, args.token) if not os.path.isabs(args.token) else args.token
    
    # Fetch if requested
    if args.fetch:
        if not fetch_history(token_file=token_file, output_file=history_file):
            sys.exit(1)
        print()  # Blank line after fetch
    
    print("=" * 70)
    print("BOOSTCAMP HISTORY PARSER - ALL-TIME PRs")
    print("=" * 70)
    
    # Load and parse all data
    try:
        data = load_history(history_file)
    except FileNotFoundError:
        print(f"Error: {history_file} not found.")
        print("Run with --fetch to download from Boostcamp API.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {history_file} - {e}")
        sys.exit(1)
    
    workouts = parse_all_workouts(data)
    print(f"\nTotal sets found (all time): {len(workouts)}")
    print_color_legend()
    
    # Define Big 3 main lifts
    big3_main = ['Squat (Low Bar)', 'Bench Press (Barbell)', 'Sumo Deadlift (Barbell)']
    
    # Define Big 3 variations
    big3_variations = [
        'Squat (Paused)', 'Tempo Squat', 'Squat (Smith',
        'Bench Press (Paused)', 'Spoto Press', 'Incline Bench Press',
        'Sumo Deadlift (Paused)', 'Romanian Deadlift'
    ]
    
    # Get all maxes
    all_maxes = find_all_rep_maxes(workouts)
    
    # Print Big 3 Main Lifts
    print_rep_maxes(
        {k: v for k, v in all_maxes.items() if any(m in k for m in big3_main)},
        "BIG 3 - MAIN LIFTS (All-Time PRs)"
    )
    
    # Print Big 3 Variations
    print_rep_maxes(
        {k: v for k, v in all_maxes.items() if any(v_name.lower() in k.lower() for v_name in big3_variations)},
        "BIG 3 - VARIATIONS (All-Time PRs)"
    )
    
    # Summary table for 1RMs
    print("\n" + "=" * 70)
    print("1RM SUMMARY")
    print("=" * 70)
    
    for name in sorted(all_maxes.keys()):
        if 1 in all_maxes[name]:
            w = all_maxes[name][1]
            # Show if it's a big 3 or variation
            if any(m in name for m in big3_main + big3_variations):
                rpe_str = f"@RPE {w['rpe']}" if w['rpe'] else ""
                colored_date = color_date(w['date'])
                print(f"{name:40} 1RM: {w['weight']:6.1f}kg {rpe_str:12} ({colored_date})")


if __name__ == '__main__':
    main()

