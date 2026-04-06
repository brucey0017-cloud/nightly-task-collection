# 🔪 Pre-Mortem Assumption Hunter

A zero-dependency Python 3 CLI tool that tears apart any plan/proposal by exposing hidden assumptions, weasel words, and the single most lethal question you should be asking.

Built by KILLJOY (首席质疑官) as a personal weapon for stress-testing plans before they die in production.

## What It Does

1. **Lethal Question** — Identifies the single most dangerous question to ask about your plan
2. **Pre-Mortem Scenarios** — Imagines the project has already failed and tells you how it died
3. **Hidden Assumptions** — Pattern-matches 14 categories of implicit assumptions you didn't state out loud
4. **Weasel Words** — Flags hedging language that masks lack of evidence
5. **Risk Density Score** — Quantifies how assumption-heavy your plan is

## Usage

```bash
# Analyze a plan file
python3 premortem.py plan.md

# Pipe from stdin
echo "We'll launch by Q3 and expect 10K users" | python3 premortem.py -

# Get JSON output
python3 premortem.py plan.md --json
```

## Risk Categories

| Category | What it catches |
|----------|----------------|
| 🟡 Market | "Users will come" (will they?) |
| 🔴 Execution | "We'll build it" (on time?) |
| 🟠 Scale | "Works at 1x" (what about 10x?) |
| 💰 Financial | Revenue projections that feel aspirational |
| 🔗 Dependency | Third-party APIs that you don't control |
| ⚖️ Compliance | Legal landmines |
| ⚔️ Competition | "No competitors" (really?) |
| ⏰ Timeline | Deadlines that are wishes |
| 🌀 Complexity | Things labeled "simple" |
| 📐 Scope | MVP that will creep |
| ⚡ Technology | AI/ML that works in demos |

## Test

```bash
python3 premortem.py sample-plan.md
```

## Philosophy

> "Every plan has a fatal flaw. My job is to find it before it kills the project."
> — KILLJOY
