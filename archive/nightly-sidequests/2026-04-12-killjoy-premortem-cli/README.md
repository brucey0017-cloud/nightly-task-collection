# premortem-cli — KILLJOY's Pre-Mortem Stress Tester

> "The plan looks great. Now let me show you how it dies." — KILLJOY

A zero-dependency Python 3 CLI that reads a project plan or decision document and generates a structured **pre-mortem analysis**: assumption extraction, failure-mode scoring, and weasel-word detection.

## What It Does

1. **Extracts assumptions** — Scans text for 18 signal patterns across 8 categories (market, user, technical, resource, timeline, regulatory, competitive, execution)
2. **Generates failure modes** — Maps assumptions to concrete ways the project could die, with severity/likelihood scoring
3. **Detects weasel words** — Flags hand-waving language ("just", "should be fine", "everyone knows", "simply")
4. **Produces risk verdict** — CRITICAL / HIGH / MODERATE / LOW with KILLJOY-style commentary

## Usage

```bash
# Analyze a file (markdown output)
python3 -m premortem plan.md

# Analyze inline text
python3 -m premortem --inline "We will launch a SaaS product targeting SMBs"

# JSON output for piping
python3 -m premortem plan.md -f json

# Pipe stdin
cat plan.md | python3 -m premortem -

# Verbose mode (show raw assumption extractions)
python3 -m premortem plan.md -v
```

## Output Example

```
## Pre-Mortem Analysis
**Source:** plan.md

### Assumptions Found: 11
- **Potentially fatal:** 1
- **execution:** 3 assumption(s)
- **market:** 2 assumption(s)
- **technical:** 3 assumption(s)

### 🚩 Weasel Words Detected: 2
- "Everyone knows"
- "just"

### Failure Modes: 8
**1. Scope Creep** (score: 16)
- Severity: ████░ (4/5)
- Likelihood: ████░ (4/5)
...

### Overall Risk: HIGH
🔪 **KILLJOY says:** I found real risks. Not dealbreakers, but they'll break you if ignored.
```

## Why This Exists

Every plan has fatal assumptions. Most teams don't find them until it's too late. This tool automates the systematic skepticism that KILLJOY applies manually — pattern-based assumption hunting, inversion testing, and failure-mode scoring.

It won't replace human judgment. But it'll catch the obvious gaps before you commit resources to a plan built on hope.

## Files

- `premortem.py` — Main script (self-contained, zero dependencies)
- `test_input.md` — Sample project plan for testing
- `README.md` — This file
