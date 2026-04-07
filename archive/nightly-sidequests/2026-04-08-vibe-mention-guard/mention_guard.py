#!/usr/bin/env python3
"""
Discord alias mention guard.

Detects lines that contain team aliases/titles but miss the required <@USER_ID>
mention in the same line.

Exit codes:
- 0: no violations
- 1: violations found
- 2: invalid usage / file read error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

RULES: Dict[str, Dict[str, Sequence[str]]] = {
    "commander": {
        "required_id": "1470262775006625990",
        "aliases": ["指挥官", "战略指挥官", "commander", "COMMANDER"],
    },
    "maker": {
        "required_id": "1470705448343830539",
        "aliases": ["首席技术", "首席技术官", "maker", "MAKER"],
    },
    "vibe": {
        "required_id": "1470708702116974761",
        "aliases": ["灵魂设计师", "首席体验官", "vibe", "VIBE"],
    },
    "killjoy": {
        "required_id": "1470710750912970915",
        "aliases": ["大反派", "首席质疑官", "killjoy", "KILLJOY"],
    },
    "main": {
        "required_id": "1476127054469533748",
        "aliases": ["阿爪", "main", "MAIN"],
    },
}

MENTION_RE = re.compile(r"<@\d+>")


def compile_alias_patterns() -> List[Tuple[str, str, re.Pattern[str]]]:
    rows: List[Tuple[str, str, re.Pattern[str]]] = []
    for owner, spec in RULES.items():
        required_id = spec["required_id"]
        for alias in spec["aliases"]:
            # ASCII aliases should match on word boundaries.
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", alias):
                pattern = re.compile(rf"\b{re.escape(alias)}\b")
            else:
                pattern = re.compile(re.escape(alias))
            rows.append((owner, required_id, pattern))
    return rows


ALIAS_PATTERNS = compile_alias_patterns()


def check_line(line: str) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    for owner, required_id, pattern in ALIAS_PATTERNS:
        if not pattern.search(line):
            continue
        required_mention = f"<@{required_id}>"
        if required_mention in line:
            continue
        # If line has some mention but not the required one, still violation.
        found_mentions = ",".join(MENTION_RE.findall(line)) or "(none)"
        issues.append(
            {
                "owner": owner,
                "required": required_mention,
                "found_mentions": found_mentions,
                "alias_pattern": pattern.pattern,
            }
        )
    return issues


def scan_file(path: Path) -> List[Dict[str, object]]:
    violations: List[Dict[str, object]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"failed to read {path}: {e}") from e

    for i, line in enumerate(text.splitlines(), start=1):
        line_issues = check_line(line)
        for issue in line_issues:
            violations.append(
                {
                    "file": str(path),
                    "line": i,
                    "content": line.strip(),
                    **issue,
                }
            )
    return violations


def iter_targets(inputs: Sequence[str], recursive: bool, exts: Sequence[str]) -> List[Path]:
    if not inputs:
        return []

    out: List[Path] = []
    normalized_exts = {e if e.startswith(".") else f".{e}" for e in exts}

    for raw in inputs:
        p = Path(raw)
        if p.is_file():
            out.append(p)
            continue
        if p.is_dir():
            if recursive:
                for child in p.rglob("*"):
                    if child.is_file() and child.suffix in normalized_exts:
                        out.append(child)
            else:
                for child in p.iterdir():
                    if child.is_file() and child.suffix in normalized_exts:
                        out.append(child)
            continue
        raise RuntimeError(f"path not found: {raw}")

    return sorted(set(out))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Detect alias lines missing required Discord user mentions.")
    p.add_argument("paths", nargs="*", help="Files or directories to scan")
    p.add_argument("--recursive", action="store_true", help="Recursively scan directories")
    p.add_argument(
        "--ext",
        default=".md,.txt",
        help="Comma-separated file extensions for directory scan (default: .md,.txt)",
    )
    p.add_argument("--text", help="Check one text line directly")
    p.add_argument("--json", action="store_true", help="Output violations in JSON")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.text and not args.paths:
        print("Provide --text or at least one path.", file=sys.stderr)
        return 2

    violations: List[Dict[str, object]] = []

    if args.text is not None:
        for issue in check_line(args.text):
            violations.append(
                {
                    "file": "<stdin-text>",
                    "line": 1,
                    "content": args.text,
                    **issue,
                }
            )

    if args.paths:
        exts = [x.strip() for x in args.ext.split(",") if x.strip()]
        try:
            targets = iter_targets(args.paths, recursive=args.recursive, exts=exts)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 2

        for target in targets:
            try:
                violations.extend(scan_file(target))
            except RuntimeError as e:
                print(str(e), file=sys.stderr)
                return 2

    if args.json:
        print(json.dumps(violations, ensure_ascii=False, indent=2))
    else:
        if not violations:
            print("PASS: no alias mention violations found.")
        else:
            print(f"FAIL: {len(violations)} violation(s) found.")
            for v in violations:
                print(
                    f"- {v['file']}:{v['line']} | need {v['required']} | "
                    f"mentions={v['found_mentions']} | text={v['content']}"
                )

    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
