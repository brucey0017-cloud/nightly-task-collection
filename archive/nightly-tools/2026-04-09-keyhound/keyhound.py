#!/usr/bin/env python3
"""keyhound: lightweight pattern-only secrets scanner (Python stdlib only)."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from typing import Dict, Iterable, List

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "vendor",
}

SKIP_FILE_EXACT = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".env.example",
    ".env.template",
}

SKIP_FILE_GLOBS = {
    "*.lock",
    "*.min.js",
    "*.min.css",
}

PATTERNS: List[Dict[str, re.Pattern[str]]] = [
    {
        "type": "aws_access_key",
        "regex": re.compile(r"AKIA[0-9A-Z]{16}"),
    },
    {
        "type": "github_token",
        "regex": re.compile(r"(?:ghp|gho|ghu|ghs)_[A-Za-z0-9_]{36,255}"),
    },
    {
        "type": "github_pat",
        "regex": re.compile(r"github_pat_[A-Za-z0-9_]{22}_[A-Za-z0-9_]{59}"),
    },
    {
        "type": "private_key_block",
        "regex": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    },
    {
        "type": "slack_token",
        "regex": re.compile(r"xox[boapr]-[A-Za-z0-9-]{10,}"),
    },
    {
        "type": "google_api_key",
        "regex": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    },
]


def redact(value: str) -> str:
    token = value.strip()
    if len(token) > 12:
        return f"{token[:8]}...{token[-4:]}"
    return "****"


def should_skip_file(name: str) -> bool:
    if name in SKIP_FILE_EXACT:
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in SKIP_FILE_GLOBS)


def is_binary_file(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
    except OSError:
        return True
    if b"\x00" in chunk:
        return True
    return False


def iter_files(target: str) -> Iterable[str]:
    if os.path.isfile(target):
        if not should_skip_file(os.path.basename(target)):
            yield target
        return

    for root, dirs, files in os.walk(target):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for filename in sorted(files):
            if should_skip_file(filename):
                continue
            yield os.path.join(root, filename)


def scan_file(path: str, display_path: str) -> List[Dict[str, object]]:
    findings: List[Dict[str, object]] = []
    if is_binary_file(path):
        return findings

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                for pattern in PATTERNS:
                    for match in pattern["regex"].finditer(line):
                        findings.append(
                            {
                                "file": display_path,
                                "line": line_no,
                                "type": pattern["type"],
                                "preview": redact(match.group(0)),
                            }
                        )
    except OSError:
        return findings

    findings.sort(key=lambda x: (x["line"], x["type"], x["preview"]))
    return findings


def collect_findings(target: str) -> List[Dict[str, object]]:
    target = os.path.abspath(target)
    is_dir = os.path.isdir(target)
    files = sorted(set(iter_files(target)))

    findings: List[Dict[str, object]] = []
    for file_path in files:
        display = (
            os.path.relpath(file_path, target) if is_dir else os.path.abspath(file_path)
        )
        findings.extend(scan_file(file_path, display))
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan files for likely leaked secrets.")
    parser.add_argument("path", help="File or directory to scan")
    parser.add_argument("--json", action="store_true", help="Output findings as JSON")
    parser.add_argument("--quiet", action="store_true", help="Output count only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not os.path.exists(args.path):
        print(f"Path not found: {args.path}", file=sys.stderr)
        return 2

    findings = collect_findings(args.path)
    count = len(findings)

    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    elif args.quiet:
        if count == 0:
            print("0 secrets found")
        else:
            print(f"{count} potential secrets found")
    else:
        for item in findings:
            print(f"{item['file']}:{item['line']}  [{item['type']}]  {item['preview']}")

        if count == 0:
            print("✅ 0 secrets found")
            print("exit=0 (clean)")
        else:
            print(f"🚨 {count} potential secrets found")
            print("exit=1 (findings)")

    return 1 if count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
