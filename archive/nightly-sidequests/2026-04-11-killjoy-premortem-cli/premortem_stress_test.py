#!/usr/bin/env python3
"""
premortem_stress_test.py — KILLJOY's Decision Stress-Test CLI

Takes a plan / decision / PRD document and runs it through the 5-layer
attack framework. Outputs a structured pre-mortem markdown report.

Usage:
    python3 premortem_stress_test.py plan.md
    python3 premortem_stress_test.py plan.md -o premortem_report.md
    echo "Build a SaaS dashboard for freelancers" | python3 premortem_stress_test.py -
    python3 premortem_stress_test.py plan.md --json

Zero dependencies. Python 3.8+.
"""

import argparse
import json
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Attack layers — each returns a dict of {question, probes, severity_hint}
# ---------------------------------------------------------------------------

ATTACK_LAYERS: List[Dict] = [
    {
        "id": "assumption",
        "name_zh": "前提攻击",
        "name_en": "Assumption Attack",
        "icon": "🔍",
        "core_question": "这个方案建立在什么假设上？这些假设有验证过吗？",
        "probes": [
            "列出方案中显式提到的所有假设",
            "列出方案中隐含但从未讨论的假设（用户行为、技术能力、市场状态）",
            "对每个假设：如果反转它，方案的哪个部分会崩塌？",
            "最危险的假设是什么？—— 那个团队认为理所当然、从未质疑过的",
        ],
        "severity_hint": "如果有 >2 个未验证的核心假设，风险等级自动提升一级",
    },
    {
        "id": "counterfactual",
        "name_zh": "反事实攻击",
        "name_en": "Counterfactual Attack",
        "icon": "🔀",
        "core_question": "如果最核心的一个假设是错的，整个方案还成立吗？",
        "probes": [
            "识别方案最核心的依赖（通常是收入假设或用户增长假设）",
            "假设这个依赖完全不成立——方案还有 Plan B 吗？",
            "方案中有哪些 '单向门' 决策（不可逆）？如果错了怎么办？",
            "最坏情况下，损失是多少？团队能活下来吗？",
        ],
        "severity_hint": "如果核心假设失败 = 项目归零且无法止损，这是致命级",
    },
    {
        "id": "competition",
        "name_zh": "竞争攻击",
        "name_en": "Competition Attack",
        "icon": "⚔️",
        "core_question": "竞争对手看到这个方案会笑还是会怕？",
        "probes": [
            "市场上已有类似方案吗？为什么它们没解决这个问题？",
            "如果竞品在 3 个月内复制你的方案，你的护城河在哪里？",
            "这个方案是在创造新需求还是在分食现有市场？",
            "用户从现有方案迁移过来的切换成本是什么？足够低吗？",
        ],
        "severity_hint": "如果没有可防御的差异化优势，这只是'又一个 X'",
    },
    {
        "id": "scale",
        "name_zh": "规模攻击",
        "name_en": "Scale Attack",
        "icon": "📐",
        "core_question": "这个方案在 10 倍规模下还能工作吗？",
        "probes": [
            "用户量 10x 后，系统的瓶颈在哪里？（技术 / 运营 / 支持）",
            "成本是线性增长还是有突变点？突变点在哪里？",
            "团队规模需要同比例增长吗？如果是，这不叫规模效应",
            "哪些流程现在是手动的？10x 时还能手动吗？",
        ],
        "severity_hint": "如果 10x 需要重写核心架构，现在就该设计好",
    },
    {
        "id": "time",
        "name_zh": "时间攻击",
        "name_en": "Time Attack",
        "icon": "⏳",
        "core_question": "6 个月后，团队会后悔这个决定吗？",
        "probes": [
            "这个决策会 lock-in 哪些未来的选择？",
            "6 个月后的市场/技术环境可能有什么变化？方案还适应吗？",
            "现在做的决定中，哪些其实可以推迟到获得更多信息后再做？",
            "如果 6 个月后要推翻这个决策，推翻成本是多少？",
        ],
        "severity_hint": "推迟可逆决策永远是更安全的选择",
    },
]


# ---------------------------------------------------------------------------
# Keyword-based risk hints (extract from document text)
# ---------------------------------------------------------------------------

RISK_KEYWORDS: Dict[str, List[str]] = {
    "market": ["用户", "市场", "需求", "增长", "转化", "付费", "TAM", "SAM", "SOM",
               "用户增长", "留存", "churn", "user", "market", "growth", "demand"],
    "execution": ["排期", "工期", "里程碑", "Sprint", "MVP", "上线", "发布",
                  "deadline", "timeline", "sprint", "launch", "交付"],
    "technical": ["架构", "性能", "并发", "延迟", "可用性", "扩展", "数据库",
                  "API", "架构", "性能", "scale", "latency", "throughput", "infra"],
    "regulatory": ["合规", "监管", "隐私", "GDPR", "数据保护", "牌照", "审批",
                   "compliance", "regulation", "privacy", "license"],
    "financial": ["成本", "预算", "收入", "利润", "ROI", "融资", "现金流",
                  "cost", "budget", "revenue", "profit", "cashflow"],
}


