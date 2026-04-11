#!/usr/bin/env python3
"""status_peek: summarize latest nightly-lab status by agent/task from jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize latest status events by agent/task.")
    p.add_argument("status_file", help="Path to status jsonl file")
    p.add_argument("--task", dest="task", default=None, help="Filter by task (e.g. sidequest)")
    p.add_argument(
        "--limit",
        dest="limit",
        type=int,
        default=0,
        help="Only inspect the most recent N matched events (0 = all)",
    )
    return p.parse_args()


def load_events(path: Path, task: str | None) -> Tuple[List[dict], int]:
    skipped = 0
    events: List[dict] = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if not isinstance(rec, dict):
                skipped += 1
                continue
            if task and rec.get("task") != task:
                continue
            events.append(rec)

    return events, skipped


def summarize(events: List[dict]) -> Dict[Tuple[str, str], dict]:
    latest: Dict[Tuple[str, str], dict] = {}
    for rec in events:
        agent = str(rec.get("agent", "-") or "-")
        task = str(rec.get("task", "-") or "-")
        latest[(agent, task)] = rec
    return latest


def main() -> int:
    args = parse_args()
    path = Path(args.status_file)

    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2
    if not path.is_file():
        print(f"error: not a regular file: {path}", file=sys.stderr)
        return 2

    events, skipped = load_events(path, args.task)
    if args.limit and args.limit > 0:
        events = events[-args.limit :]

    latest = summarize(events)

    for (agent, task) in sorted(latest.keys()):
        rec = latest[(agent, task)]
        stage = rec.get("stage") or "-"
        ts = rec.get("ts") or "-"
        artifact = rec.get("artifact") or "-"
        error = rec.get("error_code") or "-"
        print(f"{agent} {task} stage={stage} ts={ts} artifact={artifact} error={error}")

    print(
        f"matched_events={len(events)} unique_agent_task={len(latest)} skipped_malformed={skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
