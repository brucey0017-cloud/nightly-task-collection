# status-digest (maker sidequest)

Tiny zero-dependency workflow visibility helper for tonight's run.

## What it does

`status_digest.py` parses the run status JSONL and generates `STATUS_DIGEST.md` with:

- total event count
- per-agent event counts
- latest stage for each `agent/task` pair
- latest 12 events snapshot

Malformed JSON lines are skipped safely.

## Usage

```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-04-maker-status-digest/status_digest.py
```

Output:

- `/root/.openclaw/workspace/nightly-sidequests/2026-04-04-maker-status-digest/STATUS_DIGEST.md`
