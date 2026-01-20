#!/usr/bin/env python3
"""
Parses history.json from Boostcamp.
Outputs all-time PRs for Big 3 and variations.
Supports fetching fresh data from Boostcamp API.
Generates markdown reports with trends, e1RM, and volume analytics.
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
FIREBASE_API_KEY = "AIzaSyAEJcoGF-5ueF3bvaujcJm2PUV7RHKQwTw"
FIREBASE_REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
DEFAULT_REFRESH_TOKEN_FILE = ".boostcamp_refresh_token"

# Big 3 configuration
BIG3_MAIN = ['Squat (Low Bar)', 'Bench Press (Barbell)', 'Sumo Deadlift (Barbell)']
BIG3_VARIATIONS = [
    'Squat (Paused)', 'Tempo Squat', 'Squat (Smith',
    'Bench Press (Paused)', 'Spoto Press', 'Incline Bench Press',
    'Sumo Deadlift (Paused)', 'Romanian Deadlift'
]

# Lift categories for grouping
LIFT_CATEGORIES = {
    'Squat': ['Squat (Low Bar)', 'Squat (Paused)', 'Tempo Squat', 'Squat (Smith'],
    'Bench': ['Bench Press (Barbell)', 'Bench Press (Paused)', 'Spoto Press', 'Incline Bench Press'],
    'Deadlift': ['Sumo Deadlift (Barbell)', 'Sumo Deadlift (Paused)', 'Romanian Deadlift']
}


def calculate_e1rm_brzycki(weight, reps):
    """Calculate estimated 1RM using Brzycki formula.
    
    Brzycki formula: 1RM = weight / (1.0278 - 0.0278 × reps)
    
    Args:
        weight: Weight lifted in kg
        reps: Number of reps performed
        
    Returns:
        Estimated 1RM in kg, or the actual weight if reps=1
    """
    if reps <= 0:
        return 0
    if reps == 1:
        return weight
    if reps >= 37:  # Brzycki formula becomes unreliable at very high reps
        return weight * 2  # Rough estimate
    
    return weight / (1.0278 - 0.0278 * reps)


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


def get_access_token(script_dir):
    """Get a valid access token, refreshing if necessary.
    
    Returns:
        str: Valid access token or None on failure
    """
    if requests is None:
        print("Error: 'requests' library is required for --fetch.")
        print("Install with: pip install requests")
        return None
    
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
    
    with open(refresh_token_file, 'r') as f:
        refresh_token = f.read().strip()
    
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
        with open(refresh_token_file, 'w') as f:
            f.write(new_refresh_token)
        print("   (Refresh token updated)")
    
    print("✅ Token refreshed successfully!")
    return access_token


def fetch_history(token, output_file='history.json', timezone_offset=9):
    """Fetch workout history from Boostcamp API and save to file.
    
    Args:
        token: Firebase ID token (access token)
        output_file: Path to save the history JSON
        timezone_offset: Your timezone offset from UTC (default: 9 for JST)
    
    Returns:
        True if successful, False otherwise
    """
    if requests is None:
        print("Error: 'requests' library is required for --fetch.")
        print("Install with: pip install requests")
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
            json.dump(data, f, indent=2)
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
                        e1rm = calculate_e1rm_brzycki(weight, reps)
                        workouts.append({
                            'date': date_str,
                            'name': name,
                            'weight': round(weight, 1),
                            'reps': reps,
                            'rpe': rpe,
                            'e1rm': round(e1rm, 1)
                        })
    
    return workouts


def find_all_rep_maxes(workouts, exercise_filter=None):
    """Find best weight for each exercise at each rep count (all reps, not hardcoded)."""
    maxes = defaultdict(lambda: defaultdict(lambda: {'weight': 0, 'date': '', 'rpe': None, 'e1rm': 0}))
    
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
                'rpe': w['rpe'],
                'e1rm': w['e1rm']
            }
    
    return maxes


def calculate_training_volume(workouts, exercise_filters, period='weekly'):
    """Calculate training volume (kg, reps, sets) for filtered exercises.
    
    Args:
        workouts: List of workout dicts
        exercise_filters: List of exercise name substrings to filter
        period: 'weekly' or 'monthly'
        
    Returns:
        dict: {period_key: {'total_kg': X, 'total_reps': Y, 'total_sets': Z}}
    """
    volume = defaultdict(lambda: {'total_kg': 0, 'total_reps': 0, 'total_sets': 0})
    
    for w in workouts:
        name = w['name']
        
        # Filter
        if not any(f.lower() in name.lower() for f in exercise_filters):
            continue
        
        try:
            date = datetime.strptime(w['date'], '%Y-%m-%d')
        except ValueError:
            continue
        
        if period == 'weekly':
            # ISO week number
            key = f"{date.isocalendar()[0]}-W{date.isocalendar()[1]:02d}"
        else:  # monthly
            key = f"{date.year}-{date.month:02d}"
        
        volume[key]['total_kg'] += w['weight'] * w['reps']
        volume[key]['total_reps'] += w['reps']
        volume[key]['total_sets'] += 1
    
    return dict(volume)


def analyze_trends(workouts, exercise_filters, period='weekly'):
    """Analyze progression trends for exercises.
    
    Tracks best estimated 1RM per period.
    
    Args:
        workouts: List of workout dicts
        exercise_filters: List of exercise name substrings to filter
        period: 'weekly' or 'monthly'
        
    Returns:
        dict: {period_key: best_e1rm}
    """
    trends = defaultdict(lambda: 0)
    
    for w in workouts:
        name = w['name']
        
        # Filter
        if not any(f.lower() in name.lower() for f in exercise_filters):
            continue
        
        try:
            date = datetime.strptime(w['date'], '%Y-%m-%d')
        except ValueError:
            continue
        
        if period == 'weekly':
            key = f"{date.isocalendar()[0]}-W{date.isocalendar()[1]:02d}"
        else:  # monthly
            key = f"{date.year}-{date.month:02d}"
        
        if w['e1rm'] > trends[key]:
            trends[key] = w['e1rm']
    
    return dict(trends)


def get_summary_stats(workouts, data):
    """Get summary statistics from workout data."""
    if not workouts:
        return {}
    
    dates = [w['date'] for w in workouts]
    date_set = set(dates)
    
    return {
        'total_sets': len(workouts),
        'total_days': len(date_set),
        'date_range_start': min(dates),
        'date_range_end': max(dates),
        'total_days_in_data': len(data.get('data', {}))
    }


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
    'cyan': '\033[1;36m',       # Cyan bold for headers
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


def print_summary(stats, workouts):
    """Print summary statistics."""
    c = COLORS
    print(f"\n{c['cyan']}📊 SUMMARY{c['reset']}")
    print("-" * 50)
    print(f"   Date Range: {stats['date_range_start']} → {stats['date_range_end']}")
    print(f"   Training Days: {stats['total_days']}")
    print(f"   Total Sets: {stats['total_sets']}")
    
    # Count Big 3 sets
    big3_sets = [w for w in workouts if any(m in w['name'] for m in BIG3_MAIN)]
    print(f"   Big 3 Sets: {len(big3_sets)}")


def get_best_recent_e1rm(workouts, exercise_name, max_reps=6, months=2):
    """Find the best e1RM from recent sets with limited rep ranges.
    
    Args:
        workouts: List of workout dicts
        exercise_name: Exact name of the exercise to filter
        max_reps: Only consider sets with reps <= this value (default: 6)
        months: Only consider sets within this many months (default: 2)
        
    Returns:
        dict: {'e1rm': float, 'reps': int, 'date': str, 'weight': float} or None
    """
    cutoff_date = datetime.now() - timedelta(days=months * 30)
    
    best_e1rm = 0
    best_data = None
    
    for w in workouts:
        if w['name'] != exercise_name:
            continue
        
        # Filter by reps
        if w['reps'] > max_reps:
            continue
        
        # Filter by date
        try:
            workout_date = datetime.strptime(w['date'], '%Y-%m-%d')
            if workout_date < cutoff_date:
                continue
        except ValueError:
            continue
        
        if w['e1rm'] > best_e1rm:
            best_e1rm = w['e1rm']
            best_data = {
                'e1rm': w['e1rm'],
                'reps': w['reps'],
                'date': w['date'],
                'weight': w['weight']
            }
    
    return best_data


def print_e1rm_summary(all_maxes, workouts):
    """Print estimated 1RM summary for Big 3.
    
    Best e1RM is calculated from recent sets (within 2 months) with <= 6 reps.
    """
    c = COLORS
    print(f"\n{c['cyan']}💪 ESTIMATED 1RM (Brzycki Formula){c['reset']}")
    print(f"{c['dim']}Best e1RM from sets ≤6 reps within last 2 months{c['reset']}")
    print("-" * 70)
    print(f"{'Lift':<40} {'Actual 1RM':>12} {'Best e1RM':>12} {'From':>8}")
    print("-" * 70)
    
    for name in sorted(all_maxes.keys()):
        if not any(m in name for m in BIG3_MAIN):
            continue
        
        # Get actual 1RM
        actual_1rm = all_maxes[name].get(1, {}).get('weight', 0)
        
        # Find best e1RM from recent sets with <= 6 reps
        recent_best = get_best_recent_e1rm(workouts, name, max_reps=6, months=2)
        
        best_e1rm = recent_best['e1rm'] if recent_best else 0
        best_reps = recent_best['reps'] if recent_best else 0
        
        actual_str = f"{actual_1rm:.1f}kg" if actual_1rm > 0 else "-"
        e1rm_str = f"{best_e1rm:.1f}kg" if best_e1rm > 0 else "-"
        from_str = f"{best_reps}RM" if best_reps > 0 else "-"
        
        print(f"{name:<40} {actual_str:>12} {e1rm_str:>12} {from_str:>8}")


def print_volume_summary(workouts):
    """Print training volume summary."""
    c = COLORS
    print(f"\n{c['cyan']}📈 WEEKLY TRAINING VOLUME (Last 4 Weeks){c['reset']}")
    print("-" * 80)
    print(f"{'Week':<12} {'Squat (kg/reps/sets)':>22} {'Bench (kg/reps/sets)':>22} {'Deadlift (kg/reps/sets)':>22}")
    print("-" * 80)
    
    # Get volume for each category
    squat_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Squat'], 'weekly')
    bench_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Bench'], 'weekly')
    deadlift_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Deadlift'], 'weekly')
    
    # Get all weeks and sort
    all_weeks = set(squat_vol.keys()) | set(bench_vol.keys()) | set(deadlift_vol.keys())
    sorted_weeks = sorted(all_weeks, reverse=True)[:4]  # Last 4 weeks
    
    for week in sorted_weeks:
        sq = squat_vol.get(week, {'total_kg': 0, 'total_reps': 0, 'total_sets': 0})
        bn = bench_vol.get(week, {'total_kg': 0, 'total_reps': 0, 'total_sets': 0})
        dl = deadlift_vol.get(week, {'total_kg': 0, 'total_reps': 0, 'total_sets': 0})
        
        sq_str = f"{sq['total_kg']:.0f}/{sq['total_reps']}/{sq['total_sets']}"
        bn_str = f"{bn['total_kg']:.0f}/{bn['total_reps']}/{bn['total_sets']}"
        dl_str = f"{dl['total_kg']:.0f}/{dl['total_reps']}/{dl['total_sets']}"
        
        print(f"{week:<12} {sq_str:>22} {bn_str:>22} {dl_str:>22}")


def print_trends(workouts):
    """Print Big 3 trends."""
    c = COLORS
    print(f"\n{c['cyan']}📉 BIG 3 TRENDS (Best e1RM per Week, Last 6 Weeks){c['reset']}")
    print("-" * 60)
    print(f"{'Week':<12} {'Squat':>14} {'Bench':>14} {'Deadlift':>14}")
    print("-" * 60)
    
    # Get trends for main lifts only
    squat_trends = analyze_trends(workouts, [BIG3_MAIN[0]], 'weekly')
    bench_trends = analyze_trends(workouts, [BIG3_MAIN[1]], 'weekly')
    deadlift_trends = analyze_trends(workouts, [BIG3_MAIN[2]], 'weekly')
    
    all_weeks = set(squat_trends.keys()) | set(bench_trends.keys()) | set(deadlift_trends.keys())
    sorted_weeks = sorted(all_weeks, reverse=True)[:6]  # Last 6 weeks
    
    for week in sorted_weeks:
        sq = squat_trends.get(week, 0)
        bn = bench_trends.get(week, 0)
        dl = deadlift_trends.get(week, 0)
        
        sq_str = f"{sq:.1f}kg" if sq > 0 else "-"
        bn_str = f"{bn:.1f}kg" if bn > 0 else "-"
        dl_str = f"{dl:.1f}kg" if dl > 0 else "-"
        
        print(f"{week:<12} {sq_str:>14} {bn_str:>14} {dl_str:>14}")


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
            e1rm_str = f"(e1RM: {w['e1rm']:.1f}kg)" if reps > 1 else ""
            colored_date = color_date(w['date'])
            print(f"    {reps:2}RM: {w['weight']:6.1f}kg {rpe_str:12} {e1rm_str:18} ({colored_date})")


def generate_markdown_report(workouts, all_maxes, stats, output_path):
    """Generate comprehensive markdown report."""
    lines = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    lines.append("# Workout History Analysis")
    lines.append(f"")
    lines.append(f"*Generated: {now}*")
    lines.append("")
    
    # Summary
    lines.append("## 📊 Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Date Range | {stats['date_range_start']} → {stats['date_range_end']} |")
    lines.append(f"| Training Days | {stats['total_days']} |")
    lines.append(f"| Total Sets | {stats['total_sets']} |")
    lines.append("")
    
    # Big 3 Performance Summary
    lines.append("## 💪 Big 3 Performance Summary")
    lines.append("")
    lines.append("*Estimated 1RM calculated using Brzycki formula: `1RM = weight / (1.0278 - 0.0278 × reps)`*")
    lines.append("")
    lines.append("*Best e1RM from sets ≤6 reps within last 2 months*")
    lines.append("")
    lines.append("| Lift | Actual 1RM | Best e1RM | From | Date |")
    lines.append("|------|------------|-----------|------|------|")
    
    for name in sorted(all_maxes.keys()):
        if not any(m in name for m in BIG3_MAIN):
            continue
        
        actual_1rm_data = all_maxes[name].get(1, {})
        actual_1rm = actual_1rm_data.get('weight', 0)
        
        # Find best e1RM from recent sets with <= 6 reps
        recent_best = get_best_recent_e1rm(workouts, name, max_reps=6, months=2)
        
        best_e1rm = recent_best['e1rm'] if recent_best else 0
        best_reps = recent_best['reps'] if recent_best else 0
        best_date = recent_best['date'] if recent_best else '-'
        
        actual_str = f"{actual_1rm:.1f}kg" if actual_1rm > 0 else "-"
        e1rm_str = f"{best_e1rm:.1f}kg" if best_e1rm > 0 else "-"
        from_str = f"{best_reps}RM" if best_reps > 0 else "-"
        
        lines.append(f"| {name} | {actual_str} | {e1rm_str} | {from_str} | {best_date} |")
    
    lines.append("")
    
    # Trends
    lines.append("## 📈 Trends (Best e1RM per Week)")
    lines.append("")
    
    squat_trends = analyze_trends(workouts, [BIG3_MAIN[0]], 'weekly')
    bench_trends = analyze_trends(workouts, [BIG3_MAIN[1]], 'weekly')
    deadlift_trends = analyze_trends(workouts, [BIG3_MAIN[2]], 'weekly')
    
    all_weeks = set(squat_trends.keys()) | set(bench_trends.keys()) | set(deadlift_trends.keys())
    sorted_weeks = sorted(all_weeks, reverse=True)[:8]  # Last 8 weeks
    
    lines.append("| Week | Squat | Bench | Deadlift |")
    lines.append("|------|-------|-------|----------|")
    
    for week in sorted_weeks:
        sq = squat_trends.get(week, 0)
        bn = bench_trends.get(week, 0)
        dl = deadlift_trends.get(week, 0)
        
        sq_str = f"{sq:.1f}kg" if sq > 0 else "-"
        bn_str = f"{bn:.1f}kg" if bn > 0 else "-"
        dl_str = f"{dl:.1f}kg" if dl > 0 else "-"
        
        lines.append(f"| {week} | {sq_str} | {bn_str} | {dl_str} |")
    
    lines.append("")
    
    # Training Volume
    lines.append("## 🏋️ Weekly Training Volume")
    lines.append("")
    lines.append("*Format: total kg / reps / sets*")
    lines.append("")
    
    squat_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Squat'], 'weekly')
    bench_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Bench'], 'weekly')
    deadlift_vol = calculate_training_volume(workouts, LIFT_CATEGORIES['Deadlift'], 'weekly')
    
    all_vol_weeks = set(squat_vol.keys()) | set(bench_vol.keys()) | set(deadlift_vol.keys())
    sorted_vol_weeks = sorted(all_vol_weeks, reverse=True)[:8]
    
    lines.append("| Week | Squat | Bench | Deadlift |")
    lines.append("|------|-------|-------|----------|")
    
    for week in sorted_vol_weeks:
        sq = squat_vol.get(week, {'total_kg': 0, 'total_reps': 0, 'total_sets': 0})
        bn = bench_vol.get(week, {'total_kg': 0, 'total_reps': 0, 'total_sets': 0})
        dl = deadlift_vol.get(week, {'total_kg': 0, 'total_reps': 0, 'total_sets': 0})
        
        sq_str = f"{sq['total_kg']:.0f}/{sq['total_reps']}/{sq['total_sets']}"
        bn_str = f"{bn['total_kg']:.0f}/{bn['total_reps']}/{bn['total_sets']}"
        dl_str = f"{dl['total_kg']:.0f}/{dl['total_reps']}/{dl['total_sets']}"
        
        lines.append(f"| {week} | {sq_str} | {bn_str} | {dl_str} |")
    
    lines.append("")
    
    # All-Time PRs
    lines.append("## 🏆 All-Time PRs")
    lines.append("")
    
    # Big 3 Main Lifts
    lines.append("### Big 3 - Main Lifts")
    lines.append("")
    
    for name in sorted(all_maxes.keys()):
        if not any(m in name for m in BIG3_MAIN):
            continue
        
        lines.append(f"#### {name}")
        lines.append("")
        lines.append("| Reps | Weight | e1RM | RPE | Date |")
        lines.append("|------|--------|------|-----|------|")
        
        for reps in sorted(all_maxes[name].keys()):
            w = all_maxes[name][reps]
            rpe_str = str(w['rpe']) if w['rpe'] else "-"
            e1rm_str = f"{w['e1rm']:.1f}kg" if reps > 1 else "-"
            lines.append(f"| {reps}RM | {w['weight']:.1f}kg | {e1rm_str} | {rpe_str} | {w['date']} |")
        
        lines.append("")
    
    # Big 3 Variations
    lines.append("### Big 3 - Variations")
    lines.append("")
    
    for name in sorted(all_maxes.keys()):
        if not any(v.lower() in name.lower() for v in BIG3_VARIATIONS):
            continue
        if any(m in name for m in BIG3_MAIN):  # Skip main lifts
            continue
        
        lines.append(f"#### {name}")
        lines.append("")
        lines.append("| Reps | Weight | e1RM | RPE | Date |")
        lines.append("|------|--------|------|-----|------|")
        
        for reps in sorted(all_maxes[name].keys()):
            w = all_maxes[name][reps]
            rpe_str = str(w['rpe']) if w['rpe'] else "-"
            e1rm_str = f"{w['e1rm']:.1f}kg" if reps > 1 else "-"
            lines.append(f"| {reps}RM | {w['weight']:.1f}kg | {e1rm_str} | {rpe_str} | {w['date']} |")
        
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
        description='Parse Boostcamp workout history and display PRs with analytics.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parse_history.py                     # Parse existing history.json
  python parse_history.py --fetch             # Fetch fresh data, then parse
  python parse_history.py -o ./my-data/       # Use custom output directory
  python parse_history.py --no-markdown       # Skip markdown generation
        """
    )
    parser.add_argument('--fetch', action='store_true',
                        help='Fetch fresh data from Boostcamp API before parsing')
    parser.add_argument('--history', default='history.json',
                        help='Path to history.json file (default: history.json in output dir)')
    parser.add_argument('--output-dir', '-o', default=default_output_dir,
                        help=f'Output directory for history.json (default: {default_output_dir})')
    parser.add_argument('--markdown-dir', '-m', default=default_markdown_dir,
                        help=f'Output directory for markdown reports (default: {default_markdown_dir})')
    parser.add_argument('--no-markdown', action='store_true',
                        help='Skip markdown report generation')
    args = parser.parse_args()
    
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    
    history_file = os.path.join(output_dir, args.history)
    
    # Fetch if requested
    if args.fetch:
        token = get_access_token(script_dir)
        if not token:
            sys.exit(1)
        if not fetch_history(token=token, output_file=history_file):
            sys.exit(1)
        print()  # Blank line after fetch
    
    print("=" * 70)
    print("BOOSTCAMP HISTORY PARSER - ALL-TIME PRs & ANALYTICS")
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
    stats = get_summary_stats(workouts, data)
    
    # Print summary and analytics
    print_summary(stats, workouts)
    print_color_legend()
    print_e1rm_summary(find_all_rep_maxes(workouts), workouts)
    print_trends(workouts)
    print_volume_summary(workouts)
    
    # Get all maxes
    all_maxes = find_all_rep_maxes(workouts)
    
    # Print Big 3 Main Lifts
    print_rep_maxes(
        {k: v for k, v in all_maxes.items() if any(m in k for m in BIG3_MAIN)},
        "BIG 3 - MAIN LIFTS (All-Time PRs)"
    )
    
    # Print Big 3 Variations
    print_rep_maxes(
        {k: v for k, v in all_maxes.items() if any(v_name.lower() in k.lower() for v_name in BIG3_VARIATIONS)},
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
            if any(m in name for m in BIG3_MAIN + BIG3_VARIATIONS):
                rpe_str = f"@RPE {w['rpe']}" if w['rpe'] else ""
                colored_date = color_date(w['date'])
                print(f"{name:40} 1RM: {w['weight']:6.1f}kg {rpe_str:12} ({colored_date})")
    
    # Generate markdown report
    if not args.no_markdown:
        markdown_path = os.path.join(args.markdown_dir, 'history.md')
        generate_markdown_report(workouts, all_maxes, stats, markdown_path)
        print(f"\n✅ Markdown report saved to: {markdown_path}")


if __name__ == '__main__':
    main()
