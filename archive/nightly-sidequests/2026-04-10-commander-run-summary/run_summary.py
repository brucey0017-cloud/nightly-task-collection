#!/usr/bin/env python3
"""
nightly-lab run-summary — Quick status reporter for nightly-lab runs.

Reads a nightly-lab run directory and produces a human-readable summary
of team reports, sidequest status, and overall completion.

Usage:
    python3 run_summary.py [RUN_DIR]

    RUN_DIR defaults to the latest run under nightly-lab/runs/.

Zero dependencies — stdlib only.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

NIGHTLY_LAB = Path(os.environ.get(
    "NIGHTLY_LAB_ROOT",
    "/root/.openclaw/workspace/nightly-lab"
))

STAGE_ORDER = ["start", "artifact", "done"]
STAGE_ICONS = {"start": "▶", "artifact": "📦", "done": "✅", "error": "❌"}


def find_latest_run() -> Path:
    runs_dir = NIGHTLY_LAB / "runs"
    if not runs_dir.exists():
        print("No runs directory found.", file=sys.stderr)
        sys.exit(1)
    run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], reverse=True)
    if not run_dirs:
        print("No run directories found.", file=sys.stderr)
        sys.exit(1)
    return run_dirs[0]


def load_run_meta(run_dir: Path) -> dict:
    """Load current-run.json from the nightly-lab root (not inside run_dir)."""
    meta_path = NIGHTLY_LAB / "current-run.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    # Fallback: reconstruct from run_dir
    run_json = run_dir / "run.json"
    if run_json.exists():
        return json.loads(run_json.read_text())
    return {}


def parse_status_file(run_dir: Path) -> list[dict]:
    """Parse status.jsonl into a list of entries."""
    status_path = run_dir / "status.jsonl"
    entries = []
    if not status_path.exists():
        return entries
    for line in status_path.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


def parse_done_file(run_dir: Path) -> dict:
    """Parse done.json if it exists."""
    done_path = run_dir / "done.json"
    if done_path.exists():
        return json.loads(done_path.read_text())
    return {}


def agent_status_from_entries(entries: list[dict], agent: str) -> dict:
    """Extract the latest stage for a given agent from status entries."""
    latest = {"stage": None, "timestamp": None, "artifact": None, "error": None}
    for e in entries:
        if e.get("agent") != agent:
            continue
        ts = e.get("timestamp", "")
        if latest["timestamp"] is None or ts > latest["timestamp"]:
            latest["timestamp"] = ts
            latest["stage"] = e.get("stage")
            latest["artifact"] = e.get("artifact")
            latest["error"] = e.get("error_code")
    return latest


def file_exists_and_size(path: str) -> str:
    """Return size info for a file if it exists."""
    p = Path(path)
    if p.exists():
        size = p.stat().st_size
        if size > 1024:
            return f"{size / 1024:.1f}KB"
        return f"{size}B"
    return "—"


def build_summary(run_dir: Path) -> str:
    meta = load_run_meta(run_dir)
    entries = parse_status_file(run_dir)
    done = parse_done_file(run_dir)

    run_id = meta.get("run_id", run_dir.name)
    logical_date = meta.get("logical_date", run_dir.name)
    created_at = meta.get("created_at", "—")

    lines = []
    lines.append(f"╔══════════════════════════════════════════╗")
    lines.append(f"║  Nightly Lab Run Summary                 ║")
    lines.append(f"╚══════════════════════════════════════════╝")
    lines.append(f"")
    lines.append(f"  Run ID:       {run_id}")
    lines.append(f"  Logical Date: {logical_date}")
    lines.append(f"  Created:      {created_at}")
    lines.append(f"")

    # Team reports
    team_reports = meta.get("team_reports", {})
    team_agents = meta.get("agents", {}).get("team", [])
    lines.append(f"┌─ Team Reports ──────────────────────────┐")
    for agent in team_agents:
        report_path = team_reports.get(agent, "")
        size_str = file_exists_and_size(report_path)
        status = parse_status_from_entries(entries, agent, "team")
        icon = STAGE_ICONS.get(status["stage"], "·")
        lines.append(f"│ {icon} {agent:<12} {status['stage'] or 'pending':<8} {size_str:>8}")
    lines.append(f"└──────────────────────────────────────────┘")
    lines.append(f"")

    # Sidequest reports
    sq_reports = meta.get("sidequest_reports", {})
    sq_agents = meta.get("agents", {}).get("sidequest", [])
    lines.append(f"┌─ Sidequests ────────────────────────────┐")
    for agent in sq_agents:
        report_path = sq_reports.get(agent, "")
        size_str = file_exists_and_size(report_path)
        status = agent_status_from_entries(entries, agent)
        icon = STAGE_ICONS.get(status["stage"], "·")
        extra = ""
        if status.get("error"):
            extra = f" ERR: {status['error']}"
        lines.append(f"│ {icon} {agent:<12} {status['stage'] or 'pending':<8} {size_str:>8}{extra}")
    lines.append(f"└──────────────────────────────────────────┘")
    lines.append(f"")

    # Overall stats
    total_agents = len(team_agents) + len(sq_agents)
    team_done = sum(1 for a in team_agents if parse_status_from_entries(entries, a, "team")["stage"] == "done")
    sq_done = sum(1 for a in sq_agents if agent_status_from_entries(entries, a)["stage"] == "done")
    errors = sum(1 for e in entries if e.get("stage") == "error")

    lines.append(f"  Team done:     {team_done}/{len(team_agents)}")
    lines.append(f"  Sidequest done: {sq_done}/{len(sq_agents)}")
    if errors:
        lines.append(f"  Errors:        {errors}")
    if done:
        lines.append(f"  Run finished:  {done.get('finished_at', 'yes')}")
    lines.append(f"")

    return "\n".join(lines)


def parse_status_from_entries(entries: list[dict], agent: str, task: str) -> dict:
    """Extract the latest stage for a given agent+task from status entries."""
    latest = {"stage": None, "timestamp": None}
    for e in entries:
        if e.get("agent") != agent or e.get("task") != task:
            continue
        ts = e.get("timestamp", "")
        if latest["timestamp"] is None or ts > latest["timestamp"]:
            latest["timestamp"] = ts
            latest["stage"] = e.get("stage")
    return latest


def main():
    if len(sys.argv) > 1:
        run_dir = Path(sys.argv[1])
        if not run_dir.exists():
            print(f"Run directory not found: {run_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        run_dir = find_latest_run()

    print(build_summary(run_dir))


if __name__ == "__main__":
    main()
