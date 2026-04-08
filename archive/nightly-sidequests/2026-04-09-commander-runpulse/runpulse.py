#!/usr/bin/env python3
"""runpulse — nightly-lab run dashboard.

Reads a nightly-lab status.jsonl and produces a human-readable summary:
  - Agent timeline (start → done, elapsed time)
  - Per-agent status (OK / ERROR / IN-PROGRESS)
  - Artifacts produced
  - Sidequest reports
  - Overall run health at a glance

Usage:
  python3 runpulse.py                          # auto-detect latest run
  python3 runpulse.py /path/to/status.jsonl    # specific run
  python3 runpulse.py --date 2026-04-09        # by logical date
  python3 runpulse.py --json                   # machine-readable output
  python3 runpulse.py --compact                # one-line per agent

Zero dependencies — Python 3 stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Nightly lab roots ────────────────────────────────────────────────
LAB_ROOT = Path("/root/.openclaw/workspace/nightly-lab")
RUNS_DIR = LAB_ROOT / "runs"
SIDEQUEST_DIR = LAB_ROOT / "sidequests"

TERMINAL = {"done", "error"}
ERROR_STAGES = {"error"}


# ── Data loading ─────────────────────────────────────────────────────
def load_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def find_status_file(date: Optional[str] = None) -> Optional[Path]:
    if date:
        p = RUNS_DIR / date / "status.jsonl"
        return p if p.exists() else None
    # Find latest run directory
    if not RUNS_DIR.exists():
        return None
    dirs = sorted(RUNS_DIR.iterdir()) if RUNS_DIR.exists() else []
    for d in reversed(dirs):
        if d.is_dir():
            sf = d / "status.jsonl"
            if sf.exists():
                return sf
    return None


# ── Parsing ──────────────────────────────────────────────────────────
def parse_ts(ts_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def build_agent_summary(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build per-agent, per-task summary from rows."""
    # key = (agent, task) → dict of stages
    buckets: Dict[tuple, Dict[str, Any]] = {}

    for row in rows:
        agent = row.get("agent", "?")
        task = row.get("task", "?")
        stage = row.get("stage", "?")
        key = (agent, task)
        if key not in buckets:
            buckets[key] = {
                "agent": agent,
                "task": task,
                "stages": [],
                "artifact": row.get("artifact", ""),
                "report": row.get("report", ""),
                "error_code": "",
                "note": "",
            }
        b = buckets[key]
        b["stages"].append({
            "stage": stage,
            "ts": row.get("ts", ""),
            "artifact": row.get("artifact", ""),
            "note": row.get("note", ""),
        })
        # Keep latest artifact and report
        if row.get("artifact"):
            b["artifact"] = row["artifact"]
        if row.get("report"):
            b["report"] = row["report"]
        if row.get("error_code"):
            b["error_code"] = row["error_code"]
        if row.get("note") and stage in ("warn", "error"):
            b["note"] = row["note"]

    return buckets


def agent_status(b: Dict[str, Any]) -> str:
    """Determine status from stages."""
    stages = [s["stage"] for s in b["stages"]]
    if "error" in stages:
        return "ERROR"
    if "done" in stages:
        return "OK"
    if "start" in stages:
        return "IN-PROGRESS"
    return "UNKNOWN"


def elapsed(b: Dict[str, Any]) -> Optional[str]:
    """Compute elapsed time between first start and done/error."""
    starts = [s for s in b["stages"] if s["stage"] == "start"]
    ends = [s for s in b["stages"] if s["stage"] in TERMINAL]
    if not starts:
        return None
    t0 = parse_ts(starts[0]["ts"])
    if not t0:
        return None
    if not ends:
        return None
    t1 = parse_ts(ends[-1]["ts"])
    if not t1:
        return None
    delta = t1 - t0
    total_sec = int(delta.total_seconds())
    if total_sec < 60:
        return f"{total_sec}s"
    minutes, sec = divmod(total_sec, 60)
    return f"{minutes}m{sec:02d}s"


# ── Rendering ────────────────────────────────────────────────────────
STATUS_ICON = {"OK": "✅", "ERROR": "❌", "IN-PROGRESS": "⏳", "UNKNOWN": "❓"}
TASK_ORDER = {"team": 0, "sidequest": 1}


