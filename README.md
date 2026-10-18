# powerlifting-helper

Tools for fetching, normalizing, and rendering training data from Boostcamp plus health backfill sources.

## Project layout

- `scripts/history_cli/` - history fetch, parsing, and markdown outputs
- `scripts/program_cli/` - YAML program validation, diffing, docs, and Boostcamp sync
- `scripts/health_cli/` - Health Connect ingestion and normalization
- `scripts/importers_cli/` - manual one-off importers for Garmin and Zepp exports
- `scripts/state_cli/` - local training-state utilities
- `scripts/common/` - shared helpers
- `scripts/powerlifting/` - reusable parsing and API library code
- `scripts/*.py` - compatibility wrappers that keep old commands working

## Main entrypoints

### History pipeline

- `python scripts/parse_history.py --fetch`
- `python scripts/generate_12_weeks.py`
- `python scripts/generate_rpe_table.py`
- `python scripts/export_clean_history.py`
- `python scripts/render_body_weight_timeline.py`

### Program pipeline

- `python scripts/validate_programs.py`
- `python scripts/show_changes.py`
- `python scripts/generate_program_docs.py`
- `python scripts/sync_programs.py`

Program sets may include local coaching percentages and kg anchors:

```yaml
- target: 3
  rpe: [6, 6.5]
  load_percent: [81, 83.5]
  load_percent_of: squat input (180kg)
  target_weight_range_kg: [145, 150]
  target_weight_kg: 147.5
- target: 3
  rpe: [6, 7.5]
  load_percent: 90
  load_percent_of: actual top triple
  target_weight_kg: 132.5
```

`load_percent` accepts a positive number or an ordered `[min, max]` in percentage
points (e.g. `81`, not `0.81`). A nonempty `load_percent_of` explicitly identifies
the reference: a competition-lift planning input is different from the actual
chosen top set. `target_weight_range_kg` is an optional positive ordered range;
an accompanying `target_weight_kg` must lie inside it and is rendered as a
**suggested start**, not a compulsory load. Single-anchor programs retain their
existing display.

The example top set renders as:

`3 reps @ RPE 6-6.5 · 81–83.5% of squat input (180kg) · 145–150kg anchor range (147.5kg suggested start)`

Backoffs show `90% of actual top triple`; their printed kg anchors are midpoint
examples, so recalculate them after the day's top set and round to the available
plates. RPE, legal positions, and symptoms govern the daily choice; the range's
upper endpoint is not a target to chase. Other variation percentages can be
**indicative ratios** of kg anchors to a competition-lift input, not measured
variation 1RMs. Do not invent percentages for machines, dumbbells, pull-ups, or
unselected meet attempts without a defensible reference.

All of these fields are validated and rendered locally in program documentation.
The Boostcamp converter intentionally ignores them and still sends the original
reps/RPE prescriptions; this does not add unsupported API intensity fields or
change exercise names. No Boostcamp write is needed to preview the display.

Run the local regression tests with `python -m unittest discover -s tests -v`.

### Health ingestion

- `python scripts/fetch_health_connect.py ...`
- `python scripts/export_health_daily.py ...`

### Manual importers

These are not part of the default CI flows, but they are still useful:

- `python scripts/export_garmin_daily.py ...`
- `python scripts/export_zepp_body_weight.py ...`

## Output

Data files are saved under `values/`:

- `values/history.json` - normalized Boostcamp workout history
- `values/health_daily.json` - normalized Health Connect daily metrics
- `values/body_weight_history.json` - historical Zepp/Xiaomi bodyweight backfill
- `values/garmin_daily.json` - historical Garmin daily wellness and sleep backfill

Rendered markdown outputs are saved under `outputs/`:

- `outputs/history.md`
- `outputs/history_clean.md`
- `outputs/12_last_weeks_history.md`
- `outputs/rpe_table.md`
- `outputs/body_weight_timeline.md`
- `outputs/scorecard_weekly.md`
- `outputs/scorecard_monthly.md`
- `outputs/scorecard_quarterly.md`
- `outputs/scorecard_yearly.md`
- `outputs/<program_name>.md`

## Notes

- `values/history.json` is written deterministically now, so volatile API fields like request IDs do not cause pointless diffs.
- `outputs/12_last_weeks_history.md` is anchored to the latest workout date in `history.json`, not wall-clock today, so it stays stable when no new training data arrives.
- Existing top-level `scripts/*.py` commands are preserved as wrappers for compatibility.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Get your Boostcamp refresh token from browser DevTools
3. Save it to `scripts/.boostcamp_refresh_token`
4. If you want CI Health Connect ingestion, add these GitHub secrets:
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `HEALTH_CONNECT_DRIVE_FILE_ID`
   - `PRIVATE_DATA_REPO`
   - `PRIVATE_DATA_REPO_TOKEN`
