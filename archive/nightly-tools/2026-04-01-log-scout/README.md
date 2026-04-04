# log-scout

A tiny, zero-dependency Python CLI for fast morning triage of scattered logs.

## What it does

log-scout recursively scans a directory for `.log`, `.txt`, `.out`, and `.err` files, extracts lines that smell like warnings or errors, groups similar messages by normalizing variable content (timestamps, IPs, UUIDs, numbers, paths), and prints a concise summary:

- **Files scanned** & **issue count**
- **Top hot spots** — grouped by severity and frequency
- **Recent examples** — the freshest hits first

## Why it helps

Instead of `grep -r ERROR` across dozens of files and drowning in near-duplicate lines, log-scout surfaces patterns and tells you where the fire is hottest, in about a second.

## Usage

```bash
python3 log-scout.py path/to/logs
```

## How to test

A sample log directory is included. Run:

```bash
python3 log-scout.py sample-logs/
```

You should see a grouped summary with WARN and ERROR lines from the sample files.

## Design choices

- **No external dependencies** — works on any box with Python 3
- **Safe recursion** — skips binary files and stops at a sensible line limit per file
- **Heuristic normalization** — UUIDs, IPs, paths, datetimes, and numbers are replaced so "Connection failed for user 123" and "Connection failed for user 456" group together
- **Recency-aware sorting** — recent issues bubble to the top
- **Exits nonzero only on real errors** (missing directory, unreadable files, etc.)
