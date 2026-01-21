"""Constants and configuration for powerlifting analysis."""

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

# RTS RPE Chart - percentage of 1RM for given reps and RPE
# Source: Reactive Training Systems
# Format: {reps: {rpe: percentage_of_1rm}}
RTS_RPE_CHART = {
    1:  {10: 1.000, 9.5: 0.978, 9: 0.955, 8.5: 0.939, 8: 0.922, 7.5: 0.906, 7: 0.889, 6.5: 0.873, 6: 0.856},
    2:  {10: 0.955, 9.5: 0.939, 9: 0.922, 8.5: 0.906, 8: 0.889, 7.5: 0.873, 7: 0.856, 6.5: 0.840, 6: 0.823},
    3:  {10: 0.922, 9.5: 0.906, 9: 0.889, 8.5: 0.873, 8: 0.856, 7.5: 0.840, 7: 0.823, 6.5: 0.807, 6: 0.790},
    4:  {10: 0.889, 9.5: 0.873, 9: 0.856, 8.5: 0.840, 8: 0.823, 7.5: 0.807, 7: 0.790, 6.5: 0.774, 6: 0.757},
    5:  {10: 0.856, 9.5: 0.840, 9: 0.823, 8.5: 0.807, 8: 0.790, 7.5: 0.774, 7: 0.757, 6.5: 0.741, 6: 0.724},
    6:  {10: 0.823, 9.5: 0.807, 9: 0.790, 8.5: 0.774, 8: 0.757, 7.5: 0.741, 7: 0.724, 6.5: 0.708, 6: 0.691},
    7:  {10: 0.790, 9.5: 0.774, 9: 0.757, 8.5: 0.741, 8: 0.724, 7.5: 0.708, 7: 0.691, 6.5: 0.675, 6: 0.658},
    8:  {10: 0.757, 9.5: 0.741, 9: 0.724, 8.5: 0.708, 8: 0.691, 7.5: 0.675, 7: 0.658, 6.5: 0.642, 6: 0.625},
    9:  {10: 0.724, 9.5: 0.708, 9: 0.691, 8.5: 0.675, 8: 0.658, 7.5: 0.642, 7: 0.625, 6.5: 0.609, 6: 0.592},
    10: {10: 0.691, 9.5: 0.675, 9: 0.658, 8.5: 0.642, 8: 0.625, 7.5: 0.609, 7: 0.592, 6.5: 0.576, 6: 0.559},
    11: {10: 0.658, 9.5: 0.642, 9: 0.625, 8.5: 0.609, 8: 0.592, 7.5: 0.576, 7: 0.559, 6.5: 0.543, 6: 0.526},
    12: {10: 0.625, 9.5: 0.609, 9: 0.592, 8.5: 0.576, 8: 0.559, 7.5: 0.543, 7: 0.526, 6.5: 0.510, 6: 0.493},
}

# ANSI color codes for terminal output
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
