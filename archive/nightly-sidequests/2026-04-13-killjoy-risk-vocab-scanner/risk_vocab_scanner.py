#!/usr/bin/env python3
"""
risk_vocab_scanner.py — KILLJOY's risk-vocabulary scanner.

Scans markdown/text files for vague language, weasel words, hedging,
unbacked claims, and hidden assumptions. Outputs a categorized report
with line numbers and severity ratings.

Usage:
    python3 risk_vocab_scanner.py <file> [--severity low|medium|high] [--json]
    python3 risk_vocab_scanner.py <directory>  (scans all .md/.txt files)
    cat file.md | python3 risk_vocab_scanner.py -

Zero dependencies. Python 3.7+.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

class RiskPattern(NamedTuple):
    category: str
    pattern: str  # regex
    description: str
    severity: str  # low / medium / high
    suggestion: str


PATTERNS: List[RiskPattern] = [
    # --- Weasel words (Chinese) ---
    RiskPattern(
        "weasel_word",
        r"值得考虑|有一定道理|不失为一种方案|各有千秋|或许可以|也许能够",
        "模糊缓冲词：用模糊语言掩盖判断力的缺失",
        "medium",
        "用一个明确的判断替代，或承认不确定并给出验证路径",
    ),
    RiskPattern(
        "hedging_zh",
        r"可能(?:会|有|是|能|需要)?(?:一些|一定|某种|某种程度)?(?:的)?(?:影响|风险|问题|效果|变化)",
        "中式对冲：承认风险存在但模糊化具体影响",
        "medium",
        "具体化：什么条件下会发生？概率多少？后果多严重？",
    ),
    RiskPattern(
        "unsupported_claim_zh",
        r"(?:用户|市场|客户)(?:会|将会|一定会|肯定会|自然会)(?:需要|喜欢|使用|购买|接受|采用)",
        "未验证的用户假设：声称用户会做什么但没有数据支撑",
        "high",
        "改为'我们假设用户会X，验证方式是Y'，或标注为待验证假设",
    ),

    # --- Assumption signals (Chinese) ---
    RiskPattern(
        "hidden_assumption_zh",
        r"(?:只要|只需|只需要|只要能)(.+?)(?:[，。就即可])",
        "隐藏假设：用'只要'把关键假设藏在条件从句里",
        "high",
        "把'只要X'改写为显式假设：'假设：X 成立。如果 X 不成立，则...'",
    ),
    RiskPattern(
        "schedule_optimism_zh",
        r"(?:预计|大概|约|大约|差不多)(?:需要|花|耗时|用)(?:\d+|\w+)(?:天|周|月|小时|人天|人周|人月)",
        "排期乐观症：用模糊估计替代有依据的排期",
        "medium",
        "附上分解估算：各子任务的 pessimistic/optimistic/expected",
    ),
    RiskPattern(
        "future_optimism_zh",
        r"(?:以后|后续|将来|未来|之后)(?:再|会|可以|将会)(?:优化|完善|改进|补充|处理|解决|重构)",
        "未来乐观主义：把困难推给'以后'",
        "high",
        "写明具体时间和触发条件：'在 X 里程碑前完成，由 Y 负责'",
    ),

    # --- Weasel words (English) ---
    RiskPattern(
        "weasel_word",
        r"\b(?:arguably|perhaps|maybe|possibly|somewhat|fairly|quite|rather|relatively)\b",
        "Weasel word: hedges that weaken the claim without adding information",
        "low",
        "Make a clear claim or explicitly state uncertainty with a verification path",
    ),
    RiskPattern(
        "hedging_en",
        r"\b(?:might|could|may)(?:\s+also)?\s+(?:be|have|need|cause|lead|result)\b",
        "English hedging: acknowledges risk without quantifying it",
        "medium",
        "Quantify: under what conditions, with what probability, and what consequence?",
    ),
    RiskPattern(
        "unsupported_claim_en",
        r"\b(?:users?|customers?|the market|everyone|people)\s+(?:will|would|should|need to|want to|are going to)\b",
        "Unvalidated user assumption: claims what users will do without evidence",
        "high",
        "Rephrase as 'We assume users will X; validation method: Y'",
    ),

    # --- Assumption signals (English) ---
    RiskPattern(
        "hidden_assumption_en",
        r"\b(?:as long as|assuming|provided that|given that)\b",
        "Hidden assumption: buries a critical dependency in a conditional",
        "high",
        "Make the assumption explicit: 'Assumption: X holds. If not, then...'",
    ),
    RiskPattern(
        "future_optimism_en",
        r"\b(?:later|eventually|in the future|down the road|at some point)\s+(?:we['']?ll|we can|we will|to)\b",
        "Future optimism: defers difficulty to an unspecified 'later'",
        "high",
        "Attach a concrete deadline and owner: 'By milestone X, Y will handle this'",
    ),
    RiskPattern(
        "schedule_optimism_en",
        r"\b(?:should take|estimated at|about|around|roughly)\s+\d+\s+(?:days?|weeks?|months?|hours?|sprints?)\b",
        "Schedule optimism: fuzzy estimate without breakdown",
        "medium",
        "Provide a 3-point estimate (optimistic/expected/pessimistic) with task breakdown",
    ),

    # --- General danger signs ---
    RiskPattern(
        "scope_creep",
        r"(?:而且|另外|同时|此外|plus|also|additionally|and also).{0,30}(?:需要|得|have to|need to|must)",
        "范围蔓延信号：在已有工作基础上不断追加'只需要再做一件事'",
        "medium",
        "停下来做范围盘点：当前已承诺的工作量是多少？",
    ),
    RiskPattern(
        "silver_bullet",
        r"(?:只要|只需要|只需|all we need|simply|just).{0,20}(?:就能|就可以|to solve|to fix|to achieve)",
        "银弹幻觉：暗示问题有简单解法",
        "high",
        "追问：如果真的这么简单，为什么还没人做？",
    ),
    RiskPattern(
        "survivorship_bias",
        r"(?:成功案例|best practice|行业标杆|业界标准|proven|established|standard approach)",
        "幸存者偏差引用：引用成功案例但不提失败案例",
        "medium",
        "补充：有多少人用同样的方法失败了？",
    ),
]

# Compile all patterns
COMPILED = [(rp, re.compile(rp.pattern, re.IGNORECASE)) for rp in PATTERNS]


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class Finding(NamedTuple):
    file: str
    line_num: int
    line_text: str
    category: str
    severity: str
    description: str
    suggestion: str
    matched_text: str


def scan_text(text: str, filename: str = "<stdin>") -> List[Finding]:
    """Scan a single text and return findings."""
    findings = []
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            # Skip empty lines and headings for cleaner output
            pass
        for rp, pat in COMPILED:
            for m in pat.finditer(stripped):
                findings.append(Finding(
                    file=filename,
                    line_num=i,
                    line_text=stripped,
                    category=rp.category,
                    severity=rp.severity,
                    description=rp.description,
                    suggestion=rp.suggestion,
                    matched_text=m.group(0),
                ))
    return findings


def scan_file(filepath: str) -> List[Finding]:
    """Scan a single file."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return scan_text(text, filepath)


