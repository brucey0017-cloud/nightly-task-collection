# Sidequest: slot-guard visibility

A small self-contained visibility helper for diagnosing why `agent_slot_guard.py` blocks sidequest start.

## Built / explored
- Captured run status snapshot files.
- Added a zero-dependency Python helper (`build_active_tasks.py`) that computes latest non-terminal tasks per `(agent, task)`.
- Generated `active-tasks.md` from the current run status log.

## Why this is useful
When sidequest is delayed, this quickly reveals whether a stale non-terminal task (for example `team/start` without `done`/`error`) is blocking slot acquisition.

## Files
- `status-full.jsonl`
- `status-tail-120.jsonl`
- `build_active_tasks.py`
- `active-tasks.md`

## Test command
```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-10-maker-slot-guard-visibility/build_active_tasks.py
```
