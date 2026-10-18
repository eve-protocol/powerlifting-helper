#!/usr/bin/env python3
"""Generate markdown docs in /outputs from YAML programs in /programs."""

from collections import defaultdict
from itertools import groupby
import re

from powerlifting.programs import (
    OUTPUTS_DIR,
    PROGRAMS_DIR,
    format_program_set,
    iter_program_files,
    load_program_file,
)


def to_snake_case(name: str) -> str:
    s = re.sub(r"[^\w\s]", "", name)
    s = re.sub(r"\s+", "_", s).lower()
    return s


def summarize_sets(sets: list[dict]) -> str:
    if not sets:
        return "-"
    return "; ".join(format_program_set(s) for s in sets)


def display_value(value) -> str:
    """Format an optional number or range for a compact table cell."""
    if value is None:
        return "—"
    if isinstance(value, (list, tuple)):
        return "–".join(display_value(item) for item in value)
    if isinstance(value, (int, float)):
        return f"{value:g}"
    return str(value)


def set_columns(prescription: dict) -> list[str]:
    """Keep percentages, their basis and kg guidance in separate columns."""
    percentage = prescription.get("load_percent")
    reference = prescription.get("load_percent_of") if percentage is not None else None
    weight_range = prescription.get("target_weight_range_kg")
    anchor = display_value(prescription.get("target_weight_kg"))
    if prescription.get("target_weight_kg") is not None:
        if weight_range is not None:
            anchor += " (start)"
        elif reference == "actual top triple":
            anchor += " (example)"
    return [
        display_value(prescription.get("target")),
        display_value(prescription.get("rpe")),
        display_value(percentage) + "%" if percentage is not None else "—",
        display_value(reference),
        display_value(weight_range),
        anchor,
    ]


def grouped_sets(sets: list[dict]):
    """Group consecutive equal prescriptions, retaining their original set numbers."""
    for prescription, group in groupby(enumerate(sets, start=1), key=lambda item: item[1]):
        indices = [index for index, _ in group]
        label = str(indices[0]) if len(indices) == 1 else f"{indices[0]}–{indices[-1]}"
        yield label, prescription


def escape_table_cell(value: str) -> str:
    """Prevent source text from adding table columns or breaking table rows."""
    return value.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def workout_table_columns(workout: dict) -> list[int]:
    """Hide optional columns that are empty for the entire workout."""
    sets = [s for exercise in workout.get("exercises", []) for s in exercise.get("sets", [])]
    columns = [0, 1, 2, 3]
    if any(s.get("load_percent") is not None for s in sets):
        columns.extend([4, 5])
    if any(s.get("target_weight_range_kg") is not None for s in sets):
        columns.append(6)
    if any(s.get("target_weight_kg") is not None for s in sets):
        columns.append(7)
    return columns


