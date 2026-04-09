# premortem — KILLJOY's Pre-Mortem Attack Tool 🔪

A zero-dependency Python 3 CLI that reads any plan document (markdown) and generates a structured pre-mortem analysis using the **5-Layer Attack Framework**.

## What It Does

Given a plan/proposal document, it:
1. **Extracts assumptions** — finds explicit claims, implicit dependencies, user behavior predictions, and normative statements
2. **Classifies risk domains** — scores text against market, execution, technical, external, and financial risk
3. **Runs 5-layer attack** — generates targeted questions for each attack vector
4. **Delivers a verdict** — RED FLAG / CAUTION / PROCEED WITH EYES OPEN / INSUFFICIENT DATA

## The 5 Attack Layers

| # | Layer | Core Question |
|---|-------|---------------|
| 1 | Premise Attack | What assumptions is this built on? Are they verified? |
| 2 | Counterfactual | If the core assumption is wrong, does the plan survive? |
| 3 | Competition | Would competitors laugh or fear this? |
| 4 | Scale | Does this hold at 10x? |
| 5 | Time | Will we regret this in 6 months? |

## Usage

```bash
# Basic — markdown report
python3 premortem.py plan.md

# JSON output (for piping/automation)
python3 premortem.py plan.md --json

# Filter to specific attack layer
python3 premortem.py plan.md --layer 3

# Show only high-severity and above assumptions
python3 premortem.py plan.md --severity high
```

## Output

Markdown report with:
- **Verdict** with severity assessment
- **Extracted Assumptions** with severity ratings (🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low)
- **5-Layer Attack Analysis** with targeted questions per layer

## Design Principles

- **Zero dependencies** — pure Python 3 stdlib
- **Opinionated** — doesn't hedge. Uses KILLJOY's decision framework, not generic risk analysis
- **Composable** — JSON output for integration into CI/automation pipelines
- **Fast** — runs in milliseconds, no API calls

## When to Use

- Before approving any project proposal
- During sprint planning for new initiatives
- As a pre-commit hook for PRs that change architecture
- When a plan feels too good to be true (it usually is)

> "Be the critic you'd want stress-testing your plan at 2am."
