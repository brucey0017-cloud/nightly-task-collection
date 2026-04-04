# Run Status Brief

A tiny zero-dependency Python tool that audits a `nightly-lab` run for **completeness** and **consistency**.

## What it does

- Reads `current-run.json` (or any `run.json`) and the referenced `status.jsonl`
- Shows the latest stage per `(agent, task)`
- Checks expected `start / artifact / done` stages for declared team + sidequest agents
- Verifies that report files listed in the run config exist
- Verifies that artifact paths recorded in `status.jsonl` still exist
- Returns `PASS` on a clean run, `WARN` with a non-zero exit code when something is missing

## Why this is useful

Raw `status.jsonl` files are annoying to eyeball when you only want to know whether the run is actually healthy. This script gives a compact audit view instead of making you grep through logs like a raccoon in a dumpster.

## Usage

Default current run:

```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-05-main-run-status-brief/run_status_brief.py
```

Custom run file and event tail:

```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-05-main-run-status-brief/run_status_brief.py \
  --run /root/.openclaw/workspace/nightly-lab/current-run.json \
  --show-events 8
```

## Test command

```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-05-main-run-status-brief/run_status_brief.py --show-events 3 || true
```