def render_program(program: dict) -> str:
    name = program.get("name", "Unknown Program")
    description = program.get("description", "")
    weeks = program.get("weeks", 0)
    days_per_week = program.get("days_per_week", 0)
    workouts = program.get("workouts", [])

    grouped = defaultdict(list)
    for workout in workouts:
        grouped[workout.get("week")].append(workout)

    lines = []
    lines.append(f"# {name}")
    lines.append("")
    if description:
        lines.append(description)
        lines.append("")

    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Weeks: {weeks}")
    lines.append(f"- Days per week: {days_per_week}")
    lines.append(f"- Total workouts: {len(workouts)}")
    lines.append("")
    lines.append(
        "**Table guide:** Sets are the original set numbers; identical consecutive sets "
        "share a row (e.g. 2–4). Reps are per set. Range kg is the daily selection band; "
        "(start) marks a suggested starting anchor, and (example) marks a backoff anchor "
        "to recalculate from the actual top triple. — means no value is prescribed."
    )
    lines.append("")

    guidance = program.get("loading_guidance", {})
    display_rules = [guidance[key] for key in ("anchor_range_rule", "percentage_display_rule")
                     if guidance.get(key)]
    if display_rules:
        lines.append("## Load selection")
        lines.append("")
        for rule in display_rules:
            lines.append(rule)
            lines.append("")

    lines.append("## Program Structure")
    lines.append("")

    # Big 3 identification
    big3_patterns = {
        "Squat": ["Squat"],
        "Bench": ["Bench Press", "Larsen", "Spoto"],
        "Deadlift": ["Deadlift"],
    }

    def is_big3(ex_name: str, role: str | None = None) -> str | None:
        if role == "accessory":
            return None
        for lift, patterns in big3_patterns.items():
            if any(p in ex_name for p in patterns):
                return lift
        return None

    for week in sorted(grouped.keys()):
        lines.append(f"### Week {week}")
        lines.append("")

        # Track big 3 volume for this week
        week_big3: dict[str, dict] = {
            "Squat": {"sets": 0, "reps": 0},
            "Bench": {"sets": 0, "reps": 0},
            "Deadlift": {"sets": 0, "reps": 0},
        }

        for workout in sorted(grouped[week], key=lambda w: w.get("day", 0)):
            day = workout.get("day", "?")
            wname = workout.get("name", f"Day {day}")
            lines.append(f"#### Day {day} — {wname}")
            lines.append("")
            workout_intent = workout.get("intent")
            if workout_intent:
                lines.append(f"**Day intent:** {workout_intent}")
                lines.append("")
            priority = workout.get("priority")
            if priority and priority != "required":
                lines.append(f"**Priority:** {priority}")
                lines.append("")
            headings = ["Exercise", "Sets", "Reps", "RPE", "Load %", "% reference", "Range kg", "Anchor kg"]
            columns = workout_table_columns(workout)
            lines.append("| " + " | ".join(headings[index] for index in columns) + " |")
            lines.append("|" + "|".join("---" for _ in columns) + "|")
            exercise_intents = []
            for ex in workout.get("exercises", []):
                ex_name = ex.get("name", "Unknown")
                for set_label, prescription in grouped_sets(ex.get("sets", [])):
                    cells = [ex_name, set_label, *set_columns(prescription)]
                    lines.append("| " + " | ".join(escape_table_cell(cells[index]) for index in columns) + " |")
                if ex.get("intent"):
                    exercise_intents.append((ex_name, ex["intent"]))

                # Count big 3 sets/reps
                lift = is_big3(ex_name, ex.get("role"))
                if lift:
                    ex_sets = ex.get("sets", [])
                    week_big3[lift]["sets"] += len(ex_sets)
                    week_big3[lift]["reps"] += sum(
                        s.get("target", 0) for s in ex_sets
                    )
            lines.append("")
            if exercise_intents:
                lines.append("**Why these movements:**")
                lines.append("")
                for ex_name, intent in exercise_intents:
                    lines.append(f"- **{ex_name}:** {intent}")
                lines.append("")

        # Big 3 weekly summary
        lines.append("#### Weekly Big 3 Volume")
        lines.append("")
        lines.append("| Lift | Sets | Reps |")
        lines.append("|------|------|------|")
        for lift in ["Squat", "Bench", "Deadlift"]:
            s = week_big3[lift]["sets"]
            r = week_big3[lift]["reps"]
            lines.append(f"| {lift} | {s} | {r} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    if not PROGRAMS_DIR.exists():
        print("No programs directory found")
        return 1

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    yaml_files = iter_program_files(PROGRAMS_DIR)
    if not yaml_files:
        print("No YAML programs found")
        return 0

    for yaml_file in yaml_files:
        program = load_program_file(yaml_file)

        output_name = f"{to_snake_case(program.get('name', yaml_file.stem))}.md"
        output_path = OUTPUTS_DIR / output_name
        output_path.write_text(render_program(program), encoding="utf-8")
        print(f"Generated {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
