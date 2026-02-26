# Training State

`training_state.yaml` drives daily assessment generation.

## Explicit progression (current mode)
State advances **only** when you explicitly mark a session done:

```bash
python scripts/update_training_state.py --mark-done --date YYYY-MM-DD
```

If the completed session is the last workout of the block, state auto-advances to the next block in `block_sequence` and resets completed workouts to 0.

## Daily assessment automation
Workflow: `.github/workflows/daily-assessment.yml`
- Runs every day at **08:30 JST**
- Generates `outputs/daily_assessment.md`
- Supports manual run (`workflow_dispatch`)
- Optional manual run input: `mark_done=true` to advance state before generating assessment
