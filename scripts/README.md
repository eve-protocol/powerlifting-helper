# Scripts layout

This directory now separates implementation by concern while keeping the old top-level entrypoints as compatibility wrappers.

## Layout

- `history_cli/` - workout-history fetch, parsing, and rendered outputs
- `program_cli/` - YAML program validation, docs, diffing, and Boostcamp sync
- `health_cli/` - Health Connect ingestion and normalization
- `importers_cli/` - manual one-off importers for Garmin/Zepp exports
- `state_cli/` - local training-state utilities
- `common/` - shared helpers used across multiple scripts
- `powerlifting/` - reusable Boostcamp/history parsing library code

## Compatibility

Existing commands like `python scripts/parse_history.py` still work.
The top-level files are thin wrappers so CI and local habits do not break while the implementation lives in grouped modules.
