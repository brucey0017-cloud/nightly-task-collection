# runpulse — nightly-lab run dashboard

One-command visibility into nightly-lab run status. Parses `status.jsonl` and renders a clean summary.

## What it does

- **Agent timeline**: per-agent task status with elapsed time
- **Health at a glance**: ✅ OK / ❌ ERROR / ⏳ IN-PROGRESS
- **Artifacts**: shows what each agent produced
- **Wall clock**: total run duration
- **CI-friendly**: exit 1 if any errors

## Usage

```bash
# Auto-detect latest run
python3 runpulse.py

# Specific date
python3 runpulse.py --date 2026-04-09

# Specific status file
python3 runpulse.py /path/to/status.jsonl

# Compact (one line per agent)
python3 runpulse.py --compact

# JSON output (for piping)
python3 runpulse.py --json
```

## Output example

```
════════════════════════════════════════════════════════════
  RUNPULSE — nightly-lab dashboard
  Run: 2026-04-09
════════════════════════════════════════════════════════════

── TEAM TASKS ──────────────────────────────────────
  ✅ commander    │ OK           │    1m20s
     artifact: .../01-commander.md
  ✅ killjoy      │ OK           │    1m05s
  ✅ maker        │ OK           │    8m12s
     artifact: .../2026-04-09-keyhound
  ✅ vibe         │ OK           │      26s

── SUMMARY ─────────────────────────────────────────
  Total tasks: 4  │  ✅ 4  ❌ 0  ⏳ 0
  Wall clock:  1h08m45s
════════════════════════════════════════════════════════════
```

## Design decisions

- **Zero dependencies** — Python 3 stdlib only
- **No network calls** — reads local files only
- **No state** — pure function of status.jsonl
- **CI-friendly exit codes** — 0 = all good, 1 = any error
