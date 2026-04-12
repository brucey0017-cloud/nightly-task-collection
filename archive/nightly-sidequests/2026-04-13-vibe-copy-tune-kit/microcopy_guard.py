#!/usr/bin/env python3
"""
Microcopy Guard (zero-dependency)

Quickly scan text/markdown files for bland or off-brand phrasing,
then suggest sharper replacements.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class Rule:
    phrase: str
    replacement: str
    note: str


RULES: List[Rule] = [
    Rule("赋能", "让…更快/更稳/更省力", "空泛大词，换成具体收益"),
    Rule("一站式", "在一个地方完成", "营销腔过重"),
    Rule("全方位", "覆盖 A/B/C 场景", "抽象，改成可感知范围"),
    Rule("极致体验", "快到无感 / 一步完成", "形容词堆砌"),
    Rule("开启新篇章", "从今天开始…", "套话"),
    Rule("引领未来", "比现在快 2 倍", "空承诺，改成可验证结果"),
    Rule("匠心打造", "我们把 X 砍掉，只保留 Y", "陈词滥调"),
    Rule("Great question", "", "AI 常见开场白，直接进入答案"),
    Rule("I'd be happy to help", "", "礼貌冗余，删掉"),
    Rule("Absolutely", "", "开场语气词，常可删除"),
]

SENTENCE_SEP = re.compile(r"[。！？!?]\s*|\n+")


def iter_files(paths: Iterable[str]) -> Iterable[pathlib.Path]:
    for raw in paths:
        p = pathlib.Path(raw)
        if not p.exists():
            print(f"[warn] path not found: {p}", file=sys.stderr)
            continue
        if p.is_file():
            yield p
            continue
        for ext in ("*.md", "*.txt", "*.rst"):
            yield from p.rglob(ext)


def score_breathability(line: str, max_len: int) -> bool:
    return len(line.strip()) > max_len


def scan_file(path: pathlib.Path, max_line_len: int) -> List[str]:
    issues: List[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{path}: read_error: {e}"]

    lines = text.splitlines()

    # Phrase rules
    for idx, line in enumerate(lines, start=1):
        for rule in RULES:
            if rule.phrase and rule.phrase in line:
                repl = f" -> 建议：{rule.replacement}" if rule.replacement else ""
                issues.append(
                    f"{path}:{idx}: 命中『{rule.phrase}』{repl}（{rule.note}）"
                )

        if score_breathability(line, max_line_len):
            issues.append(
                f"{path}:{idx}: 句长 {len(line.strip())} > {max_line_len}，建议拆句（用户在扫读）"
            )

    # Exclamation density
    exclamations = text.count("!") + text.count("！")
    if exclamations >= 6:
        issues.append(
            f"{path}: 感叹号 {exclamations} 个，建议克制语气，避免情绪噪音"
        )

    # Paragraph breath check (very rough)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for i, para in enumerate(paragraphs, start=1):
        sentence_count = len([s for s in SENTENCE_SEP.split(para) if s.strip()])
        if sentence_count >= 6 and len(para) > 260:
            issues.append(
                f"{path}: 段落#{i} 偏重（{sentence_count} 句 / {len(para)} 字符），建议分段"
            )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan copy for off-brand phrasing.")
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument(
        "--max-line-len",
        type=int,
        default=70,
        help="Warn if a line is longer than this (default: 70)",
    )
    args = parser.parse_args()

    all_issues: List[str] = []
    seen = set()
    for file in iter_files(args.paths):
        if file in seen:
            continue
        seen.add(file)
        all_issues.extend(scan_file(file, args.max_line_len))

    if not all_issues:
        print("✅ No obvious tone issues found.")
        return 0

    print("⚠️ Microcopy Guard findings")
    for item in all_issues:
        print(f"- {item}")

    print(f"\nTotal issues: {len(all_issues)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
