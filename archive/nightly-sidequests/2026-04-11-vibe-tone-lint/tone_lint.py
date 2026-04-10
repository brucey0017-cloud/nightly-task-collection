#!/usr/bin/env python3
"""Tiny zero-dependency tone lint for brand copy.

Focus: catch corporate cliches and flat AI-style openers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

BANNED_PHRASES = [
    "赋能",
    "一站式",
    "全方位",
    "极致体验",
    "开启新篇章",
    "引领未来",
    "匠心打造",
]

FLAT_OPENERS = [
    "Great question",
    "I'd be happy to help",
    "Absolutely",
]


@dataclass
class Hit:
    kind: str
    token: str
    count: int


def find_hits(text: str) -> list[Hit]:
    hits: list[Hit] = []

    for phrase in BANNED_PHRASES:
        cnt = text.count(phrase)
        if cnt:
            hits.append(Hit("banned_phrase", phrase, cnt))

    for opener in FLAT_OPENERS:
        pattern = re.compile(rf"(^|\n)\s*{re.escape(opener)}[\s,!\.]*", re.IGNORECASE)
        cnt = len(pattern.findall(text))
        if cnt:
            hits.append(Hit("flat_opener", opener, cnt))

    return hits


def sentence_lengths(text: str) -> list[int]:
    parts = re.split(r"[。！？!?\n]+", text)
    return [len(p.strip()) for p in parts if p.strip()]


def score_copy(text: str, hits: Iterable[Hit]) -> int:
    score = 100
    for h in hits:
        if h.kind == "banned_phrase":
            score -= 15 * h.count
        elif h.kind == "flat_opener":
            score -= 10 * h.count

    lengths = sentence_lengths(text)
    if lengths:
        avg = sum(lengths) / len(lengths)
        # long average lines often read like manuals
        if avg > 40:
            score -= 10

    return max(0, score)


def lint(text: str) -> dict:
    hits = find_hits(text)
    score = score_copy(text, hits)
    total_hits = sum(h.count for h in hits)
    status = "pass" if total_hits == 0 and score >= 85 else "needs_rewrite"

    return {
        "status": status,
        "score": score,
        "total_hits": total_hits,
        "hits": [h.__dict__ for h in hits],
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Lint copy tone for cliches and stale AI opener patterns")
    p.add_argument("--file", "-f", type=Path, help="Path to text/markdown file")
    p.add_argument("--text", "-t", help="Raw text input")
    p.add_argument("--json", action="store_true", help="Output JSON")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.text:
        text = args.text
    elif args.file:
        text = args.file.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    result = lint(text)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"score: {result['score']}")
        print(f"total_hits: {result['total_hits']}")
        for hit in result["hits"]:
            print(f"- {hit['kind']}: {hit['token']} x{hit['count']}")

    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