def extract_risk_signals(text: str) -> Dict[str, List[str]]:
    """Return matched keywords per risk category."""
    text_lower = text.lower()
    signals: Dict[str, List[str]] = {}
    for category, keywords in RISK_KEYWORDS.items():
        found = [kw for kw in keywords if kw.lower() in text_lower]
        if found:
            signals[category] = found
    return signals


def extract_assumption_candidates(text: str) -> List[str]:
    """Heuristic: sentences with assumption language."""
    patterns = [
        r"[假认]为[^。，；\n]{5,}",
        r"假设[^。，；\n]{3,}",
        r"预计[^。，；\n]{3,}",
        r"assum\w+[^.\n]{5,}",
        r"expect\w+[^.\n]{5,}",
        r"should[^.\n]{5,}",
    ]
    results = []
    for p in patterns:
        results.extend(re.findall(p, text, re.IGNORECASE))
    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    input_text: str,
    source_name: str = "stdin",
    extra_context: Optional[str] = None,
) -> str:
    """Generate the full pre-mortem stress-test report."""

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    risk_signals = extract_risk_signals(input_text)
    assumption_hints = extract_assumption_candidates(input_text)

    lines: List[str] = []
    w = lines.append

    w("# 🔪 Pre-Mortem Stress Test Report")
    w("")
    w(f"**Generated:** {now}")
    w(f"**Source:** {source_name}")
    w(f"**Framework:** KILLJOY 5-Layer Attack Framework")
    w("")

    # --- Risk signal scan ---
    if risk_signals:
        w("## 🚨 Risk Signal Scan")
        w("")
        for cat, keywords in risk_signals.items():
            w(f"- **{cat}**: detected keywords: {', '.join(keywords[:6])}")
        w("")

    # --- Assumption hints ---
    if assumption_hints:
        w("## 💡 Extracted Assumption Candidates")
        w("")
        w("> These sentences contain assumption-like language. Verify each one.")
        w("")
        for i, a in enumerate(assumption_hints[:10], 1):
            w(f"{i}. \"{a.strip()}\"")
        if len(assumption_hints) > 10:
            w(f"\n... and {len(assumption_hints) - 10} more")
        w("")

    # --- 5-layer attack ---
    w("## ⚔️ 5-Layer Attack Framework")
    w("")

    for layer in ATTACK_LAYERS:
        w(f"### {layer['icon']} Layer {ATTACK_LAYERS.index(layer)+1}: {layer['name_zh']} / {layer['name_en']}")
        w("")
        w(f"**Core Question:** {layer['core_question']}")
        w("")
        w("**Probes (answer each):**")
        for i, probe in enumerate(layer["probes"], 1):
            w(f"{i}. {probe}")
        w("")
        w(f"⚠️ _{layer['severity_hint']}_")
        w("")

    # --- Pre-mortem narrative ---
    w("## 💀 Pre-Mortem Narrative")
    w("")
    w("> Imagine it's 6 months from now and this project has **failed spectacularly**.")
    w("> What happened? Write the post-mortem from the future.")
    w("")
    w("Fill in:")
    w("1. **What was the #1 cause of death?**")
    w("2. **What early warning signs did we ignore?**")
    w("3. **What would we have done differently?**")
    w("4. **Who saw it coming but didn't speak up?**")
    w("")

    # --- Verdict ---
    w("## 🏁 Verdict Template")
    w("")
    w("After completing all 5 layers, assign:")
    w("")
    w("| Dimension | Rating (🟢 Low / 🟡 Medium / 🔴 High / 💀 Fatal) | Notes |")
    w("|-----------|-------------------------------------------------------|-------|")
    w("| Assumption Risk | _fill_ | |")
    w("| Counterfactual Risk | _fill_ | |")
    w("| Competition Risk | _fill_ | |")
    w("| Scale Risk | _fill_ | |")
    w("| Time Risk | _fill_ | |")
    w("| **Overall** | _fill_ | |")
    w("")
    w("---")
    w("")
    w("_Generated by KILLJOY's premortem_stress_test.py — 首席质疑官的免疫系统_")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="KILLJOY's Decision Stress-Test CLI — 5-layer pre-mortem framework",
    )
    parser.add_argument(
        "input",
        help="Path to plan/decision document, or '-' for stdin",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of markdown",
    )
    parser.add_argument(
        "--context",
        help="Extra context string to append to analysis",
    )
    args = parser.parse_args()

    # Read input
    if args.input == "-":
        text = sys.stdin.read()
        source = "stdin"
    else:
        p = Path(args.input)
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            sys.exit(1)
        text = p.read_text(encoding="utf-8")
        source = str(p)

    report = generate_report(text, source_name=source, extra_context=args.context)

    if args.json:
        risk_signals = extract_risk_signals(text)
        assumptions = extract_assumption_candidates(text)
        out = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "risk_signals": risk_signals,
            "assumption_candidates": assumptions,
            "layers": [
                {
                    "id": l["id"],
                    "name_zh": l["name_zh"],
                    "core_question": l["core_question"],
                    "probes": l["probes"],
                }
                for l in ATTACK_LAYERS
            ],
            "report_markdown": report,
        }
        payload = json.dumps(out, ensure_ascii=False, indent=2)
    else:
        payload = report

    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(payload)


if __name__ == "__main__":
    main()
