#!/usr/bin/env python3
"""run_status_brief.py

Audit a nightly-lab run for completeness and consistency.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_RUN = "/root/.openclaw/workspace/nightly-lab/current-run.json"
REQUIRED_STAGES = ("start", "artifact", "done")


class RunAuditError(Exception):
    """Raised for fatal run audit problems."""


JsonDict = Dict[str, Any]
Pair = Tuple[str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a nightly-lab run for completeness and consistency.")
    parser.add_argument(
        "--run",
        default=DEFAULT_RUN,
        help="Path to current-run.json or a run.json file (default: current-run.json)",
    )
    parser.add_argument(
        "--show-events",
        type=int,
        default=5,
        help="Show the last N parsed events (default: 5)",
    )
    return parser.parse_args()


def load_json(path: Path) -> JsonDict:
    if not path.exists():
        raise RunAuditError(f"JSON file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RunAuditError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RunAuditError(f"Expected a JSON object in {path}")
    return data


def load_jsonl(path: Path) -> Tuple[List[JsonDict], List[str]]:
    if not path.exists():
        raise RunAuditError(f"Status log not found: {path}")

    events: List[JsonDict] = []
    warnings: List[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"Malformed JSONL skipped at line {lineno}")
                continue
            if not isinstance(obj, dict):
                warnings.append(f"Non-object JSONL entry skipped at line {lineno}")
                continue
            obj["_lineno"] = lineno
            events.append(obj)

    return events, warnings


def expected_pairs(run: JsonDict) -> List[Pair]:
    pairs: List[Pair] = []
    agents = run.get("agents", {})
    if not isinstance(agents, dict):
        return pairs

    team_agents = agents.get("team", [])
    sidequest_agents = agents.get("sidequest", [])

    if isinstance(team_agents, list):
        for agent in team_agents:
            pairs.append((str(agent), "team"))
    if isinstance(sidequest_agents, list):
        for agent in sidequest_agents:
            pairs.append((str(agent), "sidequest"))
    return pairs


def build_pair_index(events: Iterable[JsonDict]) -> Tuple[Dict[Pair, List[JsonDict]], Dict[Pair, JsonDict]]:
    per_pair: Dict[Pair, List[JsonDict]] = defaultdict(list)
    latest: Dict[Pair, JsonDict] = {}
    for event in events:
        pair = (str(event.get("agent", "unknown")), str(event.get("task", "unknown")))
        per_pair[pair].append(event)
        latest[pair] = event
    return per_pair, latest


def last_nonempty_artifact(events: Iterable[JsonDict]) -> str:
    artifact = ""
    for event in events:
        value = str(event.get("artifact", "")).strip()
        if value:
            artifact = value
    return artifact


def check_report_paths(paths: Dict[str, Any], label: str) -> List[str]:
    warnings: List[str] = []
    for agent, raw_path in sorted(paths.items()):
        report_path = Path(str(raw_path))
        if not report_path.exists():
            warnings.append(f"Missing {label} report for {agent}: {report_path}")
    return warnings


def summarize_artifact_paths(events: Iterable[JsonDict]) -> Tuple[List[str], List[str]]:
    seen: List[str] = []
    warnings: List[str] = []
    dedup = set()
    for event in events:
        artifact = str(event.get("artifact", "")).strip()
        if not artifact or artifact in dedup:
            continue
        dedup.add(artifact)
        seen.append(artifact)
        if not Path(artifact).exists():
            warnings.append(f"Recorded artifact path does not exist: {artifact}")
    return seen, warnings


def format_stage_list(stages: Iterable[str]) -> str:
    clean = [stage for stage in stages if stage]
    return ", ".join(clean) if clean else "(none)"


def main() -> int:
    args = parse_args()

    try:
        run = load_json(Path(args.run))
    except RunAuditError as exc:
        print(f"ERROR: {exc}")
        return 2

    status_path = Path(str(run.get("status_file", "")).strip())
    if not str(status_path):
        print("ERROR: current run JSON is missing status_file")
        return 2

    try:
        events, parse_warnings = load_jsonl(status_path)
    except RunAuditError as exc:
        print(f"ERROR: {exc}")
        return 2

    per_pair, latest = build_pair_index(events)
    expected = expected_pairs(run)
    warnings: List[str] = list(parse_warnings)

    team_reports = run.get("team_reports", {})
    sidequest_reports = run.get("sidequest_reports", {})
    if isinstance(team_reports, dict):
        warnings.extend(check_report_paths(team_reports, "team"))
    if isinstance(sidequest_reports, dict):
        warnings.extend(check_report_paths(sidequest_reports, "sidequest"))

    artifact_paths, artifact_warnings = summarize_artifact_paths(events)
    warnings.extend(artifact_warnings)

    expected_set = set(expected)
    for pair in sorted(expected_set):
        pair_events = per_pair.get(pair, [])
        stages = {str(event.get("stage", "")).strip() for event in pair_events}
        missing = [stage for stage in REQUIRED_STAGES if stage not in stages]
        if missing:
            warnings.append(
                f"Missing stages for {pair[0]}/{pair[1]}: {', '.join(missing)}"
            )

    unexpected_pairs = sorted(set(per_pair) - expected_set)

    print("== Run Status Brief ==")
    print(f"run_id: {run.get('run_id', '')}")
    print(f"logical_date: {run.get('logical_date', '')}")
    print(f"run_root: {run.get('run_root', '')}")
    print(f"status_file: {status_path}")
    print()

    print("== Latest stage per (agent, task) ==")
    if not latest:
        print("- (no events)")
    else:
        for pair in sorted(latest):
            event = latest[pair]
            artifact = str(event.get("artifact", "")).strip() or "-"
            print(
                f"- {pair[0]}/{pair[1]}: {event.get('stage', '')} @ {event.get('ts', '')} | artifact={artifact}"
            )
    print()

    print("== Expected pair audit ==")
    if not expected:
        print("- No expected pairs declared in run JSON")
    else:
        for agent, task in sorted(expected_set):
            pair = (agent, task)
            pair_events = per_pair.get(pair, [])
            stages = [str(event.get("stage", "")).strip() for event in pair_events]
            artifact = last_nonempty_artifact(pair_events) or "-"
            missing = [stage for stage in REQUIRED_STAGES if stage not in set(stages)]
            status = "PASS" if not missing else f"WARN missing={','.join(missing)}"
            print(
                f"- {agent}/{task}: stages={format_stage_list(stages)} | latest_artifact={artifact} | {status}"
            )
    print()

    print("== Report files ==")
    for label, report_map in (("team", team_reports), ("sidequest", sidequest_reports)):
        if not isinstance(report_map, dict):
            print(f"- {label}: (missing report map)")
            continue
        for agent, raw_path in sorted(report_map.items()):
            path = Path(str(raw_path))
            state = "exists" if path.exists() else "MISSING"
            print(f"- {label}/{agent}: {state} | {path}")
    print()

    print("== Recorded artifact paths ==")
    if not artifact_paths:
        print("- (no artifact paths recorded)")
    else:
        for artifact in artifact_paths:
            state = "exists" if Path(artifact).exists() else "MISSING"
            print(f"- {state} | {artifact}")
    print()

    if unexpected_pairs:
        print("== Unexpected pairs in status log ==")
        for agent, task in unexpected_pairs:
            print(f"- {agent}/{task}")
        print()

    show_events = max(args.show_events, 0)
    print(f"== Last {show_events} events ==")
    if show_events == 0:
        print("- (disabled)")
    else:
        for event in events[-show_events:]:
            print(
                f"- line {event.get('_lineno')}: {event.get('ts', '')} | "
                f"{event.get('agent', '')}/{event.get('task', '')} | {event.get('stage', '')} | "
                f"report={event.get('report', '')} | artifact={event.get('artifact', '')}"
            )
    print()

    final_status = "PASS" if not warnings else "WARN"
    print(f"FINAL_STATUS: {final_status}")
    if warnings:
        print("WARNINGS:")
        for item in warnings:
            print(f"- {item}")

    return 0 if not warnings else 1


if __name__ == "__main__":
    sys.exit(main())
