# status-flow-check

Tiny Python 3 CLI for quick workflow visibility from nightly-lab `status.jsonl`.

## What it shows

1. Total events
2. Per `(agent, task)` summary:
   - `first_ts`
   - `last_ts`
   - stage sequence
   - `has_error`
   - `last_stage`
3. Global stage counts
4. Malformed JSONL line count (skipped)

## Usage

```bash
python3 status_flow_check.py
```

Optional filters / machine output:

```bash
python3 status_flow_check.py --agent maker --task sidequest
python3 status_flow_check.py --file /path/to/status.jsonl --json
```

## Exit codes

- `0`: success
- `2`: input file missing or unreadable

## Tiny self-test

```bash
python3 status_flow_check.py --agent maker --task sidequest | head -n 30
```
