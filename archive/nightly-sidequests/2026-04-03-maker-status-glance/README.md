# Status Glance (Maker Sidequest)

A tiny zero-dependency workflow visibility helper for nightly-lab runs.

## What it does

- Reads `current-run.json` to locate the active `status.jsonl`
- Extracts the latest stage per `(agent, task)`
- Renders a compact markdown dashboard at `status-glance.md`

## Files

- `refresh_status_glance.py` — generator script
- `status-glance.md` — generated dashboard snapshot

## Test / refresh

```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-03-maker-status-glance/refresh_status_glance.py
```
