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

Program sets may include a local coaching anchor:

```yaml
- target: 5
  rpe: [7, 7.5]
  target_weight_kg: 150
```

`target_weight_kg` is validated and rendered in program documentation, but the
Boostcamp payload intentionally ignores it. Daily coaching can adjust the
anchor for current pain, equipment, technique, and observed RPE without
changing the programmed rep/RPE target.

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
