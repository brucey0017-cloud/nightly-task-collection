# status-lens

A tiny zero-dependency Python tool to summarize nightly-lab `status.jsonl` progress.

## What it does
- Shows per-agent/per-task stage timeline (`start -> artifact -> done` etc.)
- Shows latest stage snapshot for each `(agent, task)`
- Supports text and JSON output

## Usage

```bash
python3 status_lens.py --status-file /root/.openclaw/workspace/nightly-lab/runs/2026-04-03/status.jsonl
```

JSON output:

```bash
python3 status_lens.py --status-file /root/.openclaw/workspace/nightly-lab/runs/2026-04-03/status.jsonl --json
```