def scan_path(path: str) -> List[Finding]:
    """Scan a file or directory."""
    p = Path(path)
    if p.is_file():
        return scan_file(str(p))
    elif p.is_dir():
        findings = []
        for ext in ("*.md", "*.txt", "*.markdown"):
            for fp in p.rglob(ext):
                # Skip hidden dirs and node_modules
                parts = fp.parts
                if any(part.startswith(".") or part == "node_modules" for part in parts):
                    continue
                findings.extend(scan_file(str(fp)))
        return findings
    else:
        print(f"Error: {path} is not a file or directory", file=sys.stderr)
        return []


def format_report(findings: List[Finding], min_severity: str = "low") -> str:
    """Format findings as a human-readable report."""
    severity_order = {"low": 0, "medium": 1, "high": 2}
    min_level = severity_order.get(min_severity, 0)

    filtered = [f for f in findings if severity_order.get(f.severity, 0) >= min_level]

    if not filtered:
        return "✅ No risk vocabulary found. Either the document is clean, or it's hiding them too well."

    # Sort by severity desc, then by file/line
    filtered.sort(key=lambda f: (-severity_order.get(f.severity, 0), f.file, f.line_num))

    lines = []
    lines.append(f"🔪 KILLJOY Risk Vocabulary Scanner — {len(filtered)} finding(s)")
    lines.append("=" * 60)

    # Summary
    by_cat: Dict[str, List[Finding]] = defaultdict(list)
    by_sev: Dict[str, int] = defaultdict(int)
    for f in filtered:
        by_cat[f.category].append(f)
        by_sev[f.severity] += 1

    lines.append(f"\n📊 Severity breakdown:")
    for sev in ("high", "medium", "low"):
        if sev in by_sev:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[sev]
            lines.append(f"  {icon} {sev}: {by_sev[sev]}")

    lines.append(f"\n📋 Category breakdown:")
    for cat, items in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        lines.append(f"  {cat}: {len(items)}")

    lines.append(f"\n{'—' * 60}")
    lines.append("Findings:\n")

    for i, f in enumerate(filtered, 1):
        sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(f.severity, "⚪")
        lines.append(f"{i}. {sev_icon} [{f.severity.upper()}] {f.category}")
        lines.append(f"   📍 {f.file}:{f.line_num}")
        lines.append(f"   💬 \"{f.matched_text}\"")
        lines.append(f"   ⚠️  {f.description}")
        lines.append(f"   💡 {f.suggestion}")
        lines.append("")

    return "\n".join(lines)


def format_json(findings: List[Finding], min_severity: str = "low") -> str:
    """Format findings as JSON."""
    severity_order = {"low": 0, "medium": 1, "high": 2}
    min_level = severity_order.get(min_severity, 0)
    filtered = [f for f in findings if severity_order.get(f.severity, 0) >= min_level]
    return json.dumps([f._asdict() for f in filtered], indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="🔪 KILLJOY's risk-vocabulary scanner — find weasel words, hidden assumptions, and unbacked claims.",
    )
    parser.add_argument(
        "path",
        help="File or directory to scan. Use '-' for stdin.",
    )
    parser.add_argument(
        "--severity",
        choices=["low", "medium", "high"],
        default="low",
        help="Minimum severity to report (default: low)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON instead of human-readable report",
    )
    args = parser.parse_args()

    if args.path == "-":
        text = sys.stdin.read()
        findings = scan_text(text, "<stdin>")
    else:
        findings = scan_path(args.path)

    if args.json_output:
        print(format_json(findings, args.severity))
    else:
        print(format_report(findings, args.severity))


if __name__ == "__main__":
    main()
