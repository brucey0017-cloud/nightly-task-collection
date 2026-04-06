#!/usr/bin/env python3
"""Inspect nightly-lab status.jsonl files.

Features:
- Total matched events
- Stage counts
- Latest event per (agent, task)
- Optional filters: --agent, --task, --since-minutes
- Optional JSON output: --json

Zero external dependencies (Python 3 stdlib only).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect nightly-lab status.jsonl files")
    parser.add_argument("status_file", help="Path to status.jsonl")
    parser.add_argument("--agent", help="Only include this agent")
    parser.add_argument("--task", help="Only include this task")
    parser.add_argument(
        "--since-minutes",
        type=float,
        default=None,
        help="Only include events newer than now-<minutes> (UTC)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def parse_ts(ts_text: str | None) -> dt.datetime | None:
    if not ts_text:
        return None
    text = ts_text.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except ValueError:
        return None


def iso_or_blank(d: dt.datetime | None) -> str:
    return d.isoformat() if d else ""


def load_events(path: Path) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    invalid_lines = 0

    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            obj["_line"] = i
            obj["_parsed_ts"] = parse_ts(obj.get("ts"))
            events.append(obj)

    return events, invalid_lines


def apply_filters(
    events: list[dict[str, Any]],
    agent: str | None,
    task: str | None,
    since_minutes: float | None,
) -> list[dict[str, Any]]:
    out = events

    if agent:
        out = [e for e in out if str(e.get("agent", "")) == agent]

    if task:
        out = [e for e in out if str(e.get("task", "")) == task]

    if since_minutes is not None:
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=since_minutes)
        out = [e for e in out if e.get("_parsed_ts") and e["_parsed_ts"] >= cutoff]

    return out


def build_summary(events: list[dict[str, Any]], invalid_lines: int) -> dict[str, Any]:
    stage_counts = Counter(str(e.get("stage", "")) for e in events)

    latest_by_pair: dict[tuple[str, str], dict[str, Any]] = {}

    # Stable ordering by parsed timestamp (fallback to minimum) then line number.
    def event_sort_key(e: dict[str, Any]) -> tuple[dt.datetime, int]:
        ts = e.get("_parsed_ts") or dt.datetime.min.replace(tzinfo=dt.timezone.utc)
        return ts, int(e.get("_line", 0))

    for e in sorted(events, key=event_sort_key):
        pair = (str(e.get("agent", "")), str(e.get("task", "")))
        latest_by_pair[pair] = e

    latest_rows = []
    for (agent, task), ev in sorted(latest_by_pair.items(), key=lambda x: (x[0][0], x[0][1])):
        latest_rows.append(
            {
                "agent": agent,
                "task": task,
                "stage": str(ev.get("stage", "")),
                "ts": iso_or_blank(ev.get("_parsed_ts")),
                "artifact": str(ev.get("artifact", "")),
                "report": str(ev.get("report", "")),
                "line": int(ev.get("_line", 0)),
            }
        )

    return {
        "total_events": len(events),
        "invalid_lines": invalid_lines,
        "stage_counts": dict(sorted(stage_counts.items())),
        "latest_by_agent_task": latest_rows,
    }


def print_text(summary: dict[str, Any], source: Path, args: argparse.Namespace) -> None:
    print("Status JSONL Inspector")
    print("=" * 22)
    print(f"File: {source}")

    filters = []
    if args.agent:
        filters.append(f"agent={args.agent}")
    if args.task:
        filters.append(f"task={args.task}")
    if args.since_minutes is not None:
        filters.append(f"since_minutes={args.since_minutes}")
    print("Filters:", ", ".join(filters) if filters else "(none)")

    print(f"Total events: {summary['total_events']}")
    print(f"Invalid lines skipped: {summary['invalid_lines']}")

    print("\nStage counts:")
    if summary["stage_counts"]:
        for stage, count in summary["stage_counts"].items():
            print(f"- {stage or '(blank)'}: {count}")
    else:
        print("- (none)")

    print("\nLatest event per (agent, task):")
    rows = summary["latest_by_agent_task"]
    if not rows:
        print("- (none)")
    for row in rows:
        print(
            f"- {row['agent']}/{row['task']}: {row['stage']} @ {row['ts'] or '(no-ts)'} "
            f"[line {row['line']}]"
        )


def main() -> int:
    args = parse_args()
    source = Path(args.status_file)

    if not source.exists():
        print(f"ERROR: file not found: {source}", file=sys.stderr)
        return 2

    events, invalid = load_events(source)
    filtered = apply_filters(events, args.agent, args.task, args.since_minutes)
    summary = build_summary(filtered, invalid)
    summary["source_file"] = str(source)
    summary["filters"] = {
        "agent": args.agent,
        "task": args.task,
        "since_minutes": args.since_minutes,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_text(summary, source, args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
