#!/usr/bin/env python3
"""
premortem.py — Pre-Mortem Assumption Hunter
Feed it a plan (file or stdin), get a structured risk teardown.

Usage:
    python3 premortem.py plan.md
    python3 premortem.py < plan.md
    echo "We'll launch a SaaS by Q3" | python3 premortem.py -

KILLJOY's personal weapon. Zero dependencies. Pure Python 3.
"""

import sys
import re
import json
import textwrap
from pathlib import Path
from datetime import datetime


# ── Heuristic assumption extractors ──────────────────────────────────────────

WEASEL_WORDS = [
    "should", "probably", "likely", "assume", "assumption", "expect",
    "might", "could", "hopefully", "ideally", "plan to", "planning to",
    "will", "going to", "aim to", "intend to", "believe",
]

IMPLICIT_ASSUMPTION_PATTERNS = [
    # (pattern, category, assumption_template)
    (r"\b(launch|release|ship)\b", "execution", "Timeline is realistic and no blockers will delay {match}."),
    (r"\b(scal[e|ing]|growth|grow)\b", "scale", "Current architecture handles {match} without rework."),
    (r"\b(user[s]?\b|customer[s]?\b|adopt)", "market", "Users actually want this and will {match}."),
    (r"\b(budget|fund|invest|cost|revenue)", "financial", "Financial projections in the plan are grounded, not aspirational."),
    (r"\b(API|integration|third.party|vendor)", "dependency", "External dependency ({match}) will be available, stable, and won't change terms."),
    (r"\b(hire|recruit|team|headcount)", "execution", "Required talent is available and will join on schedule."),
    (r"\b(secur|compl[i|y]|regul|legal)", "compliance", "Compliance requirements are fully understood, not partially."),
    (r"\b(compet|market|rival)", "competition", "Competitors won't react faster or undercut the plan."),
    (r"\b(test|QA|quality|bug)", "execution", "Testing coverage is sufficient; edge cases won't kill the launch."),
    (r"\b(deadline|milestone|Q[1-4]|by \w+ \d)", "timeline", "The deadline is a real constraint, not an aspiration."),
    (r"\b(simple|easy|straightforward|just)", "complexity", "'{match}' is genuinely simple, not hiding complexity."),
    (r"\b(MVP|mvp|minimum|baseline)", "scope", "The MVP scope won't creep before launch."),
    (r"\b(automat|AI|ML|machine learning)", "technology", "The AI/automation will work reliably, not just in demos."),
    (r"\b(convert|conversion|signup|regist)", "market", "Conversion assumptions are based on data, not gut feeling."),
]

RISK_CATEGORIES = {
    "market": "🟡 Market Risk — Nobody wants it",
    "execution": "🔴 Execution Risk — Can't build it in time / at all",
    "scale": "🟠 Scale Risk — Works at 1x, dies at 10x",
    "financial": "💰 Financial Risk — Money runs out or never arrives",
    "dependency": "🔗 Dependency Risk — External factor you don't control",
    "compliance": "⚖️ Compliance Risk — Legal / regulatory landmine",
    "competition": "⚔️ Competition Risk — Someone else does it better / faster",
    "timeline": "⏰ Timeline Risk — Dates are wishes, not commitments",
    "complexity": "🌀 Complexity Risk — 'Simple' things that aren't",
    "scope": "📐 Scope Risk — Requirements will expand",
    "technology": "⚡ Technology Risk — The tech doesn't work as promised",
}


def extract_text(source: str) -> str:
    """Read from file or stdin."""
    if source == "-" or source is None:
        return sys.stdin.read()
    p = Path(source)
    if not p.exists():
        print(f"ERROR: File not found: {source}", file=sys.stderr)
        sys.exit(1)
    return p.read_text(encoding="utf-8")


def find_weasel_sentences(text: str) -> list[dict]:
    """Find sentences containing weasel/ungrounded words."""
    sentences = re.split(r'[.!?\n]', text)
    results = []
    for s in sentences:
        s = s.strip()
        if len(s) < 10:
            continue
        found_words = [w for w in WEASEL_WORDS if re.search(rf'\b{w}\b', s, re.IGNORECASE)]
        if found_words:
            results.append({
                "sentence": s[:200],
                "weasel_words": found_words,
                "risk": "Ungrounded assumption — no evidence provided",
            })
    return results


