#!/usr/bin/env python3
"""
premortem — KILLJOY's Pre-Mortem Attack Tool

Reads a plan document (markdown) and generates structured pre-mortem analysis
using the 5-layer attack framework:
  1. 前提攻击 (Premise Attack)    — What assumptions is this built on?
  2. 反事实攻击 (Counterfactual)  — If the core assumption is wrong, what survives?
  3. 竞争攻击 (Competition)       — How would competitors react?
  4. 规模攻击 (Scale)             — Does this hold at 10x?
  5. 时间攻击 (Time)              — Will we regret this in 6 months?

Usage:
  python3 premortem.py <plan.md> [--json] [--layer 1-5] [--severity critical|high|medium]

Output: Markdown pre-mortem report to stdout (or JSON with --json)
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── Severity levels ──────────────────────────────────────────────────────────

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# ── Assumption extraction heuristics ─────────────────────────────────────────

ASSUMPTION_PATTERNS = [
    # Explicit assumption markers
    (r"(?:we\s+)?(?:assume|assuming|assumption)[:\s]\s*(.+?)(?:[.\n])", "explicit"),
    # Modal verbs (will/shall) stating future state as fact
    (r"(?:we\s+)?will\s+(.{10,80}?)(?:[.\n,])", "future_claim"),
    # "Users will / customers will" — unvalidated user behavior
    (r"(?:users?|customers?|clients?)\s+will\s+(.{10,80}?)(?:[.\n,])", "user_behavior"),
    # "Should" statements — normative claims
    (r"(?:it\s+)?should\s+(.{10,80}?)(?:[.\n,])", "normative"),
    # "Can" capability claims
    (r"(?:we\s+)?can\s+(.{10,80}?)(?:[.\n,])", "capability"),
    # "X is Y" — categorical claims
    (r"(\w[\w\s]{3,40})\s+is\s+(?:a\s+|an\s+)?(\w[\w\s]{3,60}?)(?:[.\n,])", "categorical"),
    # Implicit: "Once X" / "After X" / "When X" — dependency on external events
    (r"(?:once|after|when|as soon as)\s+(.{10,80}?)(?:[,.]|\n)", "dependency"),
]

# ── Risk classification keywords ─────────────────────────────────────────────

RISK_KEYWORDS = {
    "market": [
        r"\b(?:user|users|customer|customers|demand|market| adoption|sign.?up|register|retention|churn)\b",
    ],
    "execution": [
        r"\b(?:deadline|timeline|schedule|sprint|deliver|launch|deploy|ship|build|implement|develop)\b",
    ],
    "technical": [
        r"\b(?:api|database|server|performance|scale|latency|concurrent|throughput|infra|infra|stack|framework)\b",
    ],
    "external": [
        r"\b(?:competitor|regulation|compliance|legal|policy|third.?party|vendor|partner)\b",
    ],
    "financial": [
        r"\b(?:cost|budget|revenue|price|pricing|payment|monetiz|roi|invest|funding)\b",
    ],
}

# ── Core analysis engine ─────────────────────────────────────────────────────


def extract_text(path: str) -> str:
    """Read markdown file and strip code blocks, keeping prose."""
    raw = Path(path).read_text(encoding="utf-8")
    # Remove code blocks
    cleaned = re.sub(r"```[\s\S]*?```", "", raw)
    # Remove inline code
    cleaned = re.sub(r"`[^`]+`", "", cleaned)
    # Remove URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\n{2,}", "\n\n", cleaned).strip()
    return cleaned


def extract_assumptions(text: str) -> list[dict]:
    """Pull out implicit and explicit assumptions from plan text."""
    found = []
    seen = set()
    for pattern, atype in ASSUMPTION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            statement = m.group(1).strip() if m.lastindex else m.group(0).strip()
            key = statement.lower()[:60]
            if key not in seen and len(statement) > 8:
                seen.add(key)
                found.append({
                    "type": atype,
                    "statement": statement,
                    "severity": _classify_severity(statement, atype),
                })
    return found


def _classify_severity(statement: str, atype: str) -> str:
    """Rough severity classification based on pattern type and content."""
    s = statement.lower()
    if atype == "user_behavior":
        return "critical"
    if atype == "dependency":
        return "high"
    if any(w in s for w in ["will", "must", "need to"]):
        return "high"
    if atype in ("future_claim", "categorical"):
        return "medium"
    return "low"


def classify_risk_domain(text: str) -> dict[str, float]:
    """Score text against risk domains by keyword density."""
    lower = text.lower()
    scores = {}
    total = 0
    for domain, patterns in RISK_KEYWORDS.items():
        count = sum(len(re.findall(p, lower)) for p in patterns)
        scores[domain] = count
        total += count
    if total > 0:
        scores = {k: round(v / total, 2) for k, v in scores.items()}
    return scores


def generate_layer_questions(assumptions: list[dict], risk_domains: dict) -> dict:
    """Generate the 5-layer attack questions."""
    layers = {}

    # Layer 1: Premise Attack
    premise_qs = []
    for a in assumptions[:5]:
        premise_qs.append(
            f"- **假设攻击**: "{a['statement']}" — 有验证过吗？如果没验证，为什么当真理用？"
        )
    if not premise_qs:
        premise_qs.append("- 文档中没有发现显式假设——这本身就是一个危险信号。隐式假设呢？")
    layers["1_premise"] = {
        "name": "前提攻击",
        "description": "这个方案建立在什么假设上？假设有验证过吗？",
        "questions": premise_qs,
    }

    # Layer 2: Counterfactual Attack
    critical = [a for a in assumptions if a["severity"] == "critical"]
    cf_qs = []
    if critical:
        for a in critical[:3]:
            cf_qs.append(
                f"- **反事实**: 如果"{a['statement']}"是错的，方案还成立吗？能活吗？"
            )
    else:
        cf_qs.append("- 最核心的前提假设是什么？反转它，方案还站得住吗？")
    layers["2_counterfactual"] = {
        "name": "反事实攻击",
        "description": "如果最核心的一个假设是错的，整个方案还成立吗？",
        "questions": cf_qs,
    }

    # Layer 3: Competition Attack
    comp_qs = [
        "- 竞争对手看到这个方案会笑还是会怕？",
        "- 他们复制这个需要多久？",
        "- 这个方案创造了可防御的护城河，还是只是先发优势？",
    ]
    if risk_domains.get("market", 0) > 0.2:
        comp_qs.insert(0, "- 文档中提到了市场/用户——竞品当前在做什么？为什么不做的理由不适用于他们？")
    layers["3_competition"] = {
        "name": "竞争攻击",
        "description": "竞争对手看到这个方案会笑还是会怕？",
        "questions": comp_qs,
    }

    # Layer 4: Scale Attack
    scale_qs = [
        "- 这个方案在 10 倍用户量下还能工作吗？",
        "- 哪个组件会最先断裂？",
        "- 成本是线性的还是会指数增长？",
    ]
    if risk_domains.get("technical", 0) > 0.2:
        scale_qs.insert(0, "- 技术架构的瓶颈在哪里？什么时候会撞上？")
    layers["4_scale"] = {
        "name": "规模攻击",
        "description": "这个方案在 10 倍规模下还能工作吗？",
        "questions": scale_qs,
    }

    # Layer 5: Time Attack
    time_qs = [
        "- 6 个月后，团队会后悔这个决定吗？",
        "- 这个方案在什么条件下会变成技术债？",
        "- 如果要推翻重来，成本有多大？",
    ]
    layers["5_time"] = {
        "name": "时间攻击",
        "description": "6 个月后，团队会后悔这个决定吗？",
        "questions": time_qs,
    }

    return layers


def generate_verdict(assumptions: list[dict], risk_domains: dict) -> str:
    """Generate a KILLJOY-style verdict."""
    crit_count = sum(1 for a in assumptions if a["severity"] == "critical")
    high_count = sum(1 for a in assumptions if a["severity"] == "high")

    if crit_count >= 3:
        return (
            "⚠️ **RED FLAG**: 发现 {} 个致命假设、{} 个高风险假设。\n"
            "这个方案在至少 3 个关键点上缺乏验证。继续推进 = 赌博。\n"
            "建议：先验证最致命的假设，再讨论执行。"
        ).format(crit_count, high_count)
    elif crit_count >= 1:
        return (
            "🟡 **CAUTION**: 发现 {} 个致命假设、{} 个高风险假设。\n"
            "方案有明确的薄弱环节。不致命，但如果那个假设是错的，后果很严重。\n"
            "建议：为致命假设设计 MVP 验证，同步推进其他部分。"
        ).format(crit_count, high_count)
    elif high_count >= 2:
        return (
            "🟡 **CAUTION**: 未发现致命假设，但有 {} 个高风险点。\n"
            "方案整体框架合理，但执行细节需要压力测试。\n"
            "建议：识别最大风险，准备 Plan B。"
        ).format(high_count)
    elif assumptions:
        return (
            "🟢 **PROCEED WITH EYES OPEN**: 发现 {} 个假设，无致命级。\n"
            "方案通过了初步压力测试。但没找到问题 ≠ 没有问题。\n"
            "建议：继续推进，但持续监控假设变化。"
        ).format(len(assumptions))
    else:
        return (
            "⚪ **INSUFFICIENT DATA**: 文档中没有发现可分析的假设。\n"
            "要么文档太简略，要么假设全部隐式。两者都不是好事。\n"
            "建议：补充更多细节后再做 pre-mortem。"
        )


def format_markdown_report(
    plan_path: str,
    assumptions: list[dict],
    risk_domains: dict,
    layers: dict,
    verdict: str,
) -> str:
    """Format the full pre-mortem as markdown."""
    lines = [
        f"# 🔪 Pre-Mortem Report",
        f"",
        f"**Plan**: `{plan_path}`",
        f"**Assumptions found**: {len(assumptions)}",
        f"**Risk domains**: {', '.join(f'{k} ({v:.0%})' for k, v in risk_domains.items() if v > 0) or 'none detected'}",
        f"",
        f"---",
        f"",
        f"## Verdict",
        f"",
        verdict,
        f"",
        f"---",
        f"",
    ]

    if assumptions:
        lines.append("## Extracted Assumptions")
        lines.append("")
        for i, a in enumerate(assumptions, 1):
            sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                a["severity"], "⚪"
            )
            lines.append(f"{i}. {sev_icon} **[{a['severity'].upper()}]** ({a['type']}) {a['statement']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 5-Layer Attack Analysis")
    lines.append("")
    for key, layer in layers.items():
        lines.append(f"### Layer {key[0]}: {layer['name']}")
        lines.append(f"*{layer['description']}*")
        lines.append("")
        for q in layer["questions"]:
            lines.append(q)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("> Generated by `premortem` — KILLJOY's Pre-Mortem Attack Tool 🔪")
    lines.append("> \"Be the critic you'd want stress-testing your plan at 2am.\"")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="🔪 KILLJOY's Pre-Mortem Attack Tool — stress-test any plan document"
    )
    parser.add_argument("plan", help="Path to plan document (markdown)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of markdown")
    parser.add_argument(
        "--layer",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Only show specific attack layer (1-5)",
    )
    parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low"],
        help="Minimum severity filter for assumptions",
    )
    args = parser.parse_args()

    if not Path(args.plan).exists():
        print(f"Error: file not found: {args.plan}", file=sys.stderr)
        sys.exit(1)

    # Extract and analyze
    text = extract_text(args.plan)
    assumptions = extract_assumptions(text)
    risk_domains = classify_risk_domain(text)
    layers = generate_layer_questions(assumptions, risk_domains)
    verdict = generate_verdict(assumptions, risk_domains)

    # Filter by severity
    if args.severity:
        min_sev = SEVERITY_ORDER[args.severity]
        assumptions = [a for a in assumptions if SEVERITY_ORDER[a["severity"]] <= min_sev]

    # Filter by layer
    if args.layer:
        layer_key = f"{args.layer}_*"
        layers = {k: v for k, v in layers.items() if k.startswith(str(args.layer))}

    # Output
    if args.json:
        output = {
            "plan": args.plan,
            "assumptions": assumptions,
            "risk_domains": risk_domains,
            "layers": layers,
            "verdict": verdict,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        report = format_markdown_report(args.plan, assumptions, risk_domains, layers, verdict)
        print(report)


if __name__ == "__main__":
    main()
