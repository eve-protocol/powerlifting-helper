#!/usr/bin/env python3
"""Generate markdown docs in /outputs from YAML programs in /programs."""

from collections import defaultdict
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

    lines.append("## Program Structure")
    lines.append("")

    # Big 3 identification
    big3_patterns = {
        "Squat": ["Squat"],
        "Bench": ["Bench Press", "Larsen", "Spoto"],
        "Deadlift": ["Deadlift"],
    }

    def is_big3(ex_name: str) -> str | None:
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
            lines.append("| # | Exercise | Prescription |")
            lines.append("|---|----------|--------------|")
            for idx, ex in enumerate(workout.get("exercises", []), start=1):
                ex_name = ex.get("name", "Unknown")
                prescription = summarize_sets(ex.get("sets", []))
                lines.append(f"| {idx} | {ex_name} | {prescription} |")

                # Count big 3 sets/reps
                lift = is_big3(ex_name)
                if lift:
                    ex_sets = ex.get("sets", [])
                    week_big3[lift]["sets"] += len(ex_sets)
                    week_big3[lift]["reps"] += sum(
                        s.get("target", 0) for s in ex_sets
                    )
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
