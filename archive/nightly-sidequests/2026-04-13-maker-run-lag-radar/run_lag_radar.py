#!/usr/bin/env python3
"""run_lag_radar: quick status.jsonl visibility tool for nightly runs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_STATUS_FILE = "/root/.openclaw/workspace/nightly-lab/runs/2026-04-13/status.jsonl"
TERMINAL_STAGES = {"done", "error"}


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def minutes_between(start: datetime | None, end: datetime | None) -> float | None:
    if not start or not end:
        return None
    return round((end - start).total_seconds() / 60.0, 2)


def read_status(path: Path) -> Tuple[Dict[Tuple[str, str], Dict[str, Any]], List[Dict[str, Any]]]:
    stats: Dict[Tuple[str, str], Dict[str, Any]] = {}
    malformed: List[Dict[str, Any]] = []

    if not path.exists():
        raise FileNotFoundError(f"status file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                malformed.append({"line": i, "error": f"json_decode: {e.msg}"})
                continue

            agent = str(row.get("agent") or "").strip() or "unknown"
            task = str(row.get("task") or "").strip() or "unknown"
            stage = str(row.get("stage") or "").strip() or "unknown"
            ts = parse_ts(row.get("ts"))

            key = (agent, task)
            if key not in stats:
                stats[key] = {
                    "agent": agent,
                    "task": task,
                    "first_ts": ts,
                    "latest_ts": ts,
                    "event_count": 0,
                    "latest_stage": stage,
                }

            item = stats[key]
            item["event_count"] += 1
            item["latest_stage"] = stage

            if ts:
                if not item["first_ts"] or ts < item["first_ts"]:
                    item["first_ts"] = ts
                if not item["latest_ts"] or ts > item["latest_ts"]:
                    item["latest_ts"] = ts

    return stats, malformed


def build_output(stats: Dict[Tuple[str, str], Dict[str, Any]], malformed: List[Dict[str, Any]], status_file: str) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for _, item in sorted(stats.items(), key=lambda kv: (kv[1]["first_ts"] or datetime.max.replace(tzinfo=timezone.utc), kv[0])):
        first_ts = item["first_ts"]
        latest_ts = item["latest_ts"]
        rows.append(
            {
                "agent": item["agent"],
                "task": item["task"],
                "first_ts": to_iso(first_ts),
                "latest_ts": to_iso(latest_ts),
                "event_count": item["event_count"],
                "latest_stage": item["latest_stage"],
                "span_minutes": minutes_between(first_ts, latest_ts),
            }
        )

    open_starts = []
    for row in rows:
        if row["latest_stage"] in TERMINAL_STAGES:
            continue
        latest = parse_ts(row["latest_ts"])
        age = minutes_between(latest, now)
        open_starts.append(
            {
                "agent": row["agent"],
                "task": row["task"],
                "latest_stage": row["latest_stage"],
                "age_minutes": age,
                "latest_ts": row["latest_ts"],
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status_file": status_file,
        "rows": rows,
        "open_starts": open_starts,
        "malformed_lines": malformed,
    }


def print_table(payload: Dict[str, Any]) -> None:
    rows = payload["rows"]
    headers = ["agent", "task", "events", "latest_stage", "span_min", "first_ts", "latest_ts"]

    def val(row: Dict[str, Any], key: str) -> str:
        if key == "events":
            return str(row["event_count"])
        if key == "span_min":
            v = row["span_minutes"]
            return "" if v is None else str(v)
        return str(row.get(key, ""))

    widths = {h: len(h) for h in headers}
    for r in rows:
        for h in headers:
            widths[h] = max(widths[h], len(val(r, h)))

    print(f"status_file: {payload['status_file']}")
    print(f"generated_at: {payload['generated_at']}")
    print()

    line = "  ".join(h.ljust(widths[h]) for h in headers)
    print(line)
    print("  ".join("-" * widths[h] for h in headers))
    for r in rows:
        print("  ".join(val(r, h).ljust(widths[h]) for h in headers))

    print()
    print("Open starts without done/error")
    opens = payload["open_starts"]
    if not opens:
        print("- none")
    else:
        for o in opens:
            print(
                f"- {o['agent']}/{o['task']}: stage={o['latest_stage']} "
                f"age_min={o['age_minutes']} latest_ts={o['latest_ts']}"
            )

    malformed = payload.get("malformed_lines") or []
    if malformed:
        print()
        print("Malformed lines")
        for m in malformed:
            print(f"- line {m['line']}: {m['error']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run lag radar for nightly-lab status.jsonl")
    parser.add_argument("--status-file", default=DEFAULT_STATUS_FILE, help="path to status.jsonl")
    parser.add_argument("--json", action="store_true", help="emit JSON payload")
    args = parser.parse_args()

    path = Path(args.status_file)
    stats, malformed = read_status(path)
    payload = build_output(stats, malformed, str(path))

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_table(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
