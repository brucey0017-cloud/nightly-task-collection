#!/usr/bin/env python3
"""
premortem.py — KILLJOY's Pre-Mortem Stress Tester

Reads a project plan / decision doc (markdown or plain text) and generates
a structured pre-mortem analysis: assumption extraction, failure modes,
and risk severity scoring. Zero external dependencies.

Usage:
    python3 premortem.py <file> [--format markdown|json] [--verbose]
    python3 premortem.py --inline "We will launch a SaaS product in Q3 targeting SMBs"
    cat plan.md | python3 premortem.py -
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


# ── Data structures ──────────────────────────────────────────────────

@dataclass
class Assumption:
    """An implicit or explicit assumption found in the text."""
    raw_text: str
    category: str  # market | technical | resource | timeline | user | regulatory | competitive
    confidence: str  # high | medium | low (how likely this assumption is wrong)
    inversion: str  # what happens if this assumption is false
    fatal: bool = False  # would this kill the project?

    def to_dict(self):
        return {
            "assumption": self.raw_text,
            "category": self.category,
            "confidence_risk": self.confidence,
            "inversion": self.inversion,
            "fatal": self.fatal,
        }


@dataclass
class FailureMode:
    """A specific way the project could fail."""
    name: str
    description: str
    risk_type: str  # market | execution | external
    severity: int  # 1-5
    likelihood: int  # 1-5
    mitigation_hint: str = ""

    @property
    def score(self) -> int:
        return self.severity * self.likelihood

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "risk_type": self.risk_type,
            "severity": self.severity,
            "likelihood": self.likelihood,
            "risk_score": self.score,
            "mitigation_hint": self.mitigation_hint,
        }


@dataclass
class PremortemReport:
    assumptions: List[Assumption] = field(default_factory=list)
    failure_modes: List[FailureMode] = field(default_factory=list)
    overall_risk: str = "UNKNOWN"
    summary: str = ""

    def to_dict(self):
        return {
            "overall_risk": self.overall_risk,
            "summary": self.summary,
            "assumptions": [a.to_dict() for a in self.assumptions],
            "failure_modes": sorted(
                [f.to_dict() for f in self.failure_modes],
                key=lambda x: x["risk_score"],
                reverse=True,
            ),
        }


# ── Pattern-based assumption extraction ──────────────────────────────

# Signal phrases that often indicate assumptions
ASSUMPTION_PATTERNS = [
    # (pattern, category, typical confidence of being wrong)
    (r"(?:we |our |the )?(?:will|plan to|are going to|intend to)\s+(?:launch|release|ship|deploy|roll out|go live)", "timeline", "medium"),
    (r"(?:users?|customers?|clients?|people)\s+(?:will|would|should|can|want to|need to)\s+", "user", "medium"),
    (r"(?:market|industry|sector)\s+(?:will|is|are|has|growing|expanding)", "market", "medium"),
    (r"(?:expect|expecting|anticipate|projected|forecast)\s+", "market", "medium"),
    (r"(?:assume|assuming|presume|presuming|take it that)\s+", "market", "high"),
    (r"(?:should|ought to)\s+(?:be able to|work|handle|support|scale)", "technical", "medium"),
    (r"(?:can|could|will)\s+(?:handle|support|scale|accommodate|process)\s+", "technical", "medium"),
    (r"(?:API|service|server|database|infra|platform|system)\s+(?:will|can|should)\s+", "technical", "medium"),
    (r"(?:budget|cost|spend|investment|funding)\s+(?:is|of|at|around)\s+", "resource", "medium"),
    (r"(?:team|staff|hire|hiring|engineers?|developers?)\s+(?:will|can|of)\s+", "resource", "medium"),
    (r"(?:compliant|compliance|regulation|legal|GDPR|privacy|security)\s*", "regulatory", "low"),
    (r"(?:competitor|competition|rival|alternative)\s+", "competitive", "medium"),
    (r"(?:simple|easy|straightforward|quick|fast|just|trivial)\s+", "execution", "high"),
    (r"(?:MVP|minimum viable|phase 1|first version|v1|initial)\s+", "execution", "medium"),
    (r"(?:integrate|integration|connect|third.?party|vendor)\s+", "technical", "medium"),
    (r"(?:convert|conversion|retention|engagement|churn)\s+(?:rate|will)\s*", "market", "high"),
    (r"(?:revenue|profit|margin|ARR|MRR|GMV)\s+", "market", "high"),
    (r"(?:schedule|deadline|deadline|Q[1-4]|month|quarter)\s+", "timeline", "medium"),
]

# Weasel words that inflate risk
WEASEL_PATTERNS = [
    r"\b(?:probably|likely|hopefully|should be fine|should work|famous last words)\b",
    r"\b(?:I think|I believe|I feel|I guess|I hope)\b",
    r"\b(?:everyone knows|obviously|clearly|it goes without saying)\b",
    r"\b(?:just|simply|merely|all we need to do)\b",
    r"\b(?:TBD|TBA|TODO|FIXME|XXX)\b",
]


def extract_assumptions(text: str) -> List[Assumption]:
    """Extract assumptions from text using pattern matching."""
    assumptions = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    seen = set()

    for pattern, category, confidence in ASSUMPTION_PATTERNS:
        for sentence in sentences:
            if re.search(pattern, sentence, re.IGNORECASE):
                normalized = sentence.strip().lower()[:80]
                if normalized in seen:
                    continue
                seen.add(normalized)

                # Generate inversion
                inversion = generate_inversion(sentence, category)

                # Determine if fatal
                fatal = confidence == "high" or category in ("regulatory",)

                assumptions.append(Assumption(
                    raw_text=sentence.strip(),
                    category=category,
                    confidence=confidence,
                    inversion=inversion,
                    fatal=fatal,
                ))

    return assumptions


def generate_inversion(sentence: str, category: str) -> str:
    """Generate the 'what if this is wrong' inversion."""
    inversions = {
        "market": "What if the market doesn't behave as expected? No one shows up.",
        "user": "What if users don't behave this way? They ignore it or hate it.",
        "technical": "What if the tech doesn't hold up? It breaks at the worst moment.",
        "resource": "What if resources run short? You can't finish what you started.",
        "timeline": "What if it takes 3x longer? The window closes.",
        "regulatory": "What if compliance blocks you? Forced to stop or redesign.",
        "competitive": "What if competitors move faster or undercut you?",
        "execution": "What if 'simple' turns out to be anything but? Scope creep kills the timeline.",
    }
    return inversions.get(category, "What if this assumption is simply wrong?")


def count_weasel_words(text: str) -> List[str]:
    """Find weasel words/phrases that signal hand-waving."""
    found = []
    for pattern in WEASEL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found.extend([m.strip() for m in matches])
    return found


# ── Failure mode generation ──────────────────────────────────────────

def generate_failure_modes(assumptions: List[Assumption], text: str) -> List[FailureMode]:
    """Generate failure modes from extracted assumptions and text."""
    modes = []

    # Group assumptions by category for systematic failure analysis
    by_category = {}
    for a in assumptions:
        by_category.setdefault(a.category, []).append(a)

    # Market failures
    market_assumptions = by_category.get("market", [])
    if market_assumptions or any(w in text.lower() for w in ["launch", "product", "feature", "users"]):
        modes.append(FailureMode(
            name="Nobody Wants It",
            description="The market doesn't respond. Users don't sign up, don't convert, don't stay. "
                        "The most common startup cause of death.",
            risk_type="market",
            severity=5,
            likelihood=3,
            mitigation_hint="Validate with real users before building. Landing page test, smoke test, pre-sales.",
        ))

    # User behavior failures
    user_assumptions = by_category.get("user", [])
    if user_assumptions:
        modes.append(FailureMode(
            name="Users Don't Behave As Expected",
            description=f"Found {len(user_assumptions)} user-behavior assumptions. "
                        "Each one that's wrong changes the product requirements.",
            risk_type="market",
            severity=4,
            likelihood=3,
            mitigation_hint="User interviews, prototype testing, analytics from day 1.",
        ))

    # Technical failures
    tech_assumptions = by_category.get("technical", [])
    if tech_assumptions:
        modes.append(FailureMode(
            name="Technical Overreach",
            description=f"Found {len(tech_assumptions)} technical assumptions. "
                        "Architecture that works in demo often breaks in production.",
            risk_type="execution",
            severity=4,
            likelihood=3,
            mitigation_hint="Load test early. Have a degradation plan. Don't over-engineer for day 1.",
        ))

    # Timeline failures
    timeline_assumptions = by_category.get("timeline", [])
    weasels = count_weasel_words(text)
    if timeline_assumptions or weasels:
        modes.append(FailureMode(
            name="Timeline Delusion",
            description=f"Found {len(timeline_assumptions)} timeline assumptions and {len(weasels)} weasel-word signals. "
                        "Plans are always optimistic. 'Just' is the most dangerous word in engineering.",
            risk_type="execution",
            severity=3,
            likelihood=4,
            mitigation_hint="Apply a 2-3x buffer. Cut scope ruthlessly. Ship something small first.",
        ))

    # Resource failures
    resource_assumptions = by_category.get("resource", [])
    if resource_assumptions:
        modes.append(FailureMode(
            name="Resource Exhaustion",
            description="Budget or team runs out before the finish line. "
                        "The last 20% takes 80% of the resources.",
            risk_type="execution",
            severity=4,
            likelihood=3,
            mitigation_hint="Calculate cost to completion, not cost to start. Have a runway margin.",
        ))

    # Regulatory failures
    reg_assumptions = by_category.get("regulatory", [])
    if reg_assumptions:
        modes.append(FailureMode(
            name="Compliance Landmine",
            description="Regulatory requirements discovered too late. "
                        "Retro-fitting compliance costs 10x more than building it in.",
            risk_type="external",
            severity=5,
            likelihood=2,
            mitigation_hint="Legal review before architecture decisions, not after.",
        ))

    # Competitive response
    comp_assumptions = by_category.get("competitive", [])
    if comp_assumptions or len(text) > 500:
        modes.append(FailureMode(
            name="Competitive Counter-Move",
            description="A competitor sees what you're doing and responds. "
                        "Speed is the only defense against incumbents.",
            risk_type="external",
            severity=3,
            likelihood=3,
            mitigation_hint="What's your 6-month moat? If the answer is 'nothing', reconsider the approach.",
        ))

    # Scope creep (always relevant for plans)
    if any(w in text.lower() for w in ["phase", "v1", "mvp", "later", "future", "roadmap"]):
        modes.append(FailureMode(
            name="Scope Creep",
            description="'We'll add that later' becomes 'we need that now'. "
                        "Every feature added before launch delays launch.",
            risk_type="execution",
            severity=4,
            likelihood=4,
            mitigation_hint="Write down what's NOT in scope. Refer to it every time someone says 'just one more thing'.",
        ))

    # Dependency risk
    if any(w in text.lower() for w in ["integrate", "api", "third-party", "vendor", "partner", "depend"]):
        modes.append(FailureMode(
            name="Third-Party Dependency Failure",
            description="External API changes pricing, goes down, deprecates features, or disappears. "
                        "You don't control their roadmap.",
            risk_type="external",
            severity=4,
            likelihood=2,
            mitigation_hint="Abstract external dependencies. Have fallback paths. Never single-source a critical dependency.",
        ))

    # If very few modes generated, add generic ones
    if len(modes) < 3:
        modes.append(FailureMode(
            name="Unknown Unknowns",
            description="The plan doesn't have enough detail to identify specific risks. "
                        "That itself is a risk — vagueness hides fatal flaws.",
            risk_type="execution",
            severity=3,
            likelihood=3,
            mitigation_hint="Write a more detailed plan. Specifics expose assumptions.",
        ))

    return modes


# ── Risk scoring ──────────────────────────────────────────────────────

def calculate_overall_risk(modes: List[FailureMode], assumptions: List[Assumption]) -> str:
    """Calculate overall risk level."""
    if not modes:
        return "UNKNOWN — no failure modes detected. The plan may be too vague to analyze."

    max_score = max(m.score for m in modes)
    fatal_count = sum(1 for a in assumptions if a.fatal)
    total_risk_score = sum(m.score for m in modes)

    if max_score >= 20 or fatal_count >= 3:
        return "CRITICAL — multiple high-severity failure modes. Do not proceed without addressing these."
    elif max_score >= 12 or fatal_count >= 1:
        return "HIGH — significant risks identified. Stress-test before committing resources."
    elif max_score >= 6 or total_risk_score >= 20:
        return "MODERATE — manageable risks. Mitigate top 3 before launch."
    else:
        return "LOW — risks are minor. Proceed with standard monitoring."


# ── Report generation ────────────────────────────────────────────────

def generate_summary(report: PremortemReport, weasels: List[str], source: str) -> str:
    """Generate a KILLJOY-style summary."""
    lines = []
    lines.append("## Pre-Mortem Analysis")
    lines.append(f"**Source:** {source}")
    lines.append("")

    # Assumptions found
    lines.append(f"### Assumptions Found: {len(report.assumptions)}")
    if report.assumptions:
        fatal = [a for a in report.assumptions if a.fatal]
        lines.append(f"- **Potentially fatal:** {len(fatal)}")
        by_cat = {}
        for a in report.assumptions:
            by_cat.setdefault(a.category, []).append(a)
        for cat, items in sorted(by_cat.items()):
            lines.append(f"- **{cat}:** {len(items)} assumption(s)")
    lines.append("")

    # Weasel words
    if weasels:
        lines.append(f"### 🚩 Weasel Words Detected: {len(weasels)}")
        unique = list(dict.fromkeys(weasels))[:10]
        for w in unique:
            lines.append(f'- "{w}"')
        lines.append("")
        lines.append("> These are hand-waving signals. Each one is a gap between hope and evidence.")
        lines.append("")

    # Failure modes
    lines.append(f"### Failure Modes: {len(report.failure_modes)}")
    sorted_modes = sorted(report.failure_modes, key=lambda m: m.score, reverse=True)
    for i, mode in enumerate(sorted_modes, 1):
        risk_bar = "█" * mode.severity + "░" * (5 - mode.severity)
        like_bar = "█" * mode.likelihood + "░" * (5 - mode.likelihood)
        lines.append(f"")
        lines.append(f"**{i}. {mode.name}** (score: {mode.score})")
        lines.append(f"- Type: {mode.risk_type}")
        lines.append(f"- Severity: {risk_bar} ({mode.severity}/5)")
        lines.append(f"- Likelihood: {like_bar} ({mode.likelihood}/5)")
        lines.append(f"- {mode.description}")
        if mode.mitigation_hint:
            lines.append(f"- 💡 {mode.mitigation_hint}")
    lines.append("")

    # Overall verdict
    lines.append(f"### Overall Risk: {report.overall_risk}")
    lines.append("")

    # KILLJOY verdict
    max_score = max((m.score for m in report.failure_modes), default=0)
    if max_score >= 20:
        lines.append("🔪 **KILLJOY says:** This plan has fatal gaps. Fix them or don't start. "
                      "\"Fail fast\" only works if you learn from it — and right now the lessons are predictable.")
    elif max_score >= 12:
        lines.append("🔪 **KILLJOY says:** I found real risks. Not dealbreakers, but they'll break you if ignored. "
                      "Address the top 3 before writing a single line of code.")
    elif max_score >= 6:
        lines.append("🔪 **KILLJOY says:** Manageable. I've seen worse. But \"manageable\" doesn't mean \"ignore\" — "
                      "mitigate the top risks and keep watching.")
    else:
        lines.append("🔪 **KILLJOY says:** I can't find much to hit. Either this plan is genuinely solid, "
                      "or it's too vague to analyze. My money's on the latter. Add more specifics and run me again.")

    return "\n".join(lines)


# ── Main pipeline ────────────────────────────────────────────────────

def run_premortem(text: str, source: str = "inline") -> PremortemReport:
    """Run full pre-mortem analysis on text."""
    assumptions = extract_assumptions(text)
    failure_modes = generate_failure_modes(assumptions, text)
    overall_risk = calculate_overall_risk(failure_modes, assumptions)

    report = PremortemReport(
        assumptions=assumptions,
        failure_modes=failure_modes,
        overall_risk=overall_risk,
    )

    weasels = count_weasel_words(text)
    report.summary = generate_summary(report, weasels, source)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="KILLJOY's Pre-Mortem Stress Tester — Find the fatal flaw before it finds you."
    )
    parser.add_argument("file", nargs="?", help="Input file (markdown/text), or '-' for stdin")
    parser.add_argument("--inline", "-i", help="Analyze inline text instead of file")
    parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown",
                        help="Output format (default: markdown)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show raw assumption extractions")

    args = parser.parse_args()

    # Get text
    if args.inline:
        text = args.inline
        source = "inline"
    elif args.file == "-":
        text = sys.stdin.read()
        source = "stdin"
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"🔪 File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8")
        source = str(path)
    else:
        parser.print_help()
        print("\n🔪 You gave me nothing to analyze. That's the most dangerous plan of all.", file=sys.stderr)
        sys.exit(1)

    if not text.strip():
        print("🔪 Empty input. Even a blank page has a risk: someone will fill it with bullshit.", file=sys.stderr)
        sys.exit(1)

    # Run analysis
    report = run_premortem(text, source)

    # Output
    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(report.summary)

    if args.verbose and report.assumptions:
        print("\n--- Raw Assumption Extractions ---")
        for a in report.assumptions:
            print(f"  [{a.category}] ({a.confidence}) {a.raw_text[:100]}")
            print(f"    Inversion: {a.inversion}")
            print(f"    Fatal: {a.fatal}")
            print()


if __name__ == "__main__":
    main()