def find_implicit_assumptions(text: str) -> list[dict]:
    """Pattern-match for implicit assumptions."""
    results = []
    seen = set()
    for pattern, category, template in IMPLICIT_ASSUMPTION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            key = (category, m.group().lower()[:40])
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "category": category,
                "trigger": m.group(),
                "assumption": template.format(match=m.group()),
            })
    return results


def compute_lethal_question(assumptions: list[dict], weasels: list[dict]) -> str:
    """Pick the single most dangerous question based on risk density."""
    if not assumptions and not weasels:
        return "⚠️  No detectable assumptions — either the plan is bulletproof or it's too vague to analyze."

    # Score by category density
    cat_counts = {}
    for a in assumptions:
        cat_counts[a["category"]] = cat_counts.get(a["category"], 0) + 1
    cat_counts["weasel"] = len(weasels)

    # The most frequent risk category is probably the weakest point
    if cat_counts:
        top_cat = max(cat_counts, key=cat_counts.get)
    else:
        top_cat = "execution"

    lethal_questions = {
        "market": "If zero users show up on day one, what's your plan B? Do you have one?",
        "execution": "You've listed what needs to happen. What happens when it doesn't?",
        "scale": "This works for the first 100 users. What breaks at 10,000?",
        "financial": "Run the numbers with half the revenue and double the costs. Still alive?",
        "dependency": "If your biggest external dependency disappears tomorrow, how many days until you're dead in the water?",
        "compliance": "Have you talked to someone who's actually been through a compliance audit, or are you assuming it'll be fine?",
        "competition": "A well-funded competitor launches the same thing in 3 months. What's your moat?",
        "timeline": "Every deadline in this plan is a guess. Which one, if missed, kills the whole thing?",
        "complexity": "Strip out everything marked 'simple.' What's left? Is it enough?",
        "scope": "What's the ONE thing you'll cut when scope creeps? (You will cut something.)",
        "technology": "If the core tech doesn't work as advertised, what's the fallback?",
        "weasel": "Half your plan is hedging language. Which 'should' are you actually betting the company on?",
    }

    return lethal_questions.get(top_cat, "What's the ONE assumption that, if wrong, makes the rest of the plan irrelevant?")


def generate_pretext_scenarios(assumptions: list[dict]) -> list[str]:
    """Generate pre-mortem failure scenarios."""
    scenarios = []
    category_deaths = {
        "market": "🎉 Launch day comes. Crickets. The press release is out, the product works, and literally nobody cares.",
        "execution": "🚨 Three weeks before deadline, the lead developer quits. The codebase has no documentation. Happy onboarding.",
        "scale": "💥 The product goes viral — and takes down the entire infrastructure in 4 hours. Users see 500 errors and tweet about it.",
        "financial": "💸 The runway calculation was optimistic. You have 6 weeks of cash, not 6 months. The next funding round just got pushed.",
        "dependency": "🔌 The third-party API you built everything on top of changes its pricing model. Costs 10x overnight.",
        "compliance": "📜 A regulator sends a letter. Turns out that 'we'll deal with compliance later' later is now.",
        "competition": "🎯 The competitor you didn't take seriously launches first. With better marketing. And a lower price.",
        "timeline": "⏳ The deadline was Q3. It's now Q4. The board wants to know what happened to Q3.",
        "complexity": "🕳️ That 'simple integration' required rearchitecting the entire backend. Nobody saw it coming. Except someone should have.",
        "scope": "📈 MVP scope has doubled since the kickoff meeting. Nobody remembers what 'minimum' meant anymore.",
        "technology": "🤖 The AI demo worked perfectly. In production, it's wrong 30% of the time. Users are furious.",
    }

    seen_cats = set()
    for a in assumptions:
        cat = a["category"]
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        if cat in category_deaths:
            scenarios.append(category_deaths[cat])

    return scenarios[:5]  # Top 5


