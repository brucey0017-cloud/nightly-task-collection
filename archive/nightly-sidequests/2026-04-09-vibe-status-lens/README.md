# status-lens

Tiny zero-dependency CLI to inspect `nightly-lab` `status.jsonl` progress.

## Why

`status.jsonl` is append-only and easy to miss at 2am. This script gives a one-shot summary:
- latest stage per `agent/task`
- elapsed minutes
- stage order violations (`start -> artifact -> done` expected)
- non-canonical stages (`warn`, `error`, etc.)

## Usage

```bash
python3 status_lens.py
python3 status_lens.py --task sidequest
python3 status_lens.py --json
python3 status_lens.py --status-file /path/to/status.jsonl
```

## Output sample

```text
agent/task                 stage      mins  flags
----------------------------------------------------------------
vibe/sidequest             artifact  0.23  -

Details:
- vibe/sidequest: start > artifact
```
