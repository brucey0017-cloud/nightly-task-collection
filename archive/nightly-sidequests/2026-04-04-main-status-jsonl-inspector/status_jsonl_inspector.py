#!/usr/bin/env python3
"""status_jsonl_inspector.py

Zero-dependency inspector for nightly-lab status.jsonl files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Dict, Iterable, List, Tuple

DEFAULT_STATUS_FILE = "/root/.openclaw/workspace/nightly-lab/runs/2026-04-04/status.jsonl"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inspect nightly-lab status.jsonl events")
    p.add_argument("--file", default=DEFAULT_STATUS_FILE, help="Path to status.jsonl file")
    p.add_argument("--agent", help="Only include events for this agent")
    p.add_argument("--task", help="Only include events for this task")
    p.add_argument("--stage", help="Only include events for this stage")
    p.add_argument(
        "--since",
        help="Only include events whose timestamp starts with this string (ISO prefix match)",
    )
    p.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")
    return p.parse_args()


def load_events(path: str) -> List[dict]:
    events: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            raw = line.strip()
            if not raw:
                continue
            try:
                evt = json.loads(raw)
            except json.JSONDecodeError:
                # Keep going; malformed lines should not kill the whole summary.
                continue
            if isinstance(evt, dict):
                evt["_line"] = line_no
                events.append(evt)
    return events


def match_filters(evt: dict, agent: str | None, task: str | None, stage: str | None, since: str | None) -> bool:
    if agent and str(evt.get("agent", "")) != agent:
        return False
    if task and str(evt.get("task", "")) != task:
        return False
    if stage and str(evt.get("stage", "")) != stage:
        return False
    if since:
        ts = str(evt.get("timestamp", ""))
        if not ts.startswith(since):
            return False
    return True


def summarize(events: Iterable[dict]) -> dict:
    events_list = list(events)

    per_agent = Counter(str(evt.get("agent", "unknown")) for evt in events_list)

    latest: Dict[Tuple[str, str], dict] = {}
    for evt in events_list:
        agent = str(evt.get("agent", "unknown"))
        task = str(evt.get("task", "unknown"))
        key = (agent, task)
        ts = str(evt.get("timestamp", ""))
        current = latest.get(key)
        if current is None or str(current.get("timestamp", "")) <= ts:
            latest[key] = evt

    latest_rows = []
    for (agent, task), evt in sorted(latest.items(), key=lambda x: (x[0][0], x[0][1])):
        latest_rows.append(
            {
                "agent": agent,
                "task": task,
                "stage": str(evt.get("stage", "")),
                "timestamp": str(evt.get("timestamp", "")),
                "artifact": evt.get("artifact"),
                "error_code": evt.get("error_code"),
                "line": evt.get("_line"),
            }
        )

    return {
        "total_events": len(events_list),
        "per_agent_counts": dict(sorted(per_agent.items(), key=lambda x: (-x[1], x[0]))),
        "latest_stage_per_agent_task": latest_rows,
    }


def print_text(source_file: str, filters: dict, summary: dict) -> None:
    print("Status JSONL Inspector")
    print(f"Source: {source_file}")
    print(
        "Filters: "
        + ", ".join(
            [
                f"agent={filters.get('agent') or '*'}",
                f"task={filters.get('task') or '*'}",
                f"stage={filters.get('stage') or '*'}",
                f"since={filters.get('since') or '*'}",
            ]
        )
    )
    print("")

    print(f"Total events: {summary['total_events']}")
    print("")

    print("Per-agent counts:")
    per_agent = summary["per_agent_counts"]
    if per_agent:
        for agent, count in per_agent.items():
            print(f"  - {agent}: {count}")
    else:
        print("  - (none)")

    print("")
    print("Latest stage per (agent, task):")
    latest_rows = summary["latest_stage_per_agent_task"]
    if latest_rows:
        for row in latest_rows:
            print(
                "  - "
                f"({row['agent']}, {row['task']}): {row['stage']}"
                f" @ {row['timestamp']}"
            )
    else:
        print("  - (none)")


def main() -> int:
    args = parse_args()

    if not os.path.exists(args.file):
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 1

    events = load_events(args.file)
    filtered = [
        evt
        for evt in events
        if match_filters(evt, args.agent, args.task, args.stage, args.since)
    ]

    filters = {
        "agent": args.agent,
        "task": args.task,
        "stage": args.stage,
        "since": args.since,
    }
    summary = summarize(filtered)

    if args.as_json:
        out = {
            "source": args.file,
            "filters": filters,
            **summary,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print_text(args.file, filters, summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
