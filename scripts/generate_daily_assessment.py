#!/usr/bin/env python3
"""Generate daily coaching assessment from repo programs + history."""

from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
import statistics
import yaml
import json

STATE_PATH = Path("state/training_state.yaml")
HISTORY_JSON = Path("values/history.json")
OUTPUT_PATH = Path("outputs/daily_assessment.md")

LBS_TO_KG = 0.453592
MAIN_MARKERS = ["squat", "bench", "deadlift"]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def round_2p5(x: float) -> float:
    return round(x / 2.5) * 2.5


def load_state():
    return yaml.safe_load(STATE_PATH.read_text(encoding="utf-8"))


def load_program(block: str):
    path = Path("programs") / f"{block}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_history_sets():
    data = json.loads(HISTORY_JSON.read_text(encoding="utf-8"))
    out = defaultdict(list)
    for _, sessions in data.get("data", {}).items():
        for sess in sessions:
            for ex in sess.get("records", []):
                name = ex.get("name", "").strip().lower()
                for s in ex.get("sets", []):
                    if s.get("skipped"):
                        continue
                    reps = s.get("archived_reps", s.get("amount"))
                    weight_lb = s.get("archived_weight", 0) or 0
                    rpe = s.get("archived_rpe")
                    try:
                        reps = int(reps)
                    except Exception:
                        continue
                    if reps <= 0 or weight_lb <= 0:
                        continue
                    out[name].append(
                        {
                            "reps": reps,
                            "kg": round(weight_lb * LBS_TO_KG, 1),
                            "rpe": float(rpe) if rpe not in (None, "") else None,
                        }
                    )
    return out


def is_training_day(state, now):
    wd = WEEKDAYS[now.weekday()]
    return wd in state.get("training_days", [])


def next_training_day(state, now):
    days = set(state.get("training_days", []))
    for d in range(1, 8):
        cand = now + timedelta(days=d)
        if WEEKDAYS[cand.weekday()] in days:
            return cand
    return now


def get_next_workout(state, program):
    completed = int(state.get("completed_workouts_in_current_block", 0))
    idx = completed
    workouts = sorted(program.get("workouts", []), key=lambda w: (w.get("week", 0), w.get("day", 0)))
    idx = min(idx, max(0, len(workouts) - 1))
    return workouts[idx], idx + 1, len(workouts)


def exercise_weight_range(history_sets, ex_name, target_reps, target_rpe_mid):
    sets = history_sets.get(ex_name.strip().lower(), [])
    if not sets:
        return None

    candidates = [s for s in sets if abs(s["reps"] - target_reps) <= 1] or sets

    if target_rpe_mid is not None:
        near = [s for s in candidates if s["rpe"] is not None and abs(s["rpe"] - target_rpe_mid) <= 1.0]
        if near:
            candidates = near

    kgs = sorted(s["kg"] for s in candidates)
    if not kgs:
        return None

    p25 = kgs[max(0, int(len(kgs) * 0.25) - 1)]
    p75 = kgs[min(len(kgs) - 1, int(len(kgs) * 0.75))]
    low = round_2p5(p25)
    high = round_2p5(p75)
    if high < low:
        high = low
    return (low, high)


def is_main_lift(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in MAIN_MARKERS)


def render_workout(lines, workout, history_sets):
    for ex in workout.get("exercises", []):
        name = ex.get("name", "Unknown")
        sets = ex.get("sets", [])
        if not sets:
            continue

        target_reps = int(statistics.median([s.get("target", 0) for s in sets if s.get("target") is not None]))
        rpe_mid = []
        for s in sets:
            r = s.get("rpe")
            if isinstance(r, (list, tuple)) and len(r) == 2:
                rpe_mid.append((float(r[0]) + float(r[1])) / 2)
            elif isinstance(r, (int, float)):
                rpe_mid.append(float(r))
        target_rpe_mid = statistics.mean(rpe_mid) if rpe_mid else None

        wr = exercise_weight_range(history_sets, name, target_reps, target_rpe_mid)
        prescription = " / ".join([f"{s.get('target')} reps @ RPE {s.get('rpe', '-') }" for s in sets])

        kind = "Main Lift" if is_main_lift(name) else "Accessory"
        lines.append(f"### {name} ({kind})")
        lines.append(f"- Prescription: {prescription}")
        if wr:
            lines.append(f"- Suggested load range: **{wr[0]:.1f}–{wr[1]:.1f} kg**")
        else:
            lines.append("- Suggested load range: no direct history match; start conservative and autoregulate")

        lines.append("- If RPE too high: drop **2.5–5 kg** next set (main), **2.5 kg** (accessory)")
        lines.append("- If RPE too low: add **2.5–5 kg** next set (main), **2.5 kg** (accessory)")

        if is_main_lift(name):
            lines.append("- Bar speed cue (top set): forceful concentric, no grind before final rep")
            lines.append("- Bar speed cue (backoff): stable tempo and identical technique every rep")
        else:
            lines.append("- Accessory cue: controlled eccentric, full ROM, no momentum cheating")
        lines.append("")


def build_assessment(state, program, history_sets, now):
    workout, num, total = get_next_workout(state, program)
    block = state["current_block"]

    lines = []
    lines.append(f"# Daily Assessment — {now.strftime('%Y-%m-%d')} ({now.strftime('%A')})")
    lines.append("")
    lines.append(f"**Block:** {block}")
    lines.append(f"**Session:** Week {workout.get('week')} Day {workout.get('day')} ({num}/{total} workout-days in block)")
    lines.append("")

    if not is_training_day(state, now):
        nxt = next_training_day(state, now)
        lines.append("## Today")
        lines.append("")
        lines.append("Rest day. No loading prescribed today.")
        lines.append(f"Next training day: **{nxt.strftime('%Y-%m-%d (%A)')}**")
        lines.append("")
        lines.append("## Next Session Preview")
        lines.append("")
        render_workout(lines, workout, history_sets)
    else:
        lines.append("## Session Summary & Targets")
        lines.append("")
        render_workout(lines, workout, history_sets)

    lines.append("## Progression Rule")
    lines.append("")
    lines.append("State progression is **explicit** only. Mark session complete manually with:")
    lines.append("`python scripts/update_training_state.py --mark-done --date YYYY-MM-DD`")
    lines.append("")
    return "\n".join(lines)


def main():
    state = load_state()
    tz = ZoneInfo(state.get("timezone", "Asia/Tokyo"))
    now = datetime.now(tz)
    program = load_program(state["current_block"])
    history_sets = load_history_sets()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_assessment(state, program, history_sets, now), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
