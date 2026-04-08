#!/usr/bin/env python3
"""
assumption_miner.py — Extract hidden assumptions from any markdown document.

KILLJOY's weapon of choice. Reads a .md file, identifies statements that
carry implicit assumptions, and outputs a structured assumption register
with risk ratings.

Usage:
    python3 assumption_miner.py <file.md> [--format json|md] [--min-risk low|medium|high|critical]

Heuristics (no LLM needed):
    - Future predictions ("will", "shall", "going to")
    - Unqualified claims ("obviously", "clearly", "everyone knows")
    - Superlatives / absolutes ("always", "never", "all", "none")
    - Conditional without else ("if X then Y" without "otherwise")
    - Numeric claims without source ("grow by 50%", "$10M market")
    - Vague quantifiers ("a lot", "many", "most", "significant")
    - Passive ownership ("it is expected", "should be done")
    - Scope creep signals ("and also", "plus", "as well as")
    - Dependencies stated as facts ("API returns", "users prefer")
    - Temporal assumptions ("soon", "quickly", "immediately")

Risk rating:
    - critical: assumption is foundational and unvalidated
    - high: assumption affects a major workstream
    - medium: assumption affects quality or timeline
    - low: assumption is cosmetic or easily reversible
"""

import re
import sys
import json
import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Tuple


@dataclass
class Assumption:
    line_number: int
    line_text: str
    category: str
    trigger: str
    assumption: str
    risk: str  # low, medium, high, critical
    inverted: str  # what if this assumption is wrong?


# ── Pattern definitions ──────────────────────────────────────────────

PATTERNS: List[Tuple[str, str, str, str, str]] = [
    # (regex, category, risk, assumption_template, inversion_template)
    # The trigger word is captured for context.

    # Future predictions
    (r'\b(will|shall|going to)\s+(be|have|reach|achieve|generate|support|handle|provide|deliver|allow|enable|increase|grow)\b',
     'future_prediction', 'high',
     'Predicts a future outcome as certain.',
     'If this outcome does not materialize, what is the fallback?'),

    # Unqualified claims
    (r'\b(obviously|clearly|everyone knows|it goes without saying|needless to say|of course|simply|just|merely)\b',
     'unqualified_claim', 'medium',
     'Claims something as self-evident without evidence.',
     'What evidence supports this claim? If none exists, the plan has a hole.'),

    # Absolutes
    (r'\b(always|never|all|none|every|any|no one|nobody|everybody|impossible|guaranteed|certain)\b',
     'absolute_claim', 'high',
     'Uses an absolute that is rarely true in practice.',
     'Find ONE counterexample. If you can, the absolute breaks.'),

    # Numeric claims without source
    (r'(?:grow|increase|reach|achieve|generate|save|reduce|improve)\s+(?:by\s+)?([\d,.]+\s*[%$]|[\d,.]+\s*(?:million|billion|thousand|users|customers|requests))',
     'unsupported_number', 'critical',
     'Cites a specific number without attribution.',
     'Where does this number come from? If it\'s a guess, label it as one.'),

    # Vague quantifiers
    (r'\b(a lot|many|most|significant|substantial|considerable|numerous|some|various|plenty)\b',
     'vague_quantifier', 'medium',
     'Uses a vague quantifier instead of a specific number.',
     'Replace with a number. If you can\'t, you don\'t understand the scope.'),

    # Passive ownership
    (r'\b(it is (?:expected|assumed|planned|hoped)|should be done|needs to be|ought to be|is supposed to)\b',
     'passive_ownership', 'high',
     'Describes an action without assigning an owner.',
     'WHO does this? No owner = won\'t happen.'),

    # Scope creep signals
    (r'\b(and also|plus|as well as|additionally|along with|not to mention|on top of)\b',
     'scope_creep', 'medium',
     'Signal of scope expansion without explicit approval.',
     'Is this in scope? If not, it\'s free work that delays what matters.'),

    # Dependency as fact
    (r'\b(API|system|service|platform|database|server|third[\s-]party)\s+(returns|provides|supports|handles|allows|delivers|guarantees)\b',
     'external_dependency', 'high',
     'Treats an external dependency as reliable without verification.',
     'What happens when this dependency fails or changes?'),

    # Temporal assumptions
    (r'\b(soon|quickly|immediately|right away|in no time|shortly|promptly|ASAP|before you know it)\b',
     'temporal_assumption', 'medium',
     'Assumes speed without basis.',
     'Define "soon" as a date. If you can\'t, it\'s wishful thinking.'),

    # User behavior assumptions
    (r'\b(users?|customers?|people|they)\s+(will|would|should|can|want|need|expect|prefer|like|love)\b',
     'user_behavior', 'critical',
     'Assumes user behavior without validation.',
     'Have you talked to actual users? If not, this is a guess.'),

    # "Simple" hand-waving
    (r'\b(just|simply|easy|easily|straightforward|trivial|basic|simple)\s+(need|have|add|implement|build|create|set up|configure|integrate|do)\b',
     'complexity_underestimate', 'high',
     'Dismisses implementation complexity.',
     'Nothing is "just simple" in production. What\'s the real scope?'),

    # Cost/resource silence
    (r'\b(launch|release|deploy|roll out|ship|go live)\b',
     'cost_invisible', 'medium',
     'Mentions a milestone without discussing cost/resources needed.',
     'What does this cost in time, money, and people?'),

    # Competition blindness
    (r'\b(unique|first|only|no one else|unprecedented|revolutionary|game[\s-]changing)\b',
     'competition_blind', 'high',
     'Claims uniqueness without competitive analysis.',
     'Are you sure? Search for 5 minutes before betting on this.'),
]

