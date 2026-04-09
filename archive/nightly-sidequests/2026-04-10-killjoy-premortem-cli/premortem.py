#!/usr/bin/env python3
"""
premortem -- KILLJOY's Pre-Mortem Attack Tool

Reads a plan document (markdown) and generates structured pre-mortem analysis
using the 5-layer attack framework:
  1. Premise Attack    -- What assumptions is this built on?
  2. Counterfactual    -- If the core assumption is wrong, what survives?
  3. Competition       -- How would competitors react?
  4. Scale             -- Does this hold at 10x?
  5. Time              -- Will we regret this in 6 months?

Usage:
  python3 premortem.py <plan.md> [--json] [--layer 1-5] [--severity critical|high|medium]
"""

import argparse
import json
import re
import sys
from pathlib import Path

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

ASSUMPTION_PATTERNS = [
    (r"(?:we\s+)?(?:assume|assuming|assumption)[:\s]\s*(.+?)(?:[.\n])", "explicit"),
    (r"(?:we\s+)?will\s+(.{10,80}?)(?:[.\n,])", "future_claim"),
    (r"(?:users?|customers?|clients?)\s+will\s+(.{10,80}?)(?:[.\n,])", "user_behavior"),
    (r"(?:it\s+)?should\s+(.{10,80}?)(?:[.\n,])", "normative"),
    (r"(?:we\s+)?can\s+(.{10,80}?)(?:[.\n,])", "capability"),
    (r"(\w[\w\s]{3,40})\s+is\s+(?:a\s+|an\s+)?(\w[\w\s]{3,60}?)(?:[.\n,])", "categorical"),
    (r"(?:once|after|when|as soon as)\s+(.{10,80}?)(?:[,.]|\n)", "dependency"),
]

RISK_KEYWORDS = {
    "market": [
        r"\b(?:user|users|customer|customers|demand|market|adoption|sign.?up|register|retention|churn)\b",
    ],
    "execution": [
        r"\b(?:deadline|timeline|schedule|sprint|deliver|launch|deploy|ship|build|implement|develop)\b",
    ],
    "technical": [
        r"\b(?:api|database|server|performance|scale|latency|concurrent|throughput|infra|stack|framework)\b",
    ],
    "external": [
        r"\b(?:competitor|regulation|compliance|legal|policy|third.?party|vendor|partner)\b",
    ],
    "financial": [
        r"\b(?:cost|budget|revenue|price|pricing|payment|monetiz|roi|invest|funding)\b",
    ],
}


def extract_text(path: str) -> str:
    raw = Path(path).read_text(encoding="utf-8")
    cleaned = re.sub(r"```[\s\S]*?```", "", raw)
    cleaned = re.sub(r"`[^`]+`", "", cleaned)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n\n", cleaned).strip()
    return cleaned


def extract_assumptions(text: str) -> list:
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


def classify_risk_domain(text: str) -> dict:
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


