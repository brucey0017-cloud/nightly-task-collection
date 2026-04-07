# maker sidequest — status digest

Small zero-dependency Python tool for parsing nightly `status.jsonl` and showing:

- matched event count
- latest stage per `agent/task`
- stage counts by agent

## Files

- `status_digest.py` — CLI tool

## Usage

```bash
python3 status_digest.py --status /root/.openclaw/workspace/nightly-lab/runs/2026-04-08/status.jsonl
```

Filter one agent:

```bash
python3 status_digest.py --status /root/.openclaw/workspace/nightly-lab/runs/2026-04-08/status.jsonl --agent maker
```

## Test command (run in this folder)

```bash
python3 status_digest.py --status /root/.openclaw/workspace/nightly-lab/runs/2026-04-08/status.jsonl --agent maker
```

Expected shape: shows latest `maker/team` and `maker/sidequest` stages plus stage counts (`start`, `artifact`, etc.).
