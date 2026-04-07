#!/usr/bin/env python3
"""
nightly_status_briefing.py — One-page strategic briefing for nightly-lab runs.

Usage:
    python3 nightly_status_briefing.py [--run YYYY-MM-DD] [--json] [--watch]

Reads the nightly-lab run directory and produces a condensed status report
suitable for commander review: agent progress, timing, blockers, completion %.
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

LAB_ROOT = Path("/root/.openclaw/workspace/nightly-lab")

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_jsonl(path):
    entries = []
    try:
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except FileNotFoundError:
        pass
    return entries


def fmt_time(iso_str):
    """Parse ISO timestamp, return HH:MM UTC."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M")
    except Exception:
        return iso_str[:16] if len(iso_str) > 16 else iso_str


def fmt_duration(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    m = seconds / 60
    if m < 60:
        return f"{m:.1f}m"
    h = m / 60
    return f"{h:.1f}h"


# ── Core Logic ───────────────────────────────────────────────────────────────

def collect_run_data(run_id):
    """Gather all data for a given run_id."""
    run_dir = LAB_ROOT / "runs" / run_id
    run_json = load_json(run_dir / "run.json")
    status_events = load_jsonl(run_dir / "status.jsonl")
    done_json = load_json(run_dir / "done.json")

    # Read reports existence
    reports = {}
    if run_json:
        for role, rpath in run_json.get("team_reports", {}).items():
            reports[f"team.{role}"] = Path(rpath).exists()
        for role, rpath in run_json.get("sidequest_reports", {}).items():
            reports[f"sidequest.{role}"] = Path(rpath).exists()

    return {
        "run_json": run_json,
        "status_events": status_events,
        "done_json": done_json,
        "reports": reports,
    }


def build_agent_summary(events):
    """Build per-agent summary from status events."""
    agents = {}
    for ev in events:
        agent = ev.get("agent", "?")
        stage = ev.get("stage", "?")
        ts = ev.get("ts", "")
        task = ev.get("task", "?")

        if agent not in agents:
            agents[agent] = {"events": [], "tasks": {}}
        agents[agent]["events"].append(ev)

        if task not in agents[agent]["tasks"]:
            agents[agent]["tasks"][task] = {"stages": [], "started": None, "finished": None, "artifact": None}

        t = agents[agent]["tasks"][task]
        t["stages"].append({"stage": stage, "ts": ts})
        if stage == "start" and not t["started"]:
            t["started"] = ts
        if stage in ("done", "error"):
            t["finished"] = ts
            t["final_status"] = stage
        if stage == "artifact":
            t["artifact"] = ev.get("artifact")

    return agents


def render_briefing(run_id, data, as_json=False):
    """Render the briefing. Returns string or JSON dict."""
    run_json = data["run_json"]
    events = data["status_events"]
    done_json = data["done_json"]
    reports = data["reports"]

    agents = build_agent_summary(events)

    # ── JSON output ──
    if as_json:
        result = {
            "run_id": run_id,
            "logical_date": run_json.get("logical_date") if run_json else run_id,
            "run_complete": done_json is not None,
            "agents": {},
        }
        for agent, info in sorted(agents.items()):
            result["agents"][agent] = {
                "tasks": info["tasks"],
                "event_count": len(info["events"]),
            }
        result["reports"] = reports
        return json.dumps(result, indent=2, ensure_ascii=False)

    # ── Text output ──
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    lines.append("=" * 60)
    lines.append(f"  NIGHTLY LAB BRIEFING — {run_id}")
    lines.append(f"  Generated: {now_utc}")
    lines.append("=" * 60)
    lines.append("")

    # Overall status
    if done_json:
        lines.append(f"  STATUS: COMPLETE ✓")
        if "completed_at" in done_json:
            lines.append(f"  Finished: {done_json['completed_at'][:19]}")
    else:
        lines.append(f"  STATUS: IN PROGRESS ⏳")
    lines.append("")

    # Per-agent breakdown
    lines.append("─" * 60)
    lines.append("  AGENT STATUS")
    lines.append("─" * 60)

    stage_order = {"start": 1, "artifact": 2, "done": 3, "error": 3}
    stage_icons = {"start": "▶", "artifact": "📦", "done": "✓", "error": "✗"}

    for agent in sorted(agents.keys()):
        info = agents[agent]
        lines.append("")
        lines.append(f"  [{agent.upper()}]")

        for task_name, task_info in sorted(info["tasks"].items()):
            stages = task_info["stages"]
            final = task_info.get("final_status", "running")
            started = task_info.get("started", "")
            finished = task_info.get("finished", "")
            artifact = task_info.get("artifact", "")

            icon = stage_icons.get(final, "…")
            lines.append(f"    {icon} {task_name}: {final}")

            if started:
                lines.append(f"      Started: {fmt_time(started)}")
            if finished:
                lines.append(f"      Finished: {fmt_time(finished)}")
                # Duration
                try:
                    t1 = datetime.fromisoformat(started)
                    t2 = datetime.fromisoformat(finished)
                    lines.append(f"      Duration: {fmt_duration((t2 - t1).total_seconds())}")
                except Exception:
                    pass
            if artifact:
                lines.append(f"      Artifact: {artifact}")

    # Report status
    lines.append("")
    lines.append("─" * 60)
    lines.append("  REPORT FILES")
    lines.append("─" * 60)

    for rname, exists in sorted(reports.items()):
        icon = "✓" if exists else "—"
        lines.append(f"    {icon} {rname}")

    lines.append("")
    lines.append("=" * 60)

    # Quick stats
    total_agents = len(agents)
    tasks_done = sum(
        1 for a in agents.values()
        for t in a["tasks"].values()
        if t.get("final_status") == "done"
    )
    tasks_total = sum(len(a["tasks"]) for a in agents.values())
    tasks_error = sum(
        1 for a in agents.values()
        for t in a["tasks"].values()
        if t.get("final_status") == "error"
    )

    lines.append(f"  Tasks: {tasks_done}/{tasks_total} done"
                 + (f", {tasks_error} error(s)" if tasks_error else ""))
    lines.append(f"  Agents active: {total_agents}")
    lines.append("=" * 60)

    return "\n".join(lines)


def watch_mode(run_id, interval=30):
    """Continuously print briefing, clearing screen each cycle."""
    import time
    while True:
        data = collect_run_data(run_id)
        os.system("clear" if os.name == "posix" else "cls")
        print(render_briefing(run_id, data))
        print(f"\n  [Refreshing every {interval}s — Ctrl+C to stop]")
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n  Stopped.")
            break


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nightly Lab Status Briefing")
    parser.add_argument("--run", help="Run ID (default: today's run)", default=None)
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--watch", action="store_true", help="Auto-refresh mode")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval (seconds)")
    args = parser.parse_args()

    # Determine run_id
    run_id = args.run
    if not run_id:
        # Try current-run.json
        current = load_json(LAB_ROOT / "current-run.json")
        if current:
            run_id = current.get("run_id")
        if not run_id:
            run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.watch:
        watch_mode(run_id, args.interval)
        return

    data = collect_run_data(run_id)
    print(render_briefing(run_id, data, as_json=args.json))


if __name__ == "__main__":
    main()
