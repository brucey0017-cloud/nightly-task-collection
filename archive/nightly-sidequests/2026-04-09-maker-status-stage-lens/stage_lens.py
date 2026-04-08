#!/usr/bin/env python3
"""Summarize nightly-lab status.jsonl by stage/agent/workflow."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_STATUS_FILE = "/root/.openclaw/workspace/nightly-lab/runs/2026-04-09/status.jsonl"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize status.jsonl events.")
    p.add_argument("--status-file", default=DEFAULT_STATUS_FILE, help="Path to status.jsonl")
    p.add_argument("--task", help="Only include events matching task")
    p.add_argument("--agent", help="Only include events matching agent")
    p.add_argument("--stage", action="append", dest="stages", help="Only include events matching stage (repeatable)")
    p.add_argument("--json", action="store_true", dest="as_json", help="Print summary as JSON")
    return p.parse_args()


def safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def keep_entry(entry: Dict[str, Any], agent: str | None, task: str | None, stages: List[str] | None) -> bool:
    e_agent = safe_str(entry.get("agent"))
    e_task = safe_str(entry.get("task"))
    e_stage = safe_str(entry.get("stage"))

    if agent and e_agent != agent:
        return False
    if task and e_task != task:
        return False
    if stages and e_stage not in stages:
        return False
    return True


def summarize(path: Path, agent: str | None, task: str | None, stages: List[str] | None) -> Dict[str, Any]:
    stage_counts: Counter[str] = Counter()
    agent_counts: Counter[str] = Counter()
    workflows: Dict[Tuple[str, str], Dict[str, Any]] = {}

    total_events = 0
    invalid_lines = 0

    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue

            if not isinstance(entry, dict):
                invalid_lines += 1
                continue

            if not keep_entry(entry, agent=agent, task=task, stages=stages):
                continue

            total_events += 1
            e_stage = safe_str(entry.get("stage"))
            e_agent = safe_str(entry.get("agent"))
            e_task = safe_str(entry.get("task"))
            e_ts = safe_str(entry.get("ts"))

            stage_counts[e_stage] += 1
            agent_counts[e_agent] += 1

            key = (e_agent, e_task)
            wf = workflows.get(key)
            if wf is None:
                wf = {
                    "agent": e_agent,
                    "task": e_task,
                    "first_ts": e_ts,
                    "last_ts": e_ts,
                    "stages_seen": [],
                }
                workflows[key] = wf

            if not wf["first_ts"] or (e_ts and e_ts < wf["first_ts"]):
                wf["first_ts"] = e_ts
            if not wf["last_ts"] or (e_ts and e_ts > wf["last_ts"]):
                wf["last_ts"] = e_ts
            if e_stage and e_stage not in wf["stages_seen"]:
                wf["stages_seen"].append(e_stage)

    workflow_list = sorted(workflows.values(), key=lambda x: (x.get("agent", ""), x.get("task", "")))

    return {
        "status_file": str(path),
        "filters": {
            "agent": agent,
            "task": task,
            "stages": stages or [],
        },
        "total_events": total_events,
        "invalid_lines": invalid_lines,
        "counts_by_stage": dict(sorted(stage_counts.items())),
        "counts_by_agent": dict(sorted(agent_counts.items())),
        "workflows": workflow_list,
    }


def render_text(summary: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("Status summary")
    lines.append(f"- file: {summary['status_file']}")
    lines.append(f"- total_events: {summary['total_events']}")
    lines.append(f"- invalid_lines: {summary['invalid_lines']}")

    lines.append("\nCounts by stage:")
    if summary["counts_by_stage"]:
        for k, v in summary["counts_by_stage"].items():
            label = k if k else "<missing>"
            lines.append(f"- {label}: {v}")
    else:
        lines.append("- (none)")

    lines.append("\nCounts by agent:")
    if summary["counts_by_agent"]:
        for k, v in summary["counts_by_agent"].items():
            label = k if k else "<missing>"
            lines.append(f"- {label}: {v}")
    else:
        lines.append("- (none)")

    lines.append("\nWorkflows (agent/task):")
    if summary["workflows"]:
        for wf in summary["workflows"]:
            a = wf.get("agent") or "<missing>"
            t = wf.get("task") or "<missing>"
            first_ts = wf.get("first_ts") or ""
            last_ts = wf.get("last_ts") or ""
            stages = ", ".join(wf.get("stages_seen") or []) or "(none)"
            lines.append(f"- {a}/{t}")
            lines.append(f"  first_ts: {first_ts}")
            lines.append(f"  last_ts:  {last_ts}")
            lines.append(f"  stages_seen: {stages}")
    else:
        lines.append("- (none)")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    path = Path(args.status_file)
    try:
        summary = summarize(path, agent=args.agent, task=args.task, stages=args.stages)
    except OSError as e:
        print(f"error: cannot read status file: {e}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
