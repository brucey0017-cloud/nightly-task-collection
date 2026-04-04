#!/usr/bin/env python3
"""status_lens.py

Parse a nightly-lab status.jsonl and print:
1) per-agent timeline (task: stage -> stage ...)
2) latest stage summary per (agent, task)

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_ts(ts: str) -> datetime:
    # Handles ISO8601 like 2026-04-02T20:34:04.224329+00:00
    return datetime.fromisoformat(ts)


def load_rows(status_file: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with status_file.open("r", encoding="utf-8") as f:
        for ln, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as e:
                raise SystemExit(f"Invalid JSON at line {ln}: {e}")
            if not isinstance(row, dict):
                continue
            rows.append(row)
    rows.sort(key=lambda r: parse_ts(str(r.get("ts", "1970-01-01T00:00:00+00:00"))))
    return rows


def build_view(rows: list[dict[str, Any]]) -> dict[str, Any]:
    timeline: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    latest: dict[tuple[str, str], dict[str, str]] = {}

    for r in rows:
        agent = str(r.get("agent", "unknown"))
        task = str(r.get("task", "unknown"))
        stage = str(r.get("stage", ""))
        ts = str(r.get("ts", ""))
        artifact = str(r.get("artifact", ""))
        error_code = str(r.get("error_code", ""))

        timeline[agent][task].append(
            {
                "ts": ts,
                "stage": stage,
                "error_code": error_code,
            }
        )

        latest[(agent, task)] = {
            "ts": ts,
            "stage": stage,
            "artifact": artifact,
            "error_code": error_code,
        }

    latest_rows = [
        {
            "agent": agent,
            "task": task,
            **meta,
        }
        for (agent, task), meta in latest.items()
    ]
    latest_rows.sort(key=lambda x: (x["agent"], x["task"]))

    return {
        "timeline": timeline,
        "latest": latest_rows,
        "event_count": len(rows),
    }


def print_text(view: dict[str, Any]) -> None:
    print(f"Events: {view['event_count']}")
    print("\n=== Timeline by agent/task ===")

    timeline = view["timeline"]
    for agent in sorted(timeline.keys()):
        print(f"\n[{agent}]")
        for task in sorted(timeline[agent].keys()):
            items = timeline[agent][task]
            chain = " -> ".join(i["stage"] for i in items)
            first_ts = items[0]["ts"] if items else ""
            last_ts = items[-1]["ts"] if items else ""
            print(f"- {task}: {chain}")
            print(f"  {first_ts} .. {last_ts}")

    print("\n=== Latest stage summary ===")
    for row in view["latest"]:
        extra = f" error={row['error_code']}" if row.get("error_code") else ""
        artifact = row.get("artifact") or "-"
        print(
            f"- {row['agent']}/{row['task']}: {row['stage']} @ {row['ts']} | artifact={artifact}{extra}"
        )


def main() -> None:
    p = argparse.ArgumentParser(description="Summarize nightly-lab status.jsonl")
    p.add_argument(
        "--status-file",
        default="/root/.openclaw/workspace/nightly-lab/runs/2026-04-03/status.jsonl",
        help="Path to status.jsonl",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable text",
    )
    args = p.parse_args()

    status_file = Path(args.status_file)
    if not status_file.exists():
        raise SystemExit(f"status file not found: {status_file}")

    rows = load_rows(status_file)
    view = build_view(rows)

    if args.json:
        printable = {
            "event_count": view["event_count"],
            "latest": view["latest"],
            "timeline": {
                a: {t: evs for t, evs in tasks.items()} for a, tasks in view["timeline"].items()
            },
        }
        print(json.dumps(printable, ensure_ascii=False, indent=2))
        return

    print_text(view)


if __name__ == "__main__":
    main()
