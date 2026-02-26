#!/usr/bin/env python3
"""Generate markdown docs in /outputs from YAML programs in /programs."""

from pathlib import Path
from collections import defaultdict
import yaml
import re

PROGRAMS_DIR = Path("programs")
OUTPUTS_DIR = Path("outputs")


def to_snake_case(name: str) -> str:
    s = re.sub(r"[^\w\s]", "", name)
    s = re.sub(r"\s+", "_", s).lower()
    return s


def format_set(set_data: dict) -> str:
    target = set_data.get("target", "-")
    rpe = set_data.get("rpe")
    if isinstance(rpe, (list, tuple)) and len(rpe) == 2:
        rpe_str = f"RPE {rpe[0]}-{rpe[1]}"
    elif rpe is not None:
        rpe_str = f"RPE {rpe}"
    else:
        rpe_str = "RPE -"
    return f"{target} reps @ {rpe_str}"


def summarize_sets(sets: list[dict]) -> str:
    if not sets:
        return "-"
    return "; ".join(format_set(s) for s in sets)


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

    for week in sorted(grouped.keys()):
        lines.append(f"### Week {week}")
        lines.append("")
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
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    if not PROGRAMS_DIR.exists():
        print("No programs directory found")
        return 1

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    yaml_files = sorted(list(PROGRAMS_DIR.glob("*.yaml")) + list(PROGRAMS_DIR.glob("*.yml")))
    if not yaml_files:
        print("No YAML programs found")
        return 0

    for yaml_file in yaml_files:
        with yaml_file.open("r", encoding="utf-8") as f:
            program = yaml.safe_load(f)

        output_name = f"{to_snake_case(program.get('name', yaml_file.stem))}.md"
        output_path = OUTPUTS_DIR / output_name
        output_path.write_text(render_program(program), encoding="utf-8")
        print(f"Generated {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
