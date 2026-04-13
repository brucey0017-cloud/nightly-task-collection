#!/usr/bin/env python3
"""Status flow checker for nightly-lab status.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

DEFAULT_FILE = "/root/.openclaw/workspace/nightly-lab/runs/2026-04-14/status.jsonl"


@dataclass
class FlowSummary:
    agent: str
    task: str
    first_ts: str
    last_ts: str
    stages: list[str]
    has_error: bool
    last_stage: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse status.jsonl and print workflow visibility summary."
    )
    parser.add_argument("--file", default=DEFAULT_FILE, help="Path to status.jsonl")
    parser.add_argument(
        "--agent",
        action="append",
        default=[],
        help="Filter by agent (repeatable)",
    )
    parser.add_argument(
        "--task",
        action="append",
        default=[],
        help="Filter by task (repeatable)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser.parse_args()


def load_records(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    malformed = 0

    try:
        with path.open("r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, start=1):
                text = raw.strip()
                if not text:
                    continue
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                if not isinstance(obj, dict):
                    malformed += 1
                    continue
                obj.setdefault("_line", line_no)
                records.append(obj)
    except OSError:
        raise

    return records, malformed


def summarize(
    records: list[dict[str, Any]], agents: set[str], tasks: set[str]
) -> tuple[list[FlowSummary], Counter[str], int]:
    stage_counts: Counter[str] = Counter()
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    considered = 0

    for rec in records:
        agent = str(rec.get("agent", ""))
        task = str(rec.get("task", ""))
        if agents and agent not in agents:
            continue
        if tasks and task not in tasks:
            continue

        considered += 1
        stage = str(rec.get("stage", ""))
        stage_counts[stage] += 1
        grouped[(agent, task)].append(rec)

    summaries: list[FlowSummary] = []
    for (agent, task), items in sorted(grouped.items()):
        items_sorted = sorted(items, key=lambda x: (str(x.get("ts", "")), int(x.get("_line", 0))))
        stages = [str(i.get("stage", "")) for i in items_sorted]
        has_error = any(
            bool(str(i.get("error_code", "")).strip()) or str(i.get("stage", "")) == "error"
            for i in items_sorted
        )
        summaries.append(
            FlowSummary(
                agent=agent,
                task=task,
                first_ts=str(items_sorted[0].get("ts", "")),
                last_ts=str(items_sorted[-1].get("ts", "")),
                stages=stages,
                has_error=has_error,
                last_stage=stages[-1] if stages else "",
            )
        )

    return summaries, stage_counts, considered


def print_human(
    source: Path,
    total_records: int,
    considered: int,
    malformed: int,
    stage_counts: Counter[str],
    summaries: list[FlowSummary],
) -> None:
    print(f"Source: {source}")
    print(f"Total events: {considered} (loaded: {total_records}, malformed skipped: {malformed})")
    print("\nGlobal stage counts:")
    if stage_counts:
        for stage, count in stage_counts.most_common():
            print(f"- {stage or '<empty>'}: {count}")
    else:
        print("- (no matching events)")

    print("\nPer (agent, task):")
    if not summaries:
        print("- (no matching groups)")
        return

    for item in summaries:
        seq = " > ".join(item.stages) if item.stages else "(none)"
        print(f"- {item.agent}/{item.task}")
        print(f"  first_ts: {item.first_ts}")
        print(f"  last_ts:  {item.last_ts}")
        print(f"  stages:   {seq}")
        print(f"  has_error:{item.has_error}")
        print(f"  last_stage:{item.last_stage}")


def main() -> int:
    args = parse_args()
    source = Path(args.file)

    try:
        records, malformed = load_records(source)
    except OSError as e:
        print(f"error: cannot read file '{source}': {e}", file=sys.stderr)
        return 2

    agents = {a.strip() for a in args.agent if a.strip()}
    tasks = {t.strip() for t in args.task if t.strip()}

    summaries, stage_counts, considered = summarize(records, agents, tasks)

    if args.json:
        payload = {
            "source": str(source),
            "total_loaded": len(records),
            "total_events": considered,
            "malformed_skipped": malformed,
            "stage_counts": dict(stage_counts),
            "groups": [asdict(s) for s in summaries],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(source, len(records), considered, malformed, stage_counts, summaries)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
