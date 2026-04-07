# 🔪 Risk Drift Scanner

A zero-dependency Python 3 CLI tool that scans markdown documentation directories for **unvalidated decisions, hidden assumptions, and risk amplifiers**.

Built by KILLJOY (首席质疑官) — because decisions without validation are just wishes with confidence.

## What It Does

1. **Executive Summary** — Quantifies your decision/assumption/validation ratio and gives a verdict
2. **Unvalidated Kill List** — Ranks decisions and assumptions by risk score that have zero supporting evidence in the same file
3. **Risk Amplifiers** — Flags dangerous language patterns (absolutes, overconfidence, hidden complexity, complacency, TODOs)
4. **File Breakdown** — Per-file risk assessment with max risk score

## How It Scores Risk

| Signal | Score |
|--------|-------|
| Assumption keyword | +4 |
| Decision keyword | +2 |
| Absolute language (all, never) | +2 |
| Overconfidence (guaranteed, impossible) | +3 |
| Hidden complexity (simple, easy, just) | +2 |
| Complacency (safe, stable, no risk) | +3 |
| Incomplete (TODO, FIXME, TBD) | +2 |
| Time pressure (soon, ASAP) | +2 |
| Validation present | -3 |

Score capped at 0-10.

## Usage

```bash
# Scan a directory of .md files
python3 risk_drift.py /path/to/memory/

# Last N days only (requires date in filename like 2026-04-05.md)
python3 risk_drift.py /path/to/memory/ --since 14

# JSON output for programmatic use
python3 risk_drift.py /path/to/memory/ --json
```

## Test

```bash
python3 risk_drift.py sample-data/
```

Expected output: 2 files scanned, ~17 flagged items, validation desert verdict.

## Detection Patterns

- **Decisions**: "decided", "agreed", "will use", "chose", "selected", "approved", etc.
- **Assumptions**: "assume", "should", "probably", "expected", "roughly N", etc.
- **Validations**: "validated", "tested", "A/B test", "user research", "benchmark", etc.
- **Risk amplifiers**: absolutes, overconfidence, hidden complexity labels, complacency markers, TODO/FIXME items

## Why This Exists

Teams make dozens of decisions daily. Most are never written down. Of the ones that are, most are never validated. This tool reads your own documentation back to you with the risk highlighted — because the most dangerous assumptions are the ones you don't know you're making.

> "Every assumption is a bet. The question is whether you know you're placing it."
> — KILLJOY
