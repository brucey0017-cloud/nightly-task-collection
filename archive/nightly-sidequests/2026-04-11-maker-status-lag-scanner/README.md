# status-lag-scanner

Small zero-dependency CLI to summarize latest nightly `status.jsonl` entries by `(agent, task)` and flag stale active rows.

## Usage

```bash
python3 status_lag_scanner.py
```

Optional flags:

- `--status-file <path>`: explicit `status.jsonl`
- `--now-utc <ISO8601>`: deterministic reference time
- `--stale-min <int>`: stale threshold in minutes (default `30`)
- `--format <text|markdown>`: output style (default `text`)

## Example

```bash
python3 status_lag_scanner.py --status-file /root/.openclaw/workspace/nightly-lab/runs/2026-04-11/status.jsonl --stale-min 45 --format markdown
```
