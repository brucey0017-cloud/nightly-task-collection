#!/usr/bin/env python3
"""
status_glance.py

Quick workflow visibility helper for nightly-lab runs.
- Reads current-run.json (or provided --run-file)
- Parses status.jsonl
- Shows latest stage per (task, agent)
- Highlights stale entries by minutes

Zero dependencies (Python 3 standard library only).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Show concise status summary for nightly-lab run")
    p.add_argument(
        "--run-file",
        default="/root/.openclaw/workspace/nightly-lab/current-run.json",
        help="Path to current-run.json",
    )
    p.add_argument(
        "--stale-minutes",
        type=int,
        default=30,
        help="Mark entries older than this threshold as STALE (default: 30)",
    )
    p.add_argument(
        "--task",
        default="",
        help="Optional task filter (e.g. sidequest, team)",
    )
    return p.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_iso(ts: str) -> dt.datetime:
    # Supports e.g. 2026-04-10T00:35:16.045588+08:00
    return dt.datetime.fromisoformat(ts)


def load_status_lines(status_file: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not status_file.exists():
        return rows
    for raw in status_file.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            # Skip malformed lines to keep tool resilient
            continue
    return rows


def latest_by_key(rows: List[Dict[str, Any]], task_filter: str = "") -> Dict[Tuple[str, str], Dict[str, Any]]:
    latest: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        task = str(row.get("task", ""))
        agent = str(row.get("agent", ""))
        if task_filter and task != task_filter:
            continue
        key = (task, agent)
        ts = row.get("ts")
        if not ts:
            continue
        if key not in latest:
            latest[key] = row
            continue
        try:
            old_ts = parse_iso(str(latest[key]["ts"]))
            new_ts = parse_iso(str(ts))
            if new_ts >= old_ts:
                latest[key] = row
        except Exception:
            latest[key] = row
    return latest


def format_age_minutes(now: dt.datetime, then: dt.datetime) -> int:
    delta = now - then
    return max(0, int(delta.total_seconds() // 60))


def main() -> int:
    args = parse_args()
    run_file = Path(args.run_file)
    if not run_file.exists():
        print(f"ERROR: run file not found: {run_file}")
        return 2

    run = load_json(run_file)
    status_file = Path(run["status_file"])
    rows = load_status_lines(status_file)
    latest = latest_by_key(rows, task_filter=args.task)

    now = dt.datetime.now(dt.timezone.utc)

    print("== Nightly Run Glance ==")
    print(f"run_id       : {run.get('run_id', '-')}")
    print(f"logical_date : {run.get('logical_date', '-')}")
    print(f"status_file  : {status_file}")
    print(f"events_total : {len(rows)}")
    print()

    if not latest:
        print("No matching status entries yet.")
        return 0

    print("Latest stage by (task, agent):")
    print("-" * 80)
    print(f"{'TASK':<12} {'AGENT':<10} {'STAGE':<12} {'AGE_MIN':>8}  FLAG")
    print("-" * 80)

    # Stable sort by task, then agent
    for (task, agent) in sorted(latest.keys()):
        row = latest[(task, agent)]
        stage = str(row.get("stage", "-"))
        ts_raw = str(row.get("ts", ""))

        flag = "OK"
        age_min = -1
        try:
            event_ts = parse_iso(ts_raw).astimezone(dt.timezone.utc)
            age_min = format_age_minutes(now, event_ts)
            if age_min >= args.stale_minutes and stage not in {"done"}:
                flag = "STALE"
        except Exception:
            flag = "BAD_TS"

        age_text = str(age_min) if age_min >= 0 else "-"
        print(f"{task:<12} {agent:<10} {stage:<12} {age_text:>8}  {flag}")

    print("-" * 80)
    print(f"stale_threshold_min: {args.stale_minutes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
