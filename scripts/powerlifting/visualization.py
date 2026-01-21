"""ASCII visualization and date formatting functions."""

from datetime import datetime

from .constants import COLORS, AGE_INDICATORS


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


def markdown_date_staleness(date_str, reference_date=None):
    """Return emoji indicator for date staleness (for markdown output).
    
    Args:
        date_str: Date in YYYY-MM-DD format
        reference_date: Reference date for comparison (default: today)
    
    Returns:
        String with emoji prefix and date (e.g., '🟢 2026-01-15')
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    try:
        pr_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return date_str
    
    days_old = (reference_date - pr_date).days
    
    if days_old < 90:  # < 3 months
        emoji = AGE_INDICATORS['fresh']
    elif days_old < 180:  # 3-6 months
        emoji = AGE_INDICATORS['recent']
    elif days_old < 270:  # 6-9 months
        emoji = AGE_INDICATORS['aging']
    elif days_old < 365:  # 9-12 months
        emoji = AGE_INDICATORS['old']
    else:  # > 1 year
        emoji = AGE_INDICATORS['stale']
    
    return f"{emoji} {date_str}"


def generate_ascii_line_graph(data_series, labels, height=8, width=50):
    """Generate an ASCII line graph for trend data (points only).
    
    Args:
        data_series: Dict of {label: list_of_values} for each line
        labels: List of x-axis labels (weeks)
        height: Number of rows for the graph
        width: Approximate width of the graph
        
    Returns:
        List of strings representing the graph lines
    """
    if not data_series or not labels:
        return ["No data available"]
    
    # Get all values to determine scale
    all_values = []
    for values in data_series.values():
        all_values.extend([v for v in values if v > 0])
    
    if not all_values:
        return ["No data available"]
    
    min_val = min(all_values)
    max_val = max(all_values)
    
    # Add some padding
    val_range = max_val - min_val if max_val != min_val else 1
    min_val = max(0, min_val - val_range * 0.1)
    max_val = max_val + val_range * 0.1
    
    # Create the graph
    lines = []
    
    # Define symbols for each series
    symbols = {'Squat': '●', 'Bench': '■', 'Deadlift': '▲'}
    
    # Create grid
    n_cols = len(labels)
    col_width = max(width // n_cols, 4)
    
    for row in range(height, -1, -1):
        # Y-axis label
        if row == height:
            y_label = f"{max_val:6.0f} ┤"
        elif row == 0:
            y_label = f"{min_val:6.0f} ┼"
        elif row == height // 2:
            mid_val = (min_val + max_val) / 2
            y_label = f"{mid_val:6.0f} ┤"
        else:
            y_label = "       │"
        
        row_chars = []
        for col_idx in range(n_cols):
            cell_char = " "
            for series_name, values in data_series.items():
                if col_idx < len(values) and values[col_idx] > 0:
                    val = values[col_idx]
                    # Map value to row
                    val_row = int((val - min_val) / (max_val - min_val) * height)
                    if val_row == row:
                        cell_char = symbols.get(series_name, '•')
            row_chars.append(cell_char.center(col_width))
        
        lines.append(y_label + "".join(row_chars))
    
    # X-axis
    x_axis = "       └" + "─" * (col_width * n_cols)
    lines.append(x_axis)
    
    # X-axis labels (abbreviated)
    x_labels = "        "
    for label in labels:
        # Extract just the week number (e.g., "W03" from "2026-W03")
        short_label = label.split('-')[-1] if '-' in label else label
        x_labels += short_label.center(col_width)
    lines.append(x_labels)
    
    # Legend
    legend = "       "
    for name, symbol in symbols.items():
        if name in data_series:
            legend += f" {symbol} {name} "
    lines.append(legend)
    
    return lines


def generate_ascii_bar_chart(data, title="", max_width=40):
    """Generate an ASCII horizontal bar chart.
    
    Args:
        data: Dict of {label: value}
        title: Optional title for the chart
        max_width: Maximum width of the bars
        
    Returns:
        List of strings representing the chart
    """
    if not data:
        return ["No data available"]
    
    lines = []
    if title:
        lines.append(title)
    
    max_val = max(data.values()) if data.values() else 1
    max_label_len = max(len(str(k)) for k in data.keys())
    
    for label, value in data.items():
        bar_len = int((value / max_val) * max_width) if max_val > 0 else 0
        bar = "█" * bar_len
        lines.append(f"{label:>{max_label_len}} │{bar} {value:.0f}")
    
    return lines


def generate_volume_bar_chart(squat_vol, bench_vol, deadlift_vol, weeks, max_width=30):
    """Generate grouped ASCII bar charts for volume data.
    
    Args:
        squat_vol, bench_vol, deadlift_vol: Volume dicts by week
        weeks: List of weeks to display
        max_width: Maximum bar width
        
    Returns:
        List of strings representing the chart
    """
    lines = []
    
    # Find max for scaling
    max_val = 0
    for week in weeks:
        max_val = max(max_val, 
                      squat_vol.get(week, {}).get('total_kg', 0),
                      bench_vol.get(week, {}).get('total_kg', 0),
                      deadlift_vol.get(week, {}).get('total_kg', 0))
    
    if max_val == 0:
        return ["No volume data available"]
    
    for week in weeks:
        sq = squat_vol.get(week, {}).get('total_kg', 0)
        bn = bench_vol.get(week, {}).get('total_kg', 0)
        dl = deadlift_vol.get(week, {}).get('total_kg', 0)
        
        # Week label
        short_week = week.split('-')[-1] if '-' in week else week
        lines.append(f"\n{short_week}:")
        
        # Bars
        sq_bar = "█" * int((sq / max_val) * max_width)
        bn_bar = "▓" * int((bn / max_val) * max_width)
        dl_bar = "░" * int((dl / max_val) * max_width)
        
        lines.append(f"  Squat    │{sq_bar} {sq:.0f}kg")
        lines.append(f"  Bench    │{bn_bar} {bn:.0f}kg")
        lines.append(f"  Deadlift │{dl_bar} {dl:.0f}kg")
    
    # Legend
    lines.append("\n  █ Squat  ▓ Bench  ░ Deadlift")
    
    return lines
