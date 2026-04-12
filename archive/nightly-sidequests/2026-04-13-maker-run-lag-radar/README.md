# Run Lag Radar

Tiny zero-dependency CLI for nightly workflow visibility.

## What it does
- Parses `status.jsonl`
- Aggregates per `(agent, task)`:
  - first timestamp
  - latest timestamp
  - event count
  - latest stage
  - total span minutes (`first -> latest`)
- Highlights **Open starts without done/error** (latest stage still `start`/`artifact` etc.)
- Handles malformed JSONL lines safely and reports them

## Files
- `run_lag_radar.py`

## Usage
```bash
python3 run_lag_radar.py
python3 run_lag_radar.py --status-file /root/.openclaw/workspace/nightly-lab/runs/2026-04-13/status.jsonl
python3 run_lag_radar.py --json
```

## Test command
```bash
python3 run_lag_radar.py --status-file /root/.openclaw/workspace/nightly-lab/runs/2026-04-13/status.jsonl
```
