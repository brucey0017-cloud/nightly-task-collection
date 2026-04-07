#!/usr/bin/env python3
"""Tiny status.jsonl digest for nightly workflow visibility.

Usage:
  python3 status_digest.py --status /path/to/status.jsonl [--agent maker]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Tuple


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize nightly status JSONL events")
    p.add_argument("--status", required=True, help="Path to status.jsonl")
    p.add_argument("--agent", help="Optional agent filter, e.g. maker")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    status_path = Path(args.status)
    if not status_path.exists():
        raise SystemExit(f"status file not found: {status_path}")

    total = 0
    skipped = 0
    stage_counts: Dict[str, Counter] = defaultdict(Counter)
    latest: Dict[Tuple[str, str], dict] = {}

    with status_path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            raw = line.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                skipped += 1
                continue

            agent = str(event.get("agent", "")).strip() or "unknown"
            task = str(event.get("task", "")).strip() or "unknown"
            stage = str(event.get("stage", "")).strip() or "unknown"
            ts = str(event.get("ts", "")).strip()

            if args.agent and agent != args.agent:
                continue

            total += 1
            stage_counts[agent][stage] += 1

            key = (agent, task)
            prev = latest.get(key)
            if prev is None or ts >= prev.get("ts", ""):
                latest[key] = {
                    "ts": ts,
                    "stage": stage,
                    "artifact": event.get("artifact", ""),
                }

    print(f"Status file: {status_path}")
    print(f"Matched events: {total}")
    if skipped:
        print(f"Skipped malformed lines: {skipped}")

    if total == 0:
        return 0

    print("\nLatest stage by agent/task:")
    for (agent, task), info in sorted(latest.items()):
        artifact = f" | artifact={info['artifact']}" if info.get("artifact") else ""
        print(f"- {agent}/{task}: {info['stage']} @ {info['ts']}{artifact}")

    print("\nStage counts by agent:")
    for agent in sorted(stage_counts):
        parts = [f"{k}:{v}" for k, v in sorted(stage_counts[agent].items())]
        print(f"- {agent}: " + ", ".join(parts))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
