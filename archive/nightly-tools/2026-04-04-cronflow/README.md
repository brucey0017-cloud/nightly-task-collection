# CronFlow

A zero-dependency Python CLI to make cron schedules visible at a glance.

It focuses on **user-accessible cron sources** (no sudo required), computes a simple next-run estimate, and flags **same-minute overlaps**.

## Why CronFlow?
Cron jobs are often "set and forget" until something breaks.
CronFlow gives a quick morning snapshot:
- what is scheduled,
- what runs next,
- and where obvious overlaps exist.

## Quickstart
```bash
python3 cronflow.py --demo
```

Real scan:
```bash
python3 cronflow.py
```

## What it scans (live mode)
- `crontab -l` output (current user)
- `~/.crontab` (if present)
- `/var/spool/cron/$USER` (only when readable)

Unreadable or missing sources are skipped gracefully.

## Features
- No third-party dependencies (Python stdlib only)
- Supports common 5-field cron format
- Supports macro entries: `@hourly`, `@daily`, `@weekly`, `@monthly`, `@yearly`, `@annually`, `@midnight`
- Marks commented-out jobs as disabled when parsable
- Buckets next runs into: `Next Hour`, `Today`, `This Week`, `Later`
- Conflict detection: jobs sharing the same next-run minute

## CLI options
- `--demo`: run with embedded sample jobs
- `--test`: alias of `--demo`
- `--limit N`: max printed rows (default 40)

## Example commands
```bash
# Friendly preview output
python3 cronflow.py --demo

# Check your current cron visibility
python3 cronflow.py

# Show only first 10 rows
python3 cronflow.py --limit 10
```

## Notes
- This tool is intentionally MVP and conservative.
- It does **not** modify cron jobs.
- Next-run estimation is best-effort for common schedules.
