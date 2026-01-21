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

from powerlifting import (
    # Constants
    BIG3_MAIN,
    BIG3_VARIATIONS,
    # API
    get_access_token,
    fetch_history,
    load_history,
    # Parser
    parse_all_workouts,
    find_all_rep_maxes,
    get_summary_stats,
    # Output
    print_summary,
    print_color_legend,
    print_e1rm_summary,
    print_trends,
    print_volume_summary,
    print_personal_rpe_table,
    print_rep_maxes,
    generate_markdown_report,
    # Visualization
    color_date,
)


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
    print_personal_rpe_table(workouts)
    
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
