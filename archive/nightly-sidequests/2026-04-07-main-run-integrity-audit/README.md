# run-integrity-audit

Zero-dependency Python 3 CLI for auditing `nightly-lab` run integrity.

## What it does
- Reads the active run from `nightly-lab/current-run.json` by default
- Parses `status.jsonl`
- Flags unresolved symbolic references accidentally written into events (for example `team_reports.killjoy`)
- Checks report/artifact path existence for progress and terminal events
- Checks basic per `(agent, task)` stage ordering (`start -> artifact -> done/error`)
- Supports machine-readable output with `--json`
- Returns non-zero exit codes when warnings or errors exist

## Why this is useful
The nightly flow already produces status events, but one bad path or one unresolved placeholder can silently poison the morning summary. This tool catches that drift fast instead of making humans eyeball JSONL at 8 AM.

## Usage
```bash
python3 run_integrity_audit.py
```

Explicit current-run path:
```bash
python3 run_integrity_audit.py /root/.openclaw/workspace/nightly-lab/current-run.json
```

Explicit status/current-run pair:
```bash
python3 run_integrity_audit.py \
  --current-run /root/.openclaw/workspace/nightly-lab/current-run.json \
  --status-file /root/.openclaw/workspace/nightly-lab/runs/2026-04-07/status.jsonl
```

JSON output:
```bash
python3 run_integrity_audit.py --json
```

## Exit codes
- `0`: no findings
- `1`: warnings only
- `2`: at least one error

## Test command
```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-07-main-run-integrity-audit/run_integrity_audit.py
```