def generate_layer_questions(assumptions: list, risk_domains: dict) -> dict:
    layers = {}

    # Layer 1: Premise Attack
    premise_qs = []
    for a in assumptions[:5]:
        stmt = a["statement"]
        premise_qs.append(
            "- **\u5047\u8bbe\u653b\u51fb**: `{}` \u2014 \u6709\u9a8c\u8bc1\u8fc7\u5417\uff1f\u5982\u679c\u6ca1\u9a8c\u8bc1\uff0c\u4e3a\u4ec0\u4e48\u5f53\u771f\u7406\u7528\uff1f".format(stmt)
        )
    if not premise_qs:
        premise_qs.append("- \u6587\u6863\u4e2d\u6ca1\u6709\u53d1\u73b0\u663e\u5f0f\u5047\u8bbe\u2014\u2014\u8fd9\u672c\u8eab\u5c31\u662f\u4e00\u4e2a\u5371\u9669\u4fe1\u53f7\u3002\u9690\u5f0f\u5047\u8bbe\u5462\uff1f")
    layers["1_premise"] = {
        "name": "\u524d\u63d0\u653b\u51fb",
        "description": "\u8fd9\u4e2a\u65b9\u6848\u5efa\u7acb\u5728\u4ec0\u4e48\u5047\u8bbe\u4e0a\uff1f\u5047\u8bbe\u6709\u9a8c\u8bc1\u8fc7\u5417\uff1f",
        "questions": premise_qs,
    }

    # Layer 2: Counterfactual Attack
    critical = [a for a in assumptions if a["severity"] == "critical"]
    cf_qs = []
    if critical:
        for a in critical[:3]:
            stmt = a["statement"]
            cf_qs.append(
                "- **\u53cd\u4e8b\u5b9e**: \u5982\u679c `{}` \u662f\u9519\u7684\uff0c\u65b9\u6848\u8fd8\u6210\u7acb\u5417\uff1f\u80fd\u6d3b\u5417\uff1f".format(stmt)
            )
    else:
        cf_qs.append("- \u6700\u6838\u5fc3\u7684\u524d\u63d0\u5047\u8bbe\u662f\u4ec0\u4e48\uff1f\u53cd\u8f6c\u5b83\uff0c\u65b9\u6848\u8fd8\u7ad9\u5f97\u4f4f\u5417\uff1f")
    layers["2_counterfactual"] = {
        "name": "\u53cd\u4e8b\u5b9e\u653b\u51fb",
        "description": "\u5982\u679c\u6700\u6838\u5fc3\u7684\u4e00\u4e2a\u5047\u8bbe\u662f\u9519\u7684\uff0c\u6574\u4e2a\u65b9\u6848\u8fd8\u6210\u7acb\u5417\uff1f",
        "questions": cf_qs,
    }

    # Layer 3: Competition Attack
    comp_qs = [
        "- \u7ade\u4e89\u5bf9\u624b\u770b\u5230\u8fd9\u4e2a\u65b9\u6848\u4f1a\u7b11\u8fd8\u662f\u4f1a\u6015\uff1f",
        "- \u4ed6\u4eec\u590d\u5236\u8fd9\u4e2a\u9700\u8981\u591a\u4e45\uff1f",
        "- \u8fd9\u4e2a\u65b9\u6848\u521b\u9020\u4e86\u53ef\u9632\u5fa1\u7684\u62a4\u57ce\u6cb3\uff0c\u8fd8\u662f\u53ea\u662f\u5148\u53d1\u4f18\u52bf\uff1f",
    ]
    if risk_domains.get("market", 0) > 0.2:
        comp_qs.insert(0, "- \u6587\u6863\u4e2d\u63d0\u5230\u4e86\u5e02\u573a/\u7528\u6237\u2014\u2014\u7ade\u54c1\u5f53\u524d\u5728\u505a\u4ec0\u4e48\uff1f\u4e3a\u4ec0\u4e48\u4e0d\u505a\u7684\u7406\u7531\u4e0d\u9002\u7528\u4e8e\u4ed6\u4eec\uff1f")
    layers["3_competition"] = {
        "name": "\u7ade\u4e89\u653b\u51fb",
        "description": "\u7ade\u4e89\u5bf9\u624b\u770b\u5230\u8fd9\u4e2a\u65b9\u6848\u4f1a\u7b11\u8fd8\u662f\u4f1a\u6015\uff1f",
        "questions": comp_qs,
    }

    # Layer 4: Scale Attack
    scale_qs = [
        "- \u8fd9\u4e2a\u65b9\u6848\u5728 10 \u500d\u7528\u6237\u91cf\u4e0b\u8fd8\u80fd\u5de5\u4f5c\u5417\uff1f",
        "- \u54ea\u4e2a\u7ec4\u4ef6\u4f1a\u6700\u5148\u65ad\u88c2\uff1f",
        "- \u6210\u672c\u662f\u7ebf\u6027\u7684\u8fd8\u662f\u4f1a\u6307\u6570\u589e\u957f\uff1f",
    ]
    if risk_domains.get("technical", 0) > 0.2:
        scale_qs.insert(0, "- \u6280\u672f\u67b6\u6784\u7684\u74f6\u9888\u5728\u54ea\u91cc\uff1f\u4ec0\u4e48\u65f6\u5019\u4f1a\u649e\u4e0a\uff1f")
    layers["4_scale"] = {
        "name": "\u89c4\u6a21\u653b\u51fb",
        "description": "\u8fd9\u4e2a\u65b9\u6848\u5728 10 \u500d\u89c4\u6a21\u4e0b\u8fd8\u80fd\u5de5\u4f5c\u5417\uff1f",
        "questions": scale_qs,
    }

    # Layer 5: Time Attack
    time_qs = [
        "- 6 \u4e2a\u6708\u540e\uff0c\u56e2\u961f\u4f1a\u540e\u6094\u8fd9\u4e2a\u51b3\u5b9a\u5417\uff1f",
        "- \u8fd9\u4e2a\u65b9\u6848\u5728\u4ec0\u4e48\u6761\u4ef6\u4e0b\u4f1a\u53d8\u6210\u6280\u672f\u503a\uff1f",
        "- \u5982\u679c\u8981\u63a8\u7ffb\u91cd\u6765\uff0c\u6210\u672c\u6709\u591a\u5927\uff1f",
    ]
    layers["5_time"] = {
        "name": "\u65f6\u95f4\u653b\u51fb",
        "description": "6 \u4e2a\u6708\u540e\uff0c\u56e2\u961f\u4f1a\u540e\u6094\u8fd9\u4e2a\u51b3\u5b9a\u5417\uff1f",
        "questions": time_qs,
    }

    return layers