def render_text(buckets: Dict[tuple, Dict[str, Any]], run_id: str = "?") -> str:
    lines: List[str] = []
    lines.append(f"═" * 60)
    lines.append(f"  RUNPULSE — nightly-lab dashboard")
    lines.append(f"  Run: {run_id}")
    lines.append(f"═" * 60)

    # Sort: team tasks first, then sidequest; within each, by agent order
    sorted_keys = sorted(
        buckets.keys(),
        key=lambda k: (TASK_ORDER.get(k[1], 99), k[0])
    )

    # Separate team and sidequest
    team_buckets = [(k, buckets[k]) for k in sorted_keys if k[1] == "team"]
    sq_buckets = [(k, buckets[k]) for k in sorted_keys if k[1] == "sidequest"]

    if team_buckets:
        lines.append("")
        lines.append("── TEAM TASKS ──────────────────────────────────────")
        for key, b in team_buckets:
            status = agent_status(b)
            icon = STATUS_ICON.get(status, "?")
            time_str = elapsed(b) or "—"
            lines.append(f"  {icon} {b['agent']:<12} │ {status:<12} │ {time_str:>8}")
            if b["artifact"] and status == "OK":
                lines.append(f"     artifact: {b['artifact']}")
            if b["error_code"]:
                lines.append(f"     error: {b['error_code']}")
            if b["note"] and status != "OK":
                lines.append(f"     note: {b['note']}")

    if sq_buckets:
        lines.append("")
        lines.append("── SIDEQUESTS ──────────────────────────────────────")
        for key, b in sq_buckets:
            status = agent_status(b)
            icon = STATUS_ICON.get(status, "?")
            time_str = elapsed(b) or "—"
            lines.append(f"  {icon} {b['agent']:<12} │ {status:<12} │ {time_str:>8}")
            if b["artifact"] and status == "OK":
                lines.append(f"     artifact: {b['artifact']}")
            if b["error_code"]:
                lines.append(f"     error: {b['error_code']}")
            if b["note"]:
                lines.append(f"     note: {b['note']}")

    # Summary
    ok_count = sum(1 for b in buckets.values() if agent_status(b) == "OK")
    err_count = sum(1 for b in buckets.values() if agent_status(b) == "ERROR")
    wip_count = sum(1 for b in buckets.values() if agent_status(b) == "IN-PROGRESS")
    total = len(buckets)
    lines.append("")
    lines.append("── SUMMARY ─────────────────────────────────────────")
    lines.append(f"  Total tasks: {total}  │  ✅ {ok_count}  ❌ {err_count}  ⏳ {wip_count}")

    # Timing
    all_starts = []
    all_ends = []
    for b in buckets.values():
        for s in b["stages"]:
            if s["stage"] == "start":
                t = parse_ts(s["ts"])
                if t:
                    all_starts.append(t)
            if s["stage"] in TERMINAL:
                t = parse_ts(s["ts"])
                if t:
                    all_ends.append(t)

    if all_starts and all_ends:
        wall = max(all_ends) - min(all_starts)
        wall_sec = int(wall.total_seconds())
        if wall_sec >= 3600:
            hours, rem = divmod(wall_sec, 3600)
            mins, sec = divmod(rem, 60)
            wall_str = f"{hours}h{mins:02d}m{sec:02d}s"
        else:
            mins, sec = divmod(wall_sec, 60)
            wall_str = f"{mins}m{sec:02d}s"
        lines.append(f"  Wall clock:  {wall_str}")

    lines.append(f"═" * 60)
    return "\n".join(lines)


def render_compact(buckets: Dict[tuple, Dict[str, Any]], run_id: str = "?") -> str:
    lines: List[str] = []
    sorted_keys = sorted(
        buckets.keys(),
        key=lambda k: (TASK_ORDER.get(k[1], 99), k[0])
    )
    for key in sorted_keys:
        b = buckets[key]
        status = agent_status(b)
        icon = STATUS_ICON.get(status, "?")
        time_str = elapsed(b) or "—"
        art = Path(b["artifact"]).name if b["artifact"] and status == "OK" else ""
        lines.append(f"{icon} {run_id} {b['agent']}/{b['task']} {status} {time_str} {art}")
    return "\n".join(lines)


def render_json(buckets: Dict[tuple, Dict[str, Any]], run_id: str = "?") -> str:
    out = []
    for key, b in buckets.items():
        out.append({
            "run_id": run_id,
            "agent": b["agent"],
            "task": b["task"],
            "status": agent_status(b),
            "elapsed": elapsed(b),
            "artifact": b["artifact"],
            "report": b["report"],
            "error_code": b["error_code"],
            "stages": b["stages"],
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


# ── Main ─────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="runpulse — nightly-lab run dashboard")
    parser.add_argument("status_file", nargs="?", help="Path to status.jsonl")
    parser.add_argument("--date", help="Logical date YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--compact", action="store_true", help="One-line per agent")
    args = parser.parse_args()

    # Resolve status file
    if args.status_file:
        sf = Path(args.status_file)
        if not sf.exists():
            print(f"Error: {sf} not found", file=sys.stderr)
            return 1
    else:
        sf = find_status_file(args.date)
        if not sf:
            print("Error: No status.jsonl found. Specify --date or path.", file=sys.stderr)
            return 1

    rows = load_rows(sf)
    if not rows:
        print(f"Error: {sf} is empty or invalid", file=sys.stderr)
        return 1

    run_id = rows[0].get("run_id", "?") if rows else "?"
    buckets = build_agent_summary(rows)

    if args.json:
        print(render_json(buckets, run_id))
    elif args.compact:
        print(render_compact(buckets, run_id))
    else:
        print(render_text(buckets, run_id))

    # Exit 1 if any errors, 0 otherwise
    has_errors = any(agent_status(b) == "ERROR" for b in buckets.values())
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
