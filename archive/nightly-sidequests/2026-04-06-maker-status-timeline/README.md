# status_timeline

Tiny zero-dependency viewer for `status.jsonl` timeline events.

## Usage

```bash
python3 status_timeline.py --input /path/to/status.jsonl
```

## Filters

```bash
# only maker records
python3 status_timeline.py --input /path/to/status.jsonl --agent maker

# only sidequest records
python3 status_timeline.py --input /path/to/status.jsonl --task sidequest

# last 10 matched rows
python3 status_timeline.py --input /path/to/status.jsonl --agent maker --last 10
```

## Smoke test (current run)

```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-06-maker-status-timeline/status_timeline.py \
  --input /root/.openclaw/workspace/nightly-lab/runs/2026-04-06/status.jsonl \
  --agent maker --task sidequest --last 10
```