def generate_verdict(assumptions: list, risk_domains: dict) -> str:
    crit_count = sum(1 for a in assumptions if a["severity"] == "critical")
    high_count = sum(1 for a in assumptions if a["severity"] == "high")

    if crit_count >= 3:
        return (
            "\u26a0\ufe0f **RED FLAG**: \u53d1\u73b0 {} \u4e2a\u81f4\u547d\u5047\u8bbe\u3001{} \u4e2a\u9ad8\u98ce\u9669\u5047\u8bbe\u3002\n"
            "\u8fd9\u4e2a\u65b9\u6848\u5728\u81f3\u5c11 3 \u4e2a\u5173\u952e\u70b9\u4e0a\u7f3a\u4e4f\u9a8c\u8bc1\u3002\u7ee7\u7eed\u63a8\u8fdb = \u8d4c\u535a\u3002\n"
            "\u5efa\u8bae\uff1a\u5148\u9a8c\u8bc1\u6700\u81f4\u547d\u7684\u5047\u8bbe\uff0c\u518d\u8ba8\u8bba\u6267\u884c\u3002"
        ).format(crit_count, high_count)
    elif crit_count >= 1:
        return (
            "\U0001f7e1 **CAUTION**: \u53d1\u73b0 {} \u4e2a\u81f4\u547d\u5047\u8bbe\u3001{} \u4e2a\u9ad8\u98ce\u9669\u5047\u8bbe\u3002\n"
            "\u65b9\u6848\u6709\u660e\u786e\u7684\u8584\u5f31\u73af\u8282\u3002\u4e0d\u81f4\u547d\uff0c\u4f46\u5982\u679c\u90a3\u4e2a\u5047\u8bbe\u662f\u9519\u7684\uff0c\u540e\u679c\u5f88\u4e25\u91cd\u3002\n"
            "\u5efa\u8bae\uff1a\u4e3a\u81f4\u547d\u5047\u8bbe\u8bbe\u8ba1 MVP \u9a8c\u8bc1\uff0c\u540c\u6b65\u63a8\u8fdb\u5176\u4ed6\u90e8\u5206\u3002"
        ).format(crit_count, high_count)
    elif high_count >= 2:
        return (
            "\U0001f7e1 **CAUTION**: \u672a\u53d1\u73b0\u81f4\u547d\u5047\u8bbe\uff0c\u4f46\u6709 {} \u4e2a\u9ad8\u98ce\u9669\u70b9\u3002\n"
            "\u65b9\u6848\u6574\u4f53\u6846\u67b6\u5408\u7406\uff0c\u4f46\u6267\u884c\u7ec6\u8282\u9700\u8981\u538b\u529b\u6d4b\u8bd5\u3002\n"
            "\u5efa\u8bae\uff1a\u8bc6\u522b\u6700\u5927\u98ce\u9669\uff0c\u51c6\u5907 Plan B\u3002"
        ).format(high_count)
    elif assumptions:
        return (
            "\U0001f7e2 **PROCEED WITH EYES OPEN**: \u53d1\u73b0 {} \u4e2a\u5047\u8bbe\uff0c\u65e0\u81f4\u547d\u7ea7\u3002\n"
            "\u65b9\u6848\u901a\u8fc7\u4e86\u521d\u6b65\u538b\u529b\u6d4b\u8bd5\u3002\u4f46\u6ca1\u627e\u5230\u95ee\u9898 \u2260 \u6ca1\u6709\u95ee\u9898\u3002\n"
            "\u5efa\u8bae\uff1a\u7ee7\u7eed\u63a8\u8fdb\uff0c\u4f46\u6301\u7eed\u76d1\u63a7\u5047\u8bbe\u53d8\u5316\u3002"
        ).format(len(assumptions))
    else:
        return (
            "\u26aa **INSUFFICIENT DATA**: \u6587\u6863\u4e2d\u6ca1\u6709\u53d1\u73b0\u53ef\u5206\u6790\u7684\u5047\u8bbe\u3002\n"
            "\u8981\u4e48\u6587\u6863\u592a\u7b80\u7565\uff0c\u8981\u4e48\u5047\u8bbe\u5168\u90e8\u9690\u5f0f\u3002\u4e24\u8005\u90fd\u4e0d\u662f\u597d\u4e8b\u3002\n"
            "\u5efa\u8bae\uff1a\u8865\u5145\u66f4\u591a\u7ec6\u8282\u540e\u518d\u505a pre-mortem\u3002"
        )


