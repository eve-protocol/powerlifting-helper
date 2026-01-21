"""Boostcamp API client for fetching workout history."""

import json
import os

try:
    import requests
except ImportError:
    requests = None  # Will error only if --fetch is used

from .constants import (
    BOOSTCAMP_API_URL,
    FIREBASE_REFRESH_URL,
    DEFAULT_REFRESH_TOKEN_FILE,
)


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
