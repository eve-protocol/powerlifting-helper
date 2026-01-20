# powerlifting-helper

Tools for fetching and analyzing workout data from Boostcamp.

## Scripts

- **`scripts/fetch_programs.py`** - Fetches training program details from Boostcamp API
- **`scripts/parse_history.py`** - Parses workout history and displays all-time PRs for Big 3 lifts

## Output

Data files are saved to the `values/` directory at the project root:

- `values/history.json` - Workout history
- `values/<program_name>.json` - Program details (e.g., `strength_block_v3.json`)

### Custom Output Directory

Use `--output-dir` / `-o` to specify a different location:

```bash
python scripts/fetch_programs.py --output-dir ./my-data/
python scripts/parse_history.py -o /tmp/workout-data/
```

## Setup

1. Install dependencies: `pip install requests`
2. Get your Boostcamp refresh token from browser DevTools
3. Save it to `scripts/.boostcamp_refresh_token`
4. Run the scripts