def format_markdown_report(
    plan_path: str,
    assumptions: list,
    risk_domains: dict,
    layers: dict,
    verdict: str,
) -> str:
    lines = [
        "# \U0001f52a Pre-Mortem Report",
        "",
        "**Plan**: `{}`".format(plan_path),
        "**Assumptions found**: {}".format(len(assumptions)),
        "**Risk domains**: {}".format(
            ", ".join("{} ({:.0%})".format(k, v) for k, v in risk_domains.items() if v > 0)
            or "none detected"
        ),
        "",
        "---",
        "",
        "## Verdict",
        "",
        verdict,
        "",
        "---",
        "",
    ]

    if assumptions:
        lines.append("## Extracted Assumptions")
        lines.append("")
        for i, a in enumerate(assumptions, 1):
            sev_icon = {"critical": "\U0001f534", "high": "\U0001f7e0", "medium": "\U0001f7e1", "low": "\U0001f7e2"}.get(
                a["severity"], "\u26aa"
            )
            lines.append("{}. {} **[{}]** ({}) {}".format(i, sev_icon, a["severity"].upper(), a["type"], a["statement"]))
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 5-Layer Attack Analysis")
    lines.append("")
    for key, layer in layers.items():
        lines.append("### Layer {}: {}".format(key[0], layer["name"]))
        lines.append("*{}*".format(layer["description"]))
        lines.append("")
        for q in layer["questions"]:
            lines.append(q)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("> Generated by `premortem` \u2014 KILLJOY's Pre-Mortem Attack Tool \U0001f52a")
    lines.append('> "Be the critic you\'d want stress-testing your plan at 2am."')

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="KILLJOY's Pre-Mortem Attack Tool \u2014 stress-test any plan document"
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
        print("Error: file not found: {}".format(args.plan), file=sys.stderr)
        sys.exit(1)

    text = extract_text(args.plan)
    assumptions = extract_assumptions(text)
    risk_domains = classify_risk_domain(text)
    layers = generate_layer_questions(assumptions, risk_domains)
    verdict = generate_verdict(assumptions, risk_domains)

    if args.severity:
        min_sev = SEVERITY_ORDER[args.severity]
        assumptions = [a for a in assumptions if SEVERITY_ORDER[a["severity"]] <= min_sev]

    if args.layer:
        layers = {k: v for k, v in layers.items() if k.startswith(str(args.layer))}

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
