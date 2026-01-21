"""Boostcamp API client for fetching workout history and programs."""

import json
import os
import time

try:
    import requests
except ImportError:
    requests = None  # Will error only if --fetch is used

from .constants import (
    BOOSTCAMP_API_URL,
    BOOSTCAMP_PROGRAM_DETAIL_URL,
    BOOSTCAMP_PROGRAMS_LIST_URL,
    BOOSTCAMP_PROGRAMS_CONTINUE_URL,
    FIREBASE_REFRESH_URL,
    DEFAULT_REFRESH_TOKEN_FILE,
)


def _get_headers(token):
    """Get standard headers for Boostcamp API requests."""
    return {
        'Authorization': f'FirebaseIdToken:{token}',
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': 'https://www.boostcamp.app',
        'Referer': 'https://www.boostcamp.app/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
    }


def _check_requests():
    """Check if requests library is available."""
    if requests is None:
        print("Error: 'requests' library is required.")
        print("Install with: pip install requests")
        return False
    return True


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
    if not _check_requests():
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
    if not _check_requests():
        return False
    
    headers = _get_headers(token)
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


def fetch_program(program_id, token):
    """Fetch a single program's details from the Boostcamp API.
    
    Args:
        program_id: ID of the program to fetch
        token: Firebase ID token
        
    Returns:
        dict: Program data from API
    """
    if not _check_requests():
        return None
    
    headers = _get_headers(token)
    payload = {'program_id': program_id}
    timestamp = int(time.time() * 1000)
    url = f"{BOOSTCAMP_PROGRAM_DETAIL_URL}?_={timestamp}"
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_user_programs(token):
    """Fetch list of all user's programs from Boostcamp API.
    
    Fetches from both:
    - /api/www/programs/user_programs/list (created programs)
    - /api/www/programs/continue/list (active programs you're using)
    
    Args:
        token: Firebase ID token
        
    Returns:
        list: List of program dicts with 'id' and 'title' keys
    """
    if not _check_requests():
        return []
    
    headers = _get_headers(token)
    all_programs = {}  # Use dict to dedupe by ID
    timestamp = int(time.time() * 1000)
    
    # Fetch created programs
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
        url = f"{BOOSTCAMP_PROGRAMS_CONTINUE_URL}?_={timestamp}"
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


def load_config(config_path):
    """Load boostcamp_conf.json configuration file."""
    with open(config_path, 'r') as f:
        return json.load(f)

