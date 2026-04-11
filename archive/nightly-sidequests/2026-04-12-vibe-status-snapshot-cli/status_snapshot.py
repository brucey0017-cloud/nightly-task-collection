#!/usr/bin/env python3
"""
status_snapshot.py

Small zero-dependency helper to inspect nightly-lab status.jsonl and print a compact
snapshot of per-agent progress for quick standups.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

DEFAULT_RUN_FILE = "/root/.openclaw/workspace/nightly-lab/current-run.json"


def iso_to_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def load_current_run(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def summarize(events: List[Dict[str, Any]], task_filter: Optional[str]) -> Dict[str, Any]:
    by_agent: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "events": 0,
        "latest_stage": None,
        "latest_task": None,
        "latest_ts": None,
        "latest_artifact": None,
        "errors": 0,
    })

    for ev in events:
        agent = (ev.get("agent") or "unknown").lower()
        task = ev.get("task")
        if task_filter and task != task_filter:
            continue

        info = by_agent[agent]
        info["events"] += 1

        stage = ev.get("stage")
        ts = iso_to_dt(ev.get("ts") or ev.get("timestamp"))
        prev_ts = info["latest_ts"]

        if stage == "error":
            info["errors"] += 1

        if prev_ts is None or (ts is not None and ts >= prev_ts):
            info["latest_ts"] = ts
            info["latest_stage"] = stage
            info["latest_task"] = task
            info["latest_artifact"] = ev.get("artifact")

    return by_agent


def print_text(summary: Dict[str, Any], logical_date: str, status_file: str) -> None:
    print(f"# Nightly Status Snapshot ({logical_date})")
    print(f"status_file: {status_file}")
    print("")

    if not summary:
        print("No matching events.")
        return

    order = sorted(summary.keys())
    for agent in order:
        info = summary[agent]
        ts = info["latest_ts"].isoformat(timespec="seconds") if info["latest_ts"] else "-"
        stage = info["latest_stage"] or "-"
        task = info["latest_task"] or "-"
        errors = info["errors"]
        artifact = info["latest_artifact"] or "-"
        print(f"- {agent}: stage={stage} task={task} events={info['events']} errors={errors} latest={ts}")
        if artifact != "-":
            print(f"  artifact: {artifact}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Quick snapshot for nightly-lab status.jsonl")
    parser.add_argument("--run-file", default=DEFAULT_RUN_FILE, help="Path to current-run.json")
    parser.add_argument("--status-file", default=None, help="Path to status.jsonl (overrides run-file)")
    parser.add_argument("--task", default=None, help="Optional task filter, e.g. sidequest")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args()

    run = load_current_run(args.run_file)
    status_file = args.status_file or run.get("status_file")
    logical_date = run.get("logical_date", "unknown")

    if not status_file or not os.path.exists(status_file):
        raise SystemExit(f"status file not found: {status_file}")

    events = load_jsonl(status_file)
    summary = summarize(events, args.task)

    if args.json:
        payload = {
            "logical_date": logical_date,
            "status_file": status_file,
            "agents": {
                agent: {
                    "events": info["events"],
                    "latest_stage": info["latest_stage"],
                    "latest_task": info["latest_task"],
                    "latest_ts": info["latest_ts"].isoformat() if info["latest_ts"] else None,
                    "latest_artifact": info["latest_artifact"],
                    "errors": info["errors"],
                }
                for agent, info in sorted(summary.items())
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text(summary, logical_date, status_file)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
