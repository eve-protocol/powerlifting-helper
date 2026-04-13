"""Helpers for loading and iterating local YAML training programs."""

from pathlib import Path

import yaml

PROGRAMS_DIR = Path("programs")
OUTPUTS_DIR = Path("outputs")


def iter_program_files(programs_dir=PROGRAMS_DIR):
    """Return all YAML program files in stable order."""
    return sorted(list(programs_dir.glob("*.yaml")) + list(programs_dir.glob("*.yml")))


def load_program_file(path):
    """Load one YAML program file."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_programs_by_name(programs_dir=PROGRAMS_DIR):
    """Load all local programs keyed by program name."""
    programs = {}
    if not programs_dir.exists():
        return programs

    for yaml_file in iter_program_files(programs_dir):
        data = load_program_file(yaml_file)
        programs[data["name"]] = data
    return programs


def get_program_path(block_name: str, programs_dir=PROGRAMS_DIR) -> Path:
    """Resolve a block/program name to its YAML file path."""
    return programs_dir / f"{block_name}.yaml"


def format_program_set(set_data: dict) -> str:
    """Format a program prescription set for markdown output."""
    target = set_data.get("target", "-")
    rpe = set_data.get("rpe")
    if isinstance(rpe, (list, tuple)) and len(rpe) == 2:
        rpe_str = f"RPE {rpe[0]}-{rpe[1]}"
    elif rpe is not None:
        rpe_str = f"RPE {rpe}"
    else:
        rpe_str = "RPE -"
    return f"{target} reps @ {rpe_str}"
