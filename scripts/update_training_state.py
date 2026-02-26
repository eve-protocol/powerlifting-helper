#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import argparse
import yaml

STATE_PATH = Path("state/training_state.yaml")


def load_state():
    return yaml.safe_load(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state):
    STATE_PATH.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")


def next_block(state, current):
    seq = state["block_sequence"]
    idx = seq.index(current)
    return seq[(idx + 1) % len(seq)]


def workouts_in_block(block_name: str) -> int:
    path = Path("programs") / f"{block_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Program file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return len(data.get("workouts", []))


def main():
    parser = argparse.ArgumentParser(description="Update training state only on explicit instruction")
    parser.add_argument("--mark-done", action="store_true", help="Mark next scheduled workout as completed")
    parser.add_argument("--date", default=datetime.now().date().isoformat(), help="Completion date (YYYY-MM-DD)")
    args = parser.parse_args()

    if not args.mark_done:
        print("No action taken. Use --mark-done to progress state.")
        return 0

    state = load_state()
    block = state["current_block"]
    completed = int(state.get("completed_workouts_in_current_block", 0)) + 1
    total = workouts_in_block(block)

    if completed > total:
        # rollover
        block = next_block(state, block)
        completed = 1

    # if we just completed the block exactly, advance to next block with 0 completed
    if completed == total:
        state["current_block"] = next_block(state, block)
        state["completed_workouts_in_current_block"] = 0
    else:
        state["current_block"] = block
        state["completed_workouts_in_current_block"] = completed

    state["last_completed_date"] = args.date
    save_state(state)
    print(f"Updated state: block={state['current_block']} completed={state['completed_workouts_in_current_block']} date={state['last_completed_date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
