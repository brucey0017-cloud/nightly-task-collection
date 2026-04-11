# status-peek

Tiny Python 3 (stdlib-only) CLI to inspect nightly-lab `status.jsonl` and show the latest stage per `agent + task`.

## Usage

```bash
./status_peek.py /root/.openclaw/workspace/nightly-lab/runs/2026-04-12/status.jsonl --task sidequest
```

Optional:
- `--limit N` to only inspect the most recent N matched events.
