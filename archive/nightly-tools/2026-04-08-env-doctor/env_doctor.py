#!/usr/bin/env python3
"""env-doctor: lightweight .env health checker (stdlib only)."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PLACEHOLDERS = {"changeme", "xxx", "your-api-key-here", "todo"}
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]+$")
VALID_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}


@dataclass
class Issue:
    severity: str  # CRIT | WARN | INFO
    file: str
    line: Optional[int]
    why: str
    fix: str


def colorize(text: str, severity: str, no_color: bool) -> str:
    if no_color:
        return text
    colors = {
        "CRIT": "\033[31m",  # red
        "WARN": "\033[33m",  # yellow
        "INFO": "\033[36m",  # cyan
        "OK": "\033[32m",  # green
        "RESET": "\033[0m",
    }
    code = colors.get(severity, "")
    reset = colors["RESET"] if code else ""
    return f"{code}{text}{reset}"


def is_env_file(name: str) -> bool:
    return name == ".env" or name.startswith(".env.") or name == ".envrc"


def unquote(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
        return v[1:-1]
    return v


def is_quoted(value: str) -> bool:
    v = value.strip()
    return len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'"))


def find_env_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if is_env_file(fname):
                files.append(Path(dirpath) / fname)
    return sorted(files)


def analyze_file(path: Path, relpath: str) -> Tuple[List[Issue], List[Tuple[str, int]]]:
    issues: List[Issue] = []
    keys: List[Tuple[str, int]] = []

    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        issues.append(
            Issue(
                severity="WARN",
                file=relpath,
                line=None,
                why="File is not valid UTF-8 text.",
                fix="Re-save file as UTF-8 before scanning.",
            )
        )
        return issues, keys

    for idx, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if "=" not in raw:
            issues.append(
                Issue(
                    severity="WARN",
                    file=relpath,
                    line=idx,
                    why="Missing '=' assignment syntax.",
                    fix="Use KEY=value format.",
                )
            )
            continue

        left, right = raw.split("=", 1)
        key = left.strip()
        value = right.strip()

        if not key:
            issues.append(
                Issue(
                    severity="WARN",
                    file=relpath,
                    line=idx,
                    why="Empty key name.",
                    fix="Provide a valid env var key (e.g. API_KEY=value).",
                )
            )
            continue

        if not VALID_KEY_RE.match(key):
            issues.append(
                Issue(
                    severity="WARN",
                    file=relpath,
                    line=idx,
                    why=f"Suspicious key format '{key}'.",
                    fix="Use shell-safe key names: letters/numbers/underscore.",
                )
            )

        keys.append((key, idx))

        if value == "":
            sev = "CRIT" if is_required_looking_key(key) else "WARN"
            issues.append(
                Issue(
                    severity=sev,
                    file=relpath,
                    line=idx,
                    why=f"{key} has an empty value.",
                    fix=f"Set {key} to a real value or remove it if unused.",
                )
            )
            continue

        unquoted = unquote(value)
        if unquoted.strip().lower() in PLACEHOLDERS:
            issues.append(
                Issue(
                    severity="WARN",
                    file=relpath,
                    line=idx,
                    why=f"{key} uses placeholder value '{unquoted}'.",
                    fix="Replace placeholder with a real secret/config value.",
                )
            )

        if re.search(r"\s", value) and not is_quoted(value):
            issues.append(
                Issue(
                    severity="WARN",
                    file=relpath,
                    line=idx,
                    why=f"{key} has spaces in an unquoted value.",
                    fix=f"Wrap value with quotes, e.g. {key}=\"...\".",
                )
            )

        if PRIVATE_KEY_RE.search(unquoted):
            issues.append(
                Issue(
                    severity="CRIT",
                    file=relpath,
                    line=idx,
                    why=f"{key} looks like a private key material leak.",
                    fix="Move key material to secure storage and rotate compromised keys.",
                )
            )
        elif len(unquoted) > 200 and BASE64_RE.fullmatch(unquoted):
            issues.append(
                Issue(
                    severity="CRIT",
                    file=relpath,
                    line=idx,
                    why=f"{key} is a long base64-like secret candidate (>200 chars).",
                    fix="Verify this secret belongs in env; rotate if accidentally exposed.",
                )
            )

    return issues, keys


def is_required_looking_key(key: str) -> bool:
    upper = key.upper()
    hints = [
        "KEY",
        "TOKEN",
        "SECRET",
        "PASSWORD",
        "PASS",
        "URL",
        "URI",
        "HOST",
        "DATABASE",
        "DB",
        "USER",
        "USERNAME",
        "PORT",
        "DSN",
    ]
    return any(h in upper for h in hints)


def group_counts(issues: List[Issue]) -> Dict[str, int]:
    counts = {"CRIT": 0, "WARN": 0, "INFO": 0}
    for item in issues:
        if item.severity in counts:
            counts[item.severity] += 1
    return counts


def print_banner(files_count: int, issues: List[Issue], elapsed: float, no_color: bool) -> None:
    counts = group_counts(issues)
    if counts["CRIT"] > 0:
        title = "❌ Env 有风险 (Critical issues found)"
        tone = "CRIT"
        next_step = "先修复 [CRIT] 项，再处理 [WARN]。"
    elif counts["WARN"] > 0:
        title = "⚠️ Env 有风险 (Warnings found)"
        tone = "WARN"
        next_step = "优先处理高频或共享环境的 [WARN] 项。"
    else:
        title = "✅ Env 健康 (No issues found)"
        tone = "OK"
        next_step = "当前无风险项，可继续开发/部署。"

    print(colorize(title, tone, no_color))
    print(
        f"Scanned {files_count} env file(s) in {elapsed:.2f}s | "
        f"CRIT={counts['CRIT']} WARN={counts['WARN']} INFO={counts['INFO']}"
    )
    print(f"Next: {next_step}")


def print_issues(issues: List[Issue], no_color: bool) -> None:
    by_severity: Dict[str, List[Issue]] = {"CRIT": [], "WARN": [], "INFO": []}
    for issue in issues:
        by_severity.setdefault(issue.severity, []).append(issue)

    for sev in ["CRIT", "WARN", "INFO"]:
        bucket = by_severity.get(sev, [])
        if not bucket:
            continue
        print()
        print(colorize(f"[{sev}] {len(bucket)} issue(s)", sev, no_color))
        for it in bucket:
            loc = f"{it.file}:{it.line}" if it.line else it.file
            print(f"- [{sev}] {loc} — Why: {it.why} | Fix: {it.fix}")


def print_summary_table(files: List[str], issues: List[Issue]) -> None:
    counter: Dict[str, Dict[str, int]] = {f: {"CRIT": 0, "WARN": 0, "INFO": 0} for f in files}
    for issue in issues:
        if issue.file in counter and issue.severity in counter[issue.file]:
            counter[issue.file][issue.severity] += 1

    if not files:
        return

    path_w = max(len("File"), max(len(p) for p in files))
    print()
    print("Per-file summary")
    print(f"{'File'.ljust(path_w)}  CRIT  WARN  INFO")
    print(f"{'-' * path_w}  ----  ----  ----")
    for f in files:
        c = counter[f]
        print(f"{f.ljust(path_w)}  {str(c['CRIT']).rjust(4)}  {str(c['WARN']).rjust(4)}  {str(c['INFO']).rjust(4)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan .env files and report health risks.")
    parser.add_argument("path", nargs="?", default=".", help="Root path to scan (default: current directory)")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"[CRIT] Path does not exist: {root}")
        return 1

    started = time.time()
    env_files = find_env_files(root)

    all_issues: List[Issue] = []
    key_occurrences: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    rel_files: List[str] = []

    for fpath in env_files:
        rel = os.path.relpath(fpath, root)
        rel_files.append(rel)
        issues, keys = analyze_file(fpath, rel)
        all_issues.extend(issues)
        for key, line in keys:
            key_occurrences[key].append((rel, line))

    for key, occ in key_occurrences.items():
        files = sorted({f for f, _ in occ})
        if len(files) > 1:
            places = ", ".join(files)
            all_issues.append(
                Issue(
                    severity="WARN",
                    file=files[0],
                    line=None,
                    why=f"Key '{key}' is duplicated across files: {places}.",
                    fix="Keep one source of truth per environment and document override order.",
                )
            )

    elapsed = time.time() - started
    print_banner(len(env_files), all_issues, elapsed, args.no_color)
    if all_issues:
        print_issues(all_issues, args.no_color)
    print_summary_table(rel_files, all_issues)

    if not env_files:
        print("\n[INFO] No .env/.env.*/.envrc files found under target path.")

    crit_count = sum(1 for i in all_issues if i.severity == "CRIT")
    return 1 if crit_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
