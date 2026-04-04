# Maker Sidequest: Status Board

A tiny zero-dependency Python tool for **workflow visibility** on nightly-lab runs.

## What it does
- Shows latest stage per `(agent, task)`
- Shows stage counts per agent
- Shows last N events from `status.jsonl`
- Skips malformed JSONL lines safely

## Usage
```bash
python3 status_board.py
```

Custom file and tail:
```bash
python3 status_board.py --file /path/to/status.jsonl --tail 20
```

Filter by agent:
```bash
python3 status_board.py --agent maker --tail 5
```

## Default log path
`/root/.openclaw/workspace/nightly-lab/runs/2026-04-05/status.jsonl`
