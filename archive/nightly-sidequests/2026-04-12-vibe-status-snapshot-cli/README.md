# status-snapshot-cli

Tiny zero-dependency helper for nightly-lab workflow visibility.

## What it does
- Reads `current-run.json` to locate `status.jsonl`
- Aggregates latest stage per agent
- Shows event count, error count, and artifact path
- Optional JSON output for automation

## Usage
```bash
python3 status_snapshot.py --task sidequest
python3 status_snapshot.py --json
python3 status_snapshot.py --status-file /path/to/status.jsonl
```

## Example
```bash
python3 status_snapshot.py --task sidequest
```

This sidequest is intentionally small and self-contained for same-night completion.
