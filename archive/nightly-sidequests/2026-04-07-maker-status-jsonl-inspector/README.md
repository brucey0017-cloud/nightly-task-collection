# status-jsonl-inspector

Small zero-dependency Python tool for nightly-lab workflow visibility.

## What it does
- Parses `status.jsonl` (one JSON event per line)
- Shows total matched events
- Shows counts by `stage`
- Shows the latest event per `(agent, task)` pair
- Supports filters:
  - `--agent`
  - `--task`
  - `--since-minutes`
- Supports machine-readable output with `--json`

## Usage

```bash
python3 status_jsonl_inspector.py /path/to/status.jsonl
```

Filter by task:

```bash
python3 status_jsonl_inspector.py /path/to/status.jsonl --task sidequest
```

Recent events only (last 120 minutes):

```bash
python3 status_jsonl_inspector.py /path/to/status.jsonl --since-minutes 120
```

JSON output:

```bash
python3 status_jsonl_inspector.py /path/to/status.jsonl --task sidequest --json
```

## Test command

```bash
python3 status_jsonl_inspector.py /root/.openclaw/workspace/nightly-lab/runs/2026-04-07/status.jsonl --task sidequest
```
