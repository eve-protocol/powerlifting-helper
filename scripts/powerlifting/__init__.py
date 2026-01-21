# Powerlifting Analysis Package
"""Powerlifting workout analysis tools for Boostcamp data."""

from .constants import (
    BOOSTCAMP_API_URL,
    BOOSTCAMP_PROGRAM_DETAIL_URL,
    BOOSTCAMP_PROGRAMS_LIST_URL,
    BOOSTCAMP_PROGRAMS_CONTINUE_URL,
    FIREBASE_API_KEY,
    DEFAULT_REFRESH_TOKEN_FILE,
    DEFAULT_CONFIG_FILE,
    BIG3_MAIN,
    BIG3_VARIATIONS,
    LIFT_CATEGORIES,
    RTS_RPE_CHART,
    COLORS,
    AGE_INDICATORS,
)
from .e1rm import (
    calculate_e1rm_brzycki,
    calculate_e1rm_rpe_adjusted,
    calculate_personal_rpe_table,
    get_best_recent_e1rm,
)
from .api import (
    refresh_access_token,
    get_access_token,
    fetch_history,
    load_history,
    fetch_program,
    fetch_user_programs,
    resolve_programs_by_name,
    load_config,
)
from .parser import (
    parse_all_workouts,
    find_all_rep_maxes,
    calculate_training_volume,
    analyze_trends,
    get_summary_stats,
)
from .visualization import (
    generate_ascii_line_graph,
    generate_ascii_bar_chart,
    generate_volume_bar_chart,
    color_date,
    markdown_date_staleness,
)
from .output import (
    print_summary,
    print_e1rm_summary,
    print_volume_summary,
    print_trends,
    print_rep_maxes,
    print_personal_rpe_table,
    print_color_legend,
    generate_markdown_report,
    generate_markdown_rpe_table,
)

__all__ = [
    # Constants
    'BOOSTCAMP_API_URL', 'BOOSTCAMP_PROGRAM_DETAIL_URL', 'BOOSTCAMP_PROGRAMS_LIST_URL',
    'BOOSTCAMP_PROGRAMS_CONTINUE_URL', 'FIREBASE_API_KEY', 'DEFAULT_REFRESH_TOKEN_FILE',
    'DEFAULT_CONFIG_FILE', 'BIG3_MAIN', 'BIG3_VARIATIONS', 'LIFT_CATEGORIES',
    'RTS_RPE_CHART', 'COLORS', 'AGE_INDICATORS',
    # e1RM
    'calculate_e1rm_brzycki', 'calculate_e1rm_rpe_adjusted',
    'calculate_personal_rpe_table', 'get_best_recent_e1rm',
    # API
    'refresh_access_token', 'get_access_token', 'fetch_history', 'load_history',
    'fetch_program', 'fetch_user_programs', 'resolve_programs_by_name', 'load_config',
    # Parser
    'parse_all_workouts', 'find_all_rep_maxes', 'calculate_training_volume',
    'analyze_trends', 'get_summary_stats',
    # Visualization
    'generate_ascii_line_graph', 'generate_ascii_bar_chart',
    'generate_volume_bar_chart', 'color_date', 'markdown_date_staleness',
    # Output
    'print_summary', 'print_e1rm_summary', 'print_volume_summary',
    'print_trends', 'print_rep_maxes', 'print_personal_rpe_table',
    'print_color_legend', 'generate_markdown_report', 'generate_markdown_rpe_table',
]
