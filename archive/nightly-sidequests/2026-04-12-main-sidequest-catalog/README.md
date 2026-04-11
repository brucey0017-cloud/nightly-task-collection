# sidequest-catalog

Zero-dependency Python 3 CLI that scans all nightly-sidequests directories, extracts metadata, and produces a unified index.

## Why this is useful
After 12 days of nightly builds, there are **47 sidequests** across 5 agents and no way to see them all at a glance. This tool gives Bruce instant visibility into what's been built, by whom, when, and whether it has docs/tests.

## What it does
- Scans `nightly-sidequests/YYYY-MM-DD-<agent>-<slug>/` directories
- Parses README.md or Python docstrings for descriptions
- Tracks files, README presence, test presence
- Outputs: markdown table, JSON, grouped by agent or date, summary statistics

## Usage
```bash
# Full catalog with stats
python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/ --stats

# JSON output for automation
python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/ --json

# Group by agent
python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/ --by agent

# Group by date
python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/ --by date

# Write to file
python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/ --output catalog.md --stats
```

## Test command
```bash
cd /root/.openclaw/workspace/nightly-sidequests/2026-04-12-main-sidequest-catalog
python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/ --stats | grep "Total sidequests"
# Expected: **Total sidequests:** 47 (or higher)
```

## Status
✅ Complete, tested, self-contained.
