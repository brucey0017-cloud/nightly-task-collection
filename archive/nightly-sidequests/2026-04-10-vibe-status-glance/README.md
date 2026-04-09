# Status Glance (Nightly Lab)

A tiny zero-dependency helper to make nightly-lab progress visible in one command.

## What it does
- Reads `current-run.json`
- Parses the run's `status.jsonl`
- Shows the **latest stage** for each `(task, agent)`
- Flags stale lanes (`STALE`) by age threshold

## Usage
```bash
python3 status_glance.py
```

Filter by task:
```bash
python3 status_glance.py --task sidequest
```

Adjust stale threshold (minutes):
```bash
python3 status_glance.py --stale-minutes 45
```

Custom run file:
```bash
python3 status_glance.py --run-file /root/.openclaw/workspace/nightly-lab/current-run.json
```
