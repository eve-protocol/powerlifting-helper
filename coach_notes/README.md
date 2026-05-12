# Coach Notes

Session-close reflections written by Coach Jimin after each `done today` / `done YYYY-MM-DD` workflow. Weekly block assessments live in `coach_notes/weekly/`.

Purpose:
- preserve coaching observations that are not captured by raw set data
- track recurring technical themes across sessions
- make future daily assessments compare against recent coaching context
- preserve weekly block trajectory checks against Week 4 objectives

Required closeout workflow:
1. After Boostcamp history is refreshed and local outputs are pulled, read recent coach notes before writing today's note.
2. Default lookback: the last 7 calendar days of notes.
3. Also read the latest weekly assessment in `coach_notes/weekly/` when one exists, especially the previous completed week of the active block.
4. If the relevant pattern is older than 7 days, extend lookback to the last comparable sessions/lifts.
5. Append/create one note for the completed date before marking the state complete.
6. Commit the coach note together with the state update when closing the session.

Weekly assessment workflow:
1. Generate/update the weekly assessment during the `done today` / `done YYYY-MM-DD` handler when the completed workout closes a program week.
2. Detect week close from program state, not calendar weekday: after marking done, compare the just-completed workout's day number with the maximum `day` for that same `week` in the active block YAML.
3. Review `outputs/history_clean.md`, relevant daily coach notes, the active program YAML, and `state/coaching_focus.yaml`.
4. Write one concise file under `coach_notes/weekly/` named `<block>_week_<n>.md`.
5. Assess whether the block is on track for Week 4 objectives, including load trajectory, technical trajectory, recovery/RPE discipline, risks, and next-week coaching directives.
6. Future daily assessments and `done today` closeouts should read the latest weekly assessment and reflect whether the new session confirms or changes that trajectory.

Keep notes concise, actionable, and specific. Do not duplicate the entire generated history.
