#!/usr/bin/env python3
"""Nightly status lens: quick visibility over status.jsonl progress.

Zero dependencies, Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CANONICAL_ORDER = {"start": 1, "artifact": 2, "done": 3}


@dataclass
class Track:
    agent: str
    task: str
    stage: str
    first_ts: str
    last_ts: str
    duration_min: float
    stage_path: List[str]
    report: str
    artifact: str
    error_code: str
    note: str
    non_canonical_stages: List[str]
    order_violation: bool


def parse_ts(value: str) -> datetime:
    # status file uses RFC3339-like timestamps with timezone
    return datetime.fromisoformat(value)


def load_current_run(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[Dict]:
    rows = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            # Skip malformed lines; status stream should remain readable.
            continue
    return rows


def build_tracks(rows: List[Dict], only_task: Optional[str] = None) -> List[Track]:
    grouped: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for row in rows:
        key = (row.get("agent", ""), row.get("task", ""))
        grouped[key].append(row)

    tracks: List[Track] = []
    for (agent, task), items in grouped.items():
        if only_task and task != only_task:
            continue
        items.sort(key=lambda x: parse_ts(x.get("ts", "1970-01-01T00:00:00+00:00")))
        first = items[0]
        last = items[-1]
        first_dt = parse_ts(first["ts"])
        last_dt = parse_ts(last["ts"])

        stage_path = [it.get("stage", "") for it in items]
        non_canonical = sorted({s for s in stage_path if s not in CANONICAL_ORDER})

        rank_seq = [CANONICAL_ORDER[s] for s in stage_path if s in CANONICAL_ORDER]
        order_violation = any(b < a for a, b in zip(rank_seq, rank_seq[1:]))

        tracks.append(
            Track(
                agent=agent,
                task=task,
                stage=last.get("stage", ""),
                first_ts=first.get("ts", ""),
                last_ts=last.get("ts", ""),
                duration_min=round((last_dt - first_dt).total_seconds() / 60.0, 2),
                stage_path=stage_path,
                report=last.get("report", ""),
                artifact=last.get("artifact", ""),
                error_code=last.get("error_code", ""),
                note=last.get("note", ""),
                non_canonical_stages=non_canonical,
                order_violation=order_violation,
            )
        )

    tracks.sort(key=lambda t: (t.task, t.agent))
    return tracks


def render_text(tracks: List[Track]) -> str:
    if not tracks:
        return "No matching status tracks found."

    lines = []
    lines.append("agent/task                 stage      mins  flags")
    lines.append("-" * 64)

    for t in tracks:
        flags = []
        if t.order_violation:
            flags.append("order")
        if t.non_canonical_stages:
            flags.append("extra:" + ",".join(t.non_canonical_stages))
        if t.stage == "error" and t.error_code:
            flags.append("err:" + t.error_code)
        flag_text = " | ".join(flags) if flags else "-"
        lines.append(f"{t.agent}/{t.task:<20} {t.stage:<10} {t.duration_min:>5}  {flag_text}")

    lines.append("\nDetails:")
    for t in tracks:
        stage_joined = " > ".join(t.stage_path)
        lines.append(
            f"- {t.agent}/{t.task}: {stage_joined}"
            + (f" | note={t.note}" if t.note else "")
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect nightly-lab status.jsonl progress")
    parser.add_argument(
        "--current-run",
        default="/root/.openclaw/workspace/nightly-lab/current-run.json",
        help="Path to current-run.json",
    )
    parser.add_argument(
        "--status-file",
        default="",
        help="Optional explicit status.jsonl path (overrides current-run.json)",
    )
    parser.add_argument("--task", default="", help="Filter by task (e.g. sidequest)")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    if args.status_file:
        status_path = Path(args.status_file)
    else:
        run = load_current_run(Path(args.current_run))
        status_path = Path(run["status_file"])

    rows = read_jsonl(status_path)
    tracks = build_tracks(rows, only_task=(args.task or None))

    if args.json:
        print(json.dumps([asdict(t) for t in tracks], ensure_ascii=False, indent=2))
    else:
        print(render_text(tracks))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