# Risk ordering for filtering
RISK_ORDER = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}


def mine_assumptions(text: str) -> List[Assumption]:
    """Scan text lines and extract assumptions."""
    results = []
    seen = set()  # avoid duplicates on same line

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#') and len(stripped) < 5:
            continue

        for pattern, category, risk, assumption_tmpl, inversion_tmpl in PATTERNS:
            match = re.search(pattern, stripped, re.IGNORECASE)
            if match:
                key = (lineno, category)
                if key in seen:
                    continue
                seen.add(key)

                trigger = match.group(0)
                # Build a human-readable assumption
                assumption_text = f"[{category.upper()}] Line contains '{trigger}'. {assumption_tmpl}"
                inversion_text = inversion_tmpl

                results.append(Assumption(
                    line_number=lineno,
                    line_text=stripped[:200],  # truncate long lines
                    category=category,
                    trigger=trigger,
                    assumption=assumption_text,
                    risk=risk,
                    inverted=inversion_text,
                ))

    # Sort by risk descending
    results.sort(key=lambda a: RISK_ORDER.get(a.risk, 0), reverse=True)
    return results


def format_markdown(assumptions: List[Assumption], source: str) -> str:
    """Format assumptions as markdown."""
    lines = [
        f"# Assumption Register: `{source}`",
        "",
        f"**Mined {len(assumptions)} assumptions.** Below sorted by risk (critical → low).",
        "",
    ]

    risk_counts = {}
    for a in assumptions:
        risk_counts[a.risk] = risk_counts.get(a.risk, 0) + 1

    lines.append("## Risk Summary")
    for r in ['critical', 'high', 'medium', 'low']:
        lines.append(f"- **{r.title()}**: {risk_counts.get(r, 0)}")
    lines.append("")

    current_risk = None
    for a in assumptions:
        if a.risk != current_risk:
            current_risk = a.risk
            lines.append(f"## {current_risk.title()} Risk")
            lines.append("")

        lines.append(f"### L{a.line_number}: [{a.category}] `{a.trigger}`")
        lines.append(f"> {a.line_text}")
        lines.append(f"- **Assumption**: {a.assumption}")
        lines.append(f"- **Inversion**: {a.inverted}")
        lines.append("")

    if not assumptions:
        lines.append("## Clean Bill of Health")
        lines.append("")
        lines.append("No obvious assumptions detected. Either the document is bulletproof, "
                      "or the heuristics need sharpening.")
        lines.append("")

    return "\n".join(lines)


def format_json(assumptions: List[Assumption], source: str) -> str:
    """Format assumptions as JSON."""
    return json.dumps({
        "source": source,
        "total": len(assumptions),
        "risk_counts": {
            r: sum(1 for a in assumptions if a.risk == r)
            for r in ['critical', 'high', 'medium', 'low']
        },
        "assumptions": [asdict(a) for a in assumptions],
    }, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="KILLJOY's Assumption Miner — Extract hidden assumptions from markdown."
    )
    parser.add_argument("file", help="Path to markdown file to mine")
    parser.add_argument("--format", choices=["json", "md"], default="md",
                        help="Output format (default: md)")
    parser.add_argument("--min-risk", choices=["low", "medium", "high", "critical"],
                        default="low",
                        help="Minimum risk level to include (default: low)")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")

    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    assumptions = mine_assumptions(text)

    # Filter by minimum risk
    min_level = RISK_ORDER[args.min_risk]
    assumptions = [a for a in assumptions if RISK_ORDER[a.risk] >= min_level]

    if args.format == "json":
        output = format_json(assumptions, str(path))
    else:
        output = format_markdown(assumptions, str(path))

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
