#!/usr/bin/env python3
"""Audit nightly-lab sidequest lifecycle contract from current-run.json + status.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_CURRENT_RUN = Path("/root/.openclaw/workspace/nightly-lab/current-run.json")
DEFAULT_TASK = "sidequest"
OK = "OK"
PENDING = "PENDING"
WARN = "WARN"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit nightly-lab sidequest lifecycle contract from current-run.json + status.jsonl."
    )
    parser.add_argument(
        "--current-run",
        default=str(DEFAULT_CURRENT_RUN),
        help="Path to current-run.json or a saved run.json (default: nightly-lab/current-run.json)",
    )
    parser.add_argument(
        "--agent",
        action="append",
        default=[],
        help="Only inspect one or more agents. Can be repeated.",
    )
    parser.add_argument(
        "--task",
        default=DEFAULT_TASK,
        help="Task name to inspect in status.jsonl (default: sidequest)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 1 when any agent is still pending/incomplete.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"non-object JSONL row at {path}:{line_number}")
            obj["_line"] = line_number
            rows.append(obj)
    return rows


def normalize_agents(raw_agents: list[str]) -> set[str]:
    return {agent.strip().lower() for agent in raw_agents if agent.strip()}


def path_exists(raw: str) -> bool:
    return bool(raw) and Path(raw).exists()


def under_root(raw: str, root: str) -> bool:
    if not raw or not root:
        return False
    try:
        Path(raw).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False
    except OSError:
        return False


def summarize_stages(events: list[dict[str, Any]]) -> str:
    return " -> ".join(str(event.get("stage", "")) for event in events) if events else "(none)"


def filter_events(
    events: list[dict[str, Any]], *, agent: str, task: str, run_id: str | None
) -> list[dict[str, Any]]:
    selected = []
    for event in events:
        if str(event.get("agent", "")).lower() != agent.lower():
            continue
        if str(event.get("task", "")) != task:
            continue
        if run_id and event.get("run_id") and str(event.get("run_id")) != run_id:
            continue
        selected.append(event)
    return selected


def first_stage_index(events: list[dict[str, Any]], stage: str) -> int | None:
    for index, event in enumerate(events):
        if event.get("stage") == stage:
            return index
    return None


def collect_stage(events: list[dict[str, Any]], stage: str) -> list[dict[str, Any]]:
    return [event for event in events if event.get("stage") == stage]


def last_nonempty(events: list[dict[str, Any]], field: str) -> str:
    for event in reversed(events):
        value = str(event.get(field, "") or "").strip()
        if value:
            return value
    return ""


def assess_agent(
    *,
    agent: str,
    task: str,
    events: list[dict[str, Any]],
    expected_report: str,
    artifact_root: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    notes: list[str] = []
    starts = collect_stage(events, "start")
    artifacts = collect_stage(events, "artifact")
    dones = collect_stage(events, "done")
    errors = collect_stage(events, "error")
    warns = collect_stage(events, "warn")
    terminals = dones + errors

    observed_reports = sorted(
        {str(event.get("report", "") or "") for event in events if str(event.get("report", "") or "").strip()}
    )
    observed_artifacts = sorted(
        {str(event.get("artifact", "") or "") for event in events if str(event.get("artifact", "") or "").strip()}
    )

    if not events:
        notes.append("no events yet")
    if len(starts) > 1:
        warnings.append(f"duplicate start stages: {len(starts)}")
    if len(artifacts) > 1:
        warnings.append(f"duplicate artifact stages: {len(artifacts)}")
    if len(terminals) > 1:
        warnings.append(
            "multiple terminal stages: "
            + ", ".join(str(event.get("stage", "")) for event in terminals)
        )
    if dones and errors:
        warnings.append("both done and error terminal stages present")
    if warns:
        notes.append(f"warn stages observed: {len(warns)}")

    start_index = first_stage_index(events, "start")
    artifact_index = first_stage_index(events, "artifact")
    done_index = first_stage_index(events, "done")
    error_index = first_stage_index(events, "error")
    terminal_index = min(
        [index for index in (done_index, error_index) if index is not None],
        default=None,
    )

    if artifact_index is not None and start_index is None:
        warnings.append("artifact stage exists without start stage")
    if artifact_index is not None and start_index is not None and artifact_index < start_index:
        warnings.append("artifact stage appears before start")
    if terminal_index is not None and artifact_index is None:
        warnings.append("terminal stage exists without artifact stage")
    if terminal_index is not None and start_index is None:
        warnings.append("terminal stage exists without start stage")
    if terminal_index is not None and start_index is not None and terminal_index < start_index:
        warnings.append("terminal stage appears before start")
    if terminal_index is not None and artifact_index is not None and terminal_index < artifact_index:
        warnings.append("terminal stage appears before artifact")

    if expected_report:
        if observed_reports:
            mismatches = [path for path in observed_reports if path != expected_report]
            if mismatches:
                warnings.append(
                    "report path mismatch vs current-run: " + ", ".join(mismatches)
                )
        if terminals and not path_exists(expected_report):
            warnings.append("expected report file missing after terminal stage")
        elif not path_exists(expected_report):
            notes.append("expected report file not written yet")
    elif observed_reports:
        warnings.append("status events include report path but current-run has no expected report")

    artifact_path = last_nonempty(events, "artifact")
    if artifacts:
        if not artifact_path:
            warnings.append("artifact stage exists without artifact path")
        else:
            if artifact_root and not under_root(artifact_path, artifact_root):
                warnings.append("artifact path is outside nightly_sidequests root")
            if not path_exists(artifact_path):
                warnings.append("artifact path does not exist")
    elif terminals:
        warnings.append("terminal stage exists without artifact stage")

    if len(set(observed_artifacts)) > 1:
        warnings.append("multiple distinct artifact paths recorded")

    if terminals and expected_report and path_exists(expected_report) and not artifact_path:
        warnings.append("terminal stage completed but no artifact path recorded")

    completed = bool(dones or errors)
    has_activity = bool(events)
    if warnings:
        status = WARN
    elif completed:
        status = OK
    elif has_activity:
        status = PENDING
    else:
        status = PENDING

    return {
        "agent": agent,
        "task": task,
        "status": status,
        "expected_report": expected_report,
        "expected_report_exists": path_exists(expected_report),
        "artifact_root": artifact_root,
        "artifact_path": artifact_path,
        "artifact_exists": path_exists(artifact_path),
        "artifact_under_root": under_root(artifact_path, artifact_root) if artifact_path and artifact_root else None,
        "events": events,
        "event_count": len(events),
        "stages": [str(event.get("stage", "")) for event in events],
        "stage_flow": summarize_stages(events),
        "observed_reports": observed_reports,
        "observed_artifacts": observed_artifacts,
        "warnings": warnings,
        "notes": notes,
        "completed": completed,
    }


def render_text(results: list[dict[str, Any]], strict: bool) -> str:
    counts = {OK: 0, PENDING: 0, WARN: 0}
    for result in results:
        counts[result["status"]] += 1

    lines: list[str] = []
    for result in results:
        lines.append(f"[{result['status']}] {result['agent']} :: {result['stage_flow']}")
        if result.get("expected_report"):
            report_state = "ok" if result.get("expected_report_exists") else "missing"
            lines.append(f"  report: {result['expected_report']} ({report_state})")
        if result.get("artifact_path"):
            artifact_bits = []
            artifact_bits.append("exists" if result.get("artifact_exists") else "missing")
            under_root_flag = result.get("artifact_under_root")
            if under_root_flag is True:
                artifact_bits.append("under-root")
            elif under_root_flag is False:
                artifact_bits.append("outside-root")
            lines.append(f"  artifact: {result['artifact_path']} ({', '.join(artifact_bits)})")
        elif result.get("observed_artifacts") == []:
            lines.append("  artifact: (none)")
        for warning in result.get("warnings", []):
            lines.append(f"  warn: {warning}")
        for note in result.get("notes", []):
            lines.append(f"  note: {note}")

    summary = f"SUMMARY OK={counts[OK]} PENDING={counts[PENDING]} WARN={counts[WARN]}"
    if strict:
        summary += " strict=on"
    lines.append(summary)
    return "\n".join(lines)


def exit_code(results: list[dict[str, Any]], strict: bool) -> int:
    if any(result["status"] == WARN for result in results):
        return 1
    if strict and any(result["status"] == PENDING for result in results):
        return 1
    return 0


def main() -> int:
    args = parse_args()
    try:
        current_run_path = Path(args.current_run)
        current_run = read_json(current_run_path)
        status_file = current_run.get("status_file")
        if not isinstance(status_file, str) or not status_file:
            raise ValueError("current-run is missing status_file")
        status_path = Path(status_file)
        if not status_path.exists():
            raise FileNotFoundError(f"status_file not found: {status_path}")
        events = read_jsonl(status_path)

        task = str(args.task)
        reports = current_run.get(f"{task}_reports")
        if not isinstance(reports, dict):
            raise ValueError(f"current-run is missing object field: {task}_reports")

        configured_agents = current_run.get("agents", {}).get(task)
        expected_agents = []
        if isinstance(configured_agents, list):
            expected_agents.extend(str(agent).lower() for agent in configured_agents)
        expected_agents.extend(str(agent).lower() for agent in reports.keys())
        deduped_agents = []
        seen = set()
        for agent in expected_agents:
            if agent not in seen:
                deduped_agents.append(agent)
                seen.add(agent)

        wanted_agents = normalize_agents(args.agent)
        selected_agents = [agent for agent in deduped_agents if not wanted_agents or agent in wanted_agents]
        if wanted_agents and not selected_agents:
            requested = ", ".join(sorted(wanted_agents))
            raise ValueError(f"no configured agents matched: {requested}")

        artifact_root = str(current_run.get("roots", {}).get("nightly_sidequests", "") or "")
        run_id = str(current_run.get("run_id", "") or "")
        results = []
        for agent in selected_agents:
            agent_events = filter_events(events, agent=agent, task=task, run_id=run_id or None)
            results.append(
                assess_agent(
                    agent=agent,
                    task=task,
                    events=agent_events,
                    expected_report=str(reports.get(agent, "") or ""),
                    artifact_root=artifact_root,
                )
            )

        payload = {
            "current_run": str(current_run_path),
            "run_id": run_id,
            "task": task,
            "strict": args.strict,
            "artifact_root": artifact_root,
            "results": results,
            "exit_code": exit_code(results, args.strict),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(render_text(results, args.strict))
        return int(payload["exit_code"])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "exit_code": 2}, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