def format_report(text: str) -> str:
    """Run full analysis and format output."""
    lines = []
    lines.append("=" * 70)
    lines.append("🔪 PRE-MORTEM ASSUMPTION HUNTER — KILLJOY EDITION")
    lines.append(f"   Generated: {datetime.utcnow().isoformat()}Z")
    lines.append("=" * 70)

    # Extract
    weasels = find_weasel_sentences(text)
    assumptions = find_implicit_assumptions(text)

    # Section 1: Lethal Question (front and center)
    lines.append("")
    lines.append("━" * 70)
    lines.append("💀 THE LETHAL QUESTION")
    lines.append("━" * 70)
    lethal = compute_lethal_question(assumptions, weasels)
    lines.append("")
    lines.append(f"   {lethal}")
    lines.append("")

    # Section 2: Pre-Mortem Scenarios
    scenarios = generate_pretext_scenarios(assumptions)
    if scenarios:
        lines.append("━" * 70)
        lines.append("⚰️  PRE-MORTEM: HOW THIS DIES")
        lines.append("━" * 70)
        lines.append("")
        lines.append("   Imagine the project has already failed. Here's how:")
        lines.append("")
        for i, s in enumerate(scenarios, 1):
            lines.append(f"   {i}. {s}")
        lines.append("")

    # Section 3: Hidden Assumptions
    if assumptions:
        lines.append("━" * 70)
        lines.append("🎯 HIDDEN ASSUMPTIONS (you didn't say these out loud)")
        lines.append("━" * 70)
        lines.append("")
        # Group by category
        by_cat = {}
        for a in assumptions:
            by_cat.setdefault(a["category"], []).append(a)
        for cat, items in sorted(by_cat.items()):
            label = RISK_CATEGORIES.get(cat, cat)
            lines.append(f"   {label}")
            for item in items:
                lines.append(f"      • [{item['trigger']}] → {item['assumption']}")
            lines.append("")

    # Section 4: Weasel Words
    if weasels:
        lines.append("━" * 70)
        lines.append("🐀 WEASEL WORDS (hedges that hide lack of evidence)")
        lines.append("━" * 70)
        lines.append("")
        for w in weasels[:10]:  # Cap at 10
            words = ", ".join(w["weasel_words"])
            lines.append(f"   [{words}] \"{w['sentence'][:100]}...\"")
        if len(weasels) > 10:
            lines.append(f"   ... and {len(weasels) - 10} more")
        lines.append("")

    # Section 5: Summary
    lines.append("━" * 70)
    lines.append("📊 RISK DENSITY")
    lines.append("━" * 70)
    lines.append("")
    cat_counts = {}
    for a in assumptions:
        cat_counts[a["category"]] = cat_counts.get(a["category"], 0) + 1
    if weasels:
        cat_counts["weasel"] = len(weasels)

    total = sum(cat_counts.values())
    lines.append(f"   Total assumptions flagged: {total}")
    if cat_counts:
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            bar = "█" * count + "░" * (max(cat_counts.values()) - count)
            label = RISK_CATEGORIES.get(cat, cat).split("—")[0].strip()
            lines.append(f"   {label:20s} {bar} {count}")
    lines.append("")

    # Verdict
    if total == 0:
        verdict = "⚠️  Nothing found. Either this plan is bulletproof, or it's too vague to analyze. I'd bet on the latter."
    elif total <= 3:
        verdict = "🟢 Low risk density. A few assumptions worth validating, but no red flags screaming."
    elif total <= 8:
        verdict = "🟡 Medium risk density. Several unvalidated assumptions. Stress-test the top 2 before proceeding."
    elif total <= 15:
        verdict = "🔴 High risk density. This plan is built on a stack of untested assumptions. Validate before you build."
    else:
        verdict = "💀 Critical risk density. This isn't a plan — it's a wish list with a deadline. Stop. Validate. Then plan."

    lines.append(f"   Verdict: {verdict}")
    lines.append("")
    lines.append("=" * 70)
    lines.append("   \"If you can't find the fatal flaw, you're not looking hard enough.\"")
    lines.append("    — KILLJOY, Chief Skeptic Officer")
    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    if len(sys.argv) > 1:
        source = sys.argv[1]
    else:
        source = None

    text = extract_text(source)
    if not text.strip():
        print("ERROR: Empty input. Provide a file path or pipe text via stdin.", file=sys.stderr)
        sys.exit(1)

    report = format_report(text)
    print(report)

    # Also support JSON output
    if "--json" in sys.argv:
        weasels = find_weasel_sentences(text)
        assumptions = find_implicit_assumptions(text)
        output = {
            "lethal_question": compute_lethal_question(assumptions, weasels),
            "scenarios": generate_pretext_scenarios(assumptions),
            "assumptions": assumptions,
            "weasel_sentences": weasels,
            "risk_density": len(assumptions) + len(weasels),
        }
        print("\n--- JSON ---\n")
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
