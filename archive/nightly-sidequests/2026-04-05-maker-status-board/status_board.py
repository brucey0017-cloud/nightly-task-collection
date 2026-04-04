#!/usr/bin/env python3
"""status_board.py

Quick workflow visibility helper for nightly-lab status.jsonl logs.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_FILE = "/root/.openclaw/workspace/nightly-lab/runs/2026-04-05/status.jsonl"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize nightly-lab status.jsonl")
    p.add_argument("--file", default=DEFAULT_FILE, help="Path to status.jsonl file")
    p.add_argument("--tail", type=int, default=10, help="Show last N events (default: 10)")
    p.add_argument("--agent", default=None, help="Optional agent filter (e.g. maker)")
    return p.parse_args()


def load_events(path: Path, agent_filter: str | None = None) -> Tuple[List[Dict[str, Any]], int]:
    events: List[Dict[str, Any]] = []
    malformed = 0

    if not path.exists():
        raise FileNotFoundError(f"Status log not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue

            if not isinstance(obj, dict):
                malformed += 1
                continue

            agent = str(obj.get("agent", "")).strip()
            if agent_filter and agent.lower() != agent_filter.lower():
                continue

            obj["_lineno"] = lineno
            events.append(obj)

    return events, malformed


def summarize_latest(events: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    latest: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for e in events:
        key = (str(e.get("agent", "unknown")), str(e.get("task", "unknown")))
        latest[key] = e
    return latest


def print_report(events: List[Dict[str, Any]], malformed: int, tail: int) -> None:
    latest = summarize_latest(events)
    stage_counts: Dict[str, Counter] = defaultdict(Counter)

    for e in events:
        agent = str(e.get("agent", "unknown"))
        stage = str(e.get("stage", "unknown"))
        stage_counts[agent][stage] += 1

    print("== Status Board ==")
    print(f"total_events: {len(events)}")
    print(f"malformed_lines_skipped: {malformed}")
    print()

    print("== Latest stage per (agent, task) ==")
    if not latest:
        print("(no events)")
    else:
        for (agent, task), e in sorted(latest.items()):
            ts = e.get("ts", "")
            stage = e.get("stage", "")
            print(f"- {agent}/{task}: {stage} @ {ts}")
    print()

    print("== Stage counts per agent ==")
    if not stage_counts:
        print("(no events)")
    else:
        for agent in sorted(stage_counts):
            c = stage_counts[agent]
            parts = [f"{k}:{v}" for k, v in sorted(c.items())]
            print(f"- {agent}: " + ", ".join(parts))
    print()

    print(f"== Last {max(0, tail)} events ==")
    if tail <= 0:
        print("(tail disabled)")
    else:
        for e in events[-tail:]:
            print(
                f"- line {e.get('_lineno')}: "
                f"{e.get('ts', '')} | {e.get('agent', '')}/{e.get('task', '')} "
                f"| {e.get('stage', '')} | artifact={e.get('artifact', '')}"
            )


def main() -> int:
    args = parse_args()
    try:
        events, malformed = load_events(Path(args.file), agent_filter=args.agent)
    except FileNotFoundError as e:
        print(str(e))
        return 2

    print_report(events, malformed, args.tail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
