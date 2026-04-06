#!/usr/bin/env python3
"""
copy_tone_guard.py

A tiny zero-dependency CLI to catch corporate-cliche phrases in Chinese copy
and suggest a cleaner, more human alternative.

Usage:
  python3 copy_tone_guard.py path/to/file.txt
  cat text.txt | python3 copy_tone_guard.py --stdin
  python3 copy_tone_guard.py path/to/file.txt --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

BANNED = {
    "赋能": "帮你做好",
    "一站式": "一个地方搞定",
    "全方位": "完整覆盖",
    "极致体验": "更顺手",
    "开启新篇章": "现在开始",
    "引领未来": "走在前面",
    "匠心打造": "认真做出来",
}


@dataclass
class Hit:
    line_no: int
    phrase: str
    line: str
    suggestion: str


def load_text(path: str | None, use_stdin: bool) -> str:
    if use_stdin:
        return sys.stdin.read()
    if not path:
        raise ValueError("Missing input path. Pass a file or use --stdin.")
    return Path(path).read_text(encoding="utf-8")


def scan(text: str, banned: Dict[str, str]) -> List[Hit]:
    hits: List[Hit] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for phrase, suggestion in banned.items():
            if phrase in line:
                hits.append(Hit(i, phrase, line.strip(), suggestion))
    return hits


def sentence_length_warnings(text: str, threshold: int) -> List[dict]:
    warnings: List[dict] = []
    for i, line in enumerate(text.splitlines(), start=1):
        clean = re.sub(r"\s+", "", line)
        if len(clean) > threshold:
            warnings.append({
                "line_no": i,
                "length": len(clean),
                "line": line.strip(),
            })
    return warnings


def render_text_report(hits: List[Hit], long_lines: List[dict], threshold: int) -> str:
    out: List[str] = []
    out.append("# Copy Tone Guard")
    out.append("")

    if hits:
        out.append(f"Found {len(hits)} cliche phrase hit(s):")
        for h in hits:
            out.append(
                f"- L{h.line_no}: `{h.phrase}` in \"{h.line}\" → suggestion: `{h.suggestion}`"
            )
    else:
        out.append("No banned cliche phrases found. ✅")

    out.append("")
    if long_lines:
        out.append(
            f"Found {len(long_lines)} line(s) longer than {threshold} chars (consider splitting for scan readability):"
        )
        for item in long_lines:
            out.append(
                f"- L{item['line_no']} ({item['length']} chars): \"{item['line']}\""
            )
    else:
        out.append(f"No overly long lines (>{threshold} chars). ✅")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Catch cliche Chinese marketing copy.")
    parser.add_argument("path", nargs="?", help="Text file path")
    parser.add_argument("--stdin", action="store_true", help="Read text from stdin")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--length-threshold",
        type=int,
        default=36,
        help="Warn when a line exceeds this many non-space chars (default: 36)",
    )

    args = parser.parse_args()

    try:
        text = load_text(args.path, args.stdin)
    except Exception as e:
        print(f"Input error: {e}", file=sys.stderr)
        return 2

    hits = scan(text, BANNED)
    long_lines = sentence_length_warnings(text, args.length_threshold)

    if args.json:
        payload = {
            "cliche_hits": [
                {
                    "line_no": h.line_no,
                    "phrase": h.phrase,
                    "line": h.line,
                    "suggestion": h.suggestion,
                }
                for h in hits
            ],
            "long_line_warnings": long_lines,
            "summary": {
                "cliche_hit_count": len(hits),
                "long_line_count": len(long_lines),
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text_report(hits, long_lines, args.length_threshold))

    # Non-zero if issues found, useful in CI/check hooks.
    return 1 if (hits or long_lines) else 0


if __name__ == "__main__":
    raise SystemExit(main())
