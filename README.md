# powerlifting-helper

Tools for fetching and analyzing workout data from Boostcamp.

## Scripts

- **`scripts/fetch_programs.py`** - Fetches training program details from Boostcamp API
- **`scripts/parse_history.py`** - Parses workout history and displays all-time PRs for Big 3 lifts

## Output

Data files are saved to the `values/` directory at the project root:

- `values/history.json` - Workout history
- `values/health_daily.json` - Normalized daily Health Connect metrics (Garmin-first), generated transiently in CI and not committed
- `values/body_weight_history.json` - Long-range bodyweight history extracted from Zepp/Xiaomi scale export when configured
- `values/<program_name>.json` - Program details (e.g., `strength_block_v3.json`)

Rendered markdown outputs are saved to `outputs/`, including:

- `outputs/history_clean.md`
- `outputs/12_last_weeks_history.md`
- `outputs/scorecard_weekly.md`
- `outputs/scorecard_monthly.md`
- `outputs/scorecard_quarterly.md`
- `outputs/scorecard_yearly.md`

### Custom Output Directory

Use `--output-dir` / `-o` to specify a different location:

```bash
python scripts/fetch_programs.py --output-dir ./my-data/
python scripts/parse_history.py -o /tmp/workout-data/
```

## Setup

1. Install dependencies: `pip install requests google-auth`
2. Get your Boostcamp refresh token from browser DevTools
3. Save it to `scripts/.boostcamp_refresh_token`
4. If you want CI Health Connect ingestion, add these GitHub secrets:
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `HEALTH_CONNECT_DRIVE_FILE_ID`
   - Optional for legacy Zepp/Xiaomi scale history:
     - `ZEPP_BODY_DRIVE_FILE_ID`
     - `ZEPP_BODY_ZIP_PASSWORD`
5. Run the scripts
