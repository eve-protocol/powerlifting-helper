"""Expected SBD-family workload for opt-in, explicitly scoped program summaries."""

from decimal import Decimal, ROUND_HALF_UP

FAMILIES = ("Squat", "Bench", "Deadlift")


def empty_metrics():
    return {"sets": 0, "reps": 0, "tonnage_low": 0.0, "tonnage_high": 0.0,
            "unanchored_sets": 0}


def set_weight_bounds(prescription, top_bounds=None, plate_increment=2.5):
    """Resolve kg bands; dependent backoffs follow the chosen top-set endpoint."""
    if prescription.get("load_percent_of") == "actual top triple":
        if top_bounds is None:
            return None
        percent = prescription["load_percent"]
        percents = percent if isinstance(percent, list) else [percent, percent]
        increment = Decimal(str(plate_increment))
        return tuple(float((Decimal(str(weight)) * Decimal(str(pct)) / 100 / increment)
                           .quantize(Decimal("1"), rounding=ROUND_HALF_UP) * increment)
                     for weight, pct in zip(top_bounds, percents))
    if prescription.get("target_weight_range_kg") is not None:
        return tuple(prescription["target_weight_range_kg"])
    anchor = prescription.get("target_weight_kg")
    return (anchor, anchor) if anchor is not None else None


def calculate_weekly_workload(program):
    """Count original source sets, never grouped Markdown display rows."""
    config = program.get("workload_summary")
    if not config:
        return {}
    mapping = {name: family for family, names in config["families"].items() for name in names}
    exclusions = {(item["week"], item["day"]): item for item in config.get("exclude_workouts", [])}
    weeks = {workout["week"] for workout in program.get("workouts", [])}
    summary = {week: {"lifts": {family: empty_metrics() for family in FAMILIES},
                      "total": empty_metrics(), "excluded_workouts": []}
               for week in sorted(weeks)}
    for workout in program.get("workouts", []):
        exclusion = exclusions.get((workout["week"], workout["day"]))
        if exclusion is not None:
            sets = [s for exercise in workout.get("exercises", []) for s in exercise.get("sets", [])]
            summary[workout["week"]]["excluded_workouts"].append({
                "name": workout.get("name", "Workout"), "reason": exclusion["reason"],
                "sets": len(sets), "reps": sum(s["target"] for s in sets),
            })
            continue
        for exercise in workout.get("exercises", []):
            family = mapping.get(exercise["name"])
            if family is None:
                continue
            metrics = summary[workout["week"]]["lifts"][family]
            sets = exercise.get("sets", [])
            increment = config.get("plate_increment_kg", 2.5)
            top_bounds = set_weight_bounds(sets[0], plate_increment=increment) if sets else None
            for prescription in sets:
                metrics["sets"] += 1
                metrics["reps"] += prescription["target"]
                bounds = set_weight_bounds(prescription, top_bounds, increment)
                if bounds is None:
                    metrics["unanchored_sets"] += 1
                else:
                    metrics["tonnage_low"] += prescription["target"] * bounds[0]
                    metrics["tonnage_high"] += prescription["target"] * bounds[1]
    for row in summary.values():
        for metrics in row["lifts"].values():
            for key in row["total"]:
                row["total"][key] += metrics[key]
    return summary


def format_number(value):
    return f"{value:,.1f}".rstrip("0").rstrip(".")


def format_tonnage(metrics):
    low, high = metrics["tonnage_low"], metrics["tonnage_high"]
    amount = format_number(low) if low == high else f"{format_number(low)}–{format_number(high)}"
    missing = metrics["unanchored_sets"]
    if missing:
        label = f"{missing} set" + ("s" if missing != 1 else "")
        return (f"{amount} + unknown ({label})" if high else f"Unknown ({label})")
    return amount


def format_change(current, previous):
    """Conservative interval change: current low / previous high through the reverse."""
    if current is None or previous is None or previous[0] <= 0:
        return "—"
    low = (current[0] / previous[1] - 1) * 100
    high = (current[1] / previous[0] - 1) * 100

    def percent(value):
        value = round(value, 1)
        return "0.0%" if value == 0 else f"{value:+.1f}%"

    return percent(low) if round(low, 1) == round(high, 1) else f"{percent(low)} to {percent(high)}"


def tonnage_change(current, previous):
    if previous is None or current["unanchored_sets"] or previous["unanchored_sets"]:
        return "—"
    return format_change((current["tonnage_low"], current["tonnage_high"]),
                         (previous["tonnage_low"], previous["tonnage_high"]))


def metric_cells(current, previous):
    def count_change(key):
        return format_change((current[key], current[key]),
                             (previous[key], previous[key]) if previous is not None else None)
    return [str(current["sets"]), count_change("sets"), str(current["reps"]),
            count_change("reps"), format_tonnage(current), tonnage_change(current, previous)]


def week_label(week, row):
    return f"{week} (training only)" if row["excluded_workouts"] else str(week)


def render_workload_overview(program, summary):
    if not summary:
        return []
    config = program["workload_summary"]
    lines = ["### Weekly expected SBD workload", "",
             config.get("scope_note", "SBD total includes only the explicitly listed lift families; unmapped accessories are excluded."), ""]
    for family in FAMILIES:
        lines.append(f"- **{family}:** " + ", ".join(config["families"][family]))
    lines += ["", "Planning estimates, not completed tonnage. Tonnage = reps × load. "
              "Week 1 has no comparison; all Δ values compare with the immediately previous week. "
              "For load ranges, Δ spans current minimum / previous maximum through current maximum / previous minimum. "
              "Unknown loads are not silently counted as zero, and undefined comparisons show —.", "",
              "| Week | Expected SBD tonnage kg | Δ vs previous week |", "|---|---|---|"]
    for week, row in summary.items():
        previous = summary.get(week - 1)
        delta = tonnage_change(row["total"], previous["total"] if previous else None)
        lines.append(f"| {week_label(week, row)} | {format_tonnage(row['total'])} | {delta} |")
    lines.append("")
    for family in FAMILIES:
        lines += [f"#### {family} workload by week", "",
                  "| Week | Sets | Δ sets | Reps | Δ reps | Tonnage kg | Δ tonnage |",
                  "|---|---|---|---|---|---|---|"]
        for week, row in summary.items():
            previous = summary.get(week - 1)
            cells = [week_label(week, row), *metric_cells(row["lifts"][family],
                     previous["lifts"][family] if previous else None)]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    for week, row in summary.items():
        for excluded in row["excluded_workouts"]:
            lines += [f"**Excluded from training totals, week {week}:** {excluded['reason']} "
                      f"({excluded['sets']} sets / {excluded['reps']} reps).", ""]
    return lines
