#!/usr/bin/env python3
"""Validate and optionally smoke-test nightly sidequest reports."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_CURRENT_RUN = Path("/root/.openclaw/workspace/nightly-lab/current-run.json")
SEPARATORS = (" — ", " – ", " - ")
CODE_SPAN_RE = re.compile(r"`([^`]+)`")
TOP_BULLET_RE = re.compile(r"^-\s+([^:]+):\s*(.*)$")
NESTED_BULLET_RE = re.compile(r"^\s+-\s+(.*)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate nightly-lab sidequest reports and optionally run their smoke tests."
    )
    parser.add_argument(
        "--current-run",
        default=str(DEFAULT_CURRENT_RUN),
        help="Path to current-run.json (default: nightly-lab/current-run.json)",
    )
    parser.add_argument(
        "--report",
        action="append",
        default=[],
        help="Explicit report path(s). Can be repeated.",
    )
    parser.add_argument(
        "--agent",
        action="append",
        default=[],
        help="Only include one or more agents from sidequest_reports.",
    )
    parser.add_argument("--list", action="store_true", help="List selected reports and exit.")
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run extracted test command(s) with bash -lc.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Per-test timeout in seconds when --run-tests is used (default: 60).",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize_key(raw: str) -> str:
    key = raw.strip().lower()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    return key.strip("_")


def strip_wrapping_code(text: str) -> str:
    value = text.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1].strip()
    return value


def first_code_span(text: str) -> str | None:
    match = CODE_SPAN_RE.search(text)
    return match.group(1).strip() if match else None


def parse_report(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    data: dict[str, Any] = {"raw_lines": len(lines), "files": []}
    i = 0
    while i < len(lines):
        line = lines[i]
        top = TOP_BULLET_RE.match(line)
        if not top:
            i += 1
            continue
        key_raw, value_raw = top.groups()
        key = normalize_key(key_raw)
        value = strip_wrapping_code(value_raw)
        if key == "files":
            items: list[str] = []
            j = i + 1
            while j < len(lines):
                nested = NESTED_BULLET_RE.match(lines[j])
                if nested:
                    items.append(nested.group(1).rstrip())
                    j += 1
                    continue
                if TOP_BULLET_RE.match(lines[j]):
                    break
                if not lines[j].strip():
                    j += 1
                    continue
                break
            data["files"] = items
            i = j
            continue
        data[key] = value
        i += 1
    return data


def extract_path_hint(raw: str) -> str:
    code = first_code_span(raw)
    if code:
        return code
    cleaned = raw.strip()
    for separator in SEPARATORS:
        if separator in cleaned:
            cleaned = cleaned.split(separator, 1)[0].strip()
            break
    return strip_wrapping_code(cleaned)


def resolve_file_path(raw: str, folder: Path | None, report_path: Path) -> Path:
    hint = extract_path_hint(raw)
    candidate = Path(hint)
    if candidate.is_absolute():
        return candidate
    if folder is not None:
        return folder / candidate
    return report_path.parent / candidate


def load_selected_reports(args: argparse.Namespace) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    if args.report:
        selected = [{"agent": "explicit", "path": path} for path in args.report]
        return selected, None

    current_run_path = Path(args.current_run)
    if not current_run_path.exists():
        raise FileNotFoundError(f"current-run file not found: {current_run_path}")

    current_run = read_json(current_run_path)
    sidequest_reports = current_run.get("sidequest_reports")
    if not isinstance(sidequest_reports, dict):
        raise ValueError("current-run.json is missing object field: sidequest_reports")

    allowed_agents = {agent.lower() for agent in args.agent}
    selected = []
    for agent, path in sidequest_reports.items():
        if allowed_agents and agent.lower() not in allowed_agents:
            continue
        selected.append({"agent": agent, "path": path})

    if allowed_agents and not selected:
        requested = ", ".join(sorted(allowed_agents))
        raise ValueError(f"no sidequest reports matched requested agent(s): {requested}")

    return selected, current_run


def validate_report(agent: str, report_path: Path, run_tests: bool, timeout: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "agent": agent,
        "report_path": str(report_path),
        "warnings": [],
        "errors": [],
        "validation": {},
        "test": {"status": "not-run"},
    }

    if not report_path.exists():
        result["warnings"].append("report file is missing")
        result["status"] = "WARN"
        return result

    try:
        parsed = parse_report(report_path)
    except OSError as exc:
        result["errors"].append(f"failed to read report: {exc}")
        result["status"] = "ERROR"
        return result
    except Exception as exc:  # defensive
        result["errors"].append(f"failed to parse report: {exc}")
        result["status"] = "ERROR"
        return result

    result["parsed"] = parsed

    folder_value = parsed.get("folder", "")
    folder_path: Path | None = None
    if folder_value:
        folder_path = Path(folder_value)
        if not folder_path.is_absolute():
            folder_path = report_path.parent / folder_path
        result["validation"]["folder"] = {
            "path": str(folder_path),
            "exists": folder_path.exists(),
            "is_dir": folder_path.is_dir(),
        }
        if not folder_path.exists():
            result["warnings"].append("declared folder does not exist")
        elif not folder_path.is_dir():
            result["warnings"].append("declared folder is not a directory")
    else:
        result["warnings"].append("missing Folder field")

    files_raw = parsed.get("files") or []
    files_checked = []
    if files_raw:
        for raw in files_raw:
            resolved = resolve_file_path(raw, folder_path, report_path)
            exists = resolved.exists()
            files_checked.append({
                "raw": raw,
                "path": str(resolved),
                "exists": exists,
            })
            if not exists:
                result["warnings"].append(f"listed file missing: {resolved}")
    else:
        result["warnings"].append("missing Files list")
    result["validation"]["files"] = files_checked

    test_command = parsed.get("test_command", "")
    result["validation"]["test_command"] = test_command
    if not test_command:
        result["warnings"].append("missing Test command field")

    status_value = parsed.get("status", "")
    if not status_value:
        result["warnings"].append("missing Status field")
    result["validation"]["status_field"] = status_value

    if run_tests and test_command:
        started = time.time()
        cwd = str(folder_path) if folder_path and folder_path.is_dir() else str(report_path.parent)
        try:
            completed = subprocess.run(
                ["bash", "-lc", test_command],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = round(time.time() - started, 3)
            result["test"] = {
                "status": "pass" if completed.returncode == 0 else "fail",
                "command": test_command,
                "cwd": cwd,
                "timeout_seconds": timeout,
                "duration_seconds": duration,
                "exit_code": completed.returncode,
                "stdout_tail": completed.stdout[-1200:],
                "stderr_tail": completed.stderr[-1200:],
            }
            if completed.returncode != 0:
                result["warnings"].append(f"test command failed with exit code {completed.returncode}")
        except subprocess.TimeoutExpired as exc:
            duration = round(time.time() - started, 3)
            result["test"] = {
                "status": "fail",
                "command": test_command,
                "cwd": cwd,
                "timeout_seconds": timeout,
                "duration_seconds": duration,
                "exit_code": None,
                "stdout_tail": (exc.stdout or "")[-1200:] if isinstance(exc.stdout, str) else "",
                "stderr_tail": (exc.stderr or "")[-1200:] if isinstance(exc.stderr, str) else "",
                "error": f"timed out after {timeout} seconds",
            }
            result["warnings"].append(f"test command timed out after {timeout} seconds")
        except OSError as exc:
            result["errors"].append(f"failed to execute test command: {exc}")

    if result["errors"]:
        result["status"] = "ERROR"
    elif result["warnings"]:
        if result["test"].get("status") == "fail":
            result["status"] = "FAIL"
        else:
            result["status"] = "WARN"
    else:
        result["status"] = "OK"

    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"OK": 0, "WARN": 0, "FAIL": 0, "ERROR": 0}
    for result in results:
        counts[result.get("status", "ERROR")] = counts.get(result.get("status", "ERROR"), 0) + 1
    return counts


def determine_exit_code(results: list[dict[str, Any]]) -> int:
    if any(result.get("status") == "ERROR" for result in results):
        return 2
    if any(result.get("status") in {"WARN", "FAIL"} for result in results):
        return 1
    return 0


def render_text_listing(selected: list[dict[str, str]]) -> str:
    lines = []
    for item in selected:
        lines.append(f"{item['agent']}\t{item['path']}")
    return "\n".join(lines)


def render_text_results(results: list[dict[str, Any]], counts: dict[str, int]) -> str:
    lines = []
    for result in results:
        lines.append(f"[{result['status']}] {result['agent']} :: {result['report_path']}")
        validation = result.get("validation", {})
        folder = validation.get("folder")
        if folder:
            lines.append(
                f"  folder: {folder['path']} ({'ok' if folder['exists'] and folder['is_dir'] else 'missing'})"
            )
        files = validation.get("files", [])
        if files:
            present = sum(1 for item in files if item["exists"])
            lines.append(f"  files: {present}/{len(files)} present")
        elif validation.get("files") == []:
            lines.append("  files: 0 listed")
        test = result.get("test", {})
        if test.get("status") == "not-run":
            lines.append(
                "  test: not run"
                + (" (missing command)" if not validation.get("test_command") else "")
            )
        else:
            extra = f", exit={test.get('exit_code')}" if test.get("exit_code") is not None else ""
            lines.append(
                f"  test: {test.get('status')} in {test.get('duration_seconds')}s{extra}"
            )
        for warning in result.get("warnings", []):
            lines.append(f"  warn: {warning}")
        for error in result.get("errors", []):
            lines.append(f"  error: {error}")
    lines.append(
        "SUMMARY " + " ".join(f"{key}={value}" for key, value in counts.items())
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        selected, current_run = load_selected_reports(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {"error": str(exc), "exit_code": 2}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.list:
        output = {
            "reports": selected,
            "current_run": current_run,
        }
        if args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(render_text_listing(selected))
        return 0

    results = [
        validate_report(item["agent"], Path(item["path"]), args.run_tests, args.timeout)
        for item in selected
    ]
    counts = summarize(results)
    exit_code = determine_exit_code(results)
    payload = {
        "current_run": args.current_run if not args.report else None,
        "selected_reports": selected,
        "run_tests": args.run_tests,
        "timeout_seconds": args.timeout,
        "counts": counts,
        "results": results,
        "exit_code": exit_code,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text_results(results, counts))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
