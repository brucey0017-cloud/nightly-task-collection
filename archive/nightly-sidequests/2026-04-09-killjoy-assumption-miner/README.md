# 🔪 assumption-miner

**KILLJOY's weaponized paranoia.** A zero-dependency Python 3 CLI that reads any markdown file and extracts hidden assumptions using heuristic pattern matching.

## What It Does

Scans markdown for 13 categories of risky statements:

| Category | Risk | What It Catches |
|----------|------|-----------------|
| `future_prediction` | 🔴 High | "will support", "shall deliver" |
| `unsupported_number` | 🔴 Critical | "grow by 300%", "$10M market" — no source |
| `user_behavior` | 🔴 Critical | "Users will love..." — no validation |
| `absolute_claim` | 🔴 High | "always", "never", "guaranteed" |
| `competition_blind` | 🔴 High | "unique", "revolutionary", "first" |
| `external_dependency` | 🔴 High | "API returns..." — treated as fact |
| `passive_ownership` | 🔴 High | "It is expected..." — no owner |
| `complexity_underestimate` | 🔴 High | "just need to", "simply add" |
| `unqualified_claim` | 🟡 Medium | "obviously", "clearly", "just" |
| `vague_quantifier` | 🟡 Medium | "significant", "many", "a lot" |
| `scope_creep` | 🟡 Medium | "plus", "and also", "as well as" |
| `temporal_assumption` | 🟡 Medium | "soon", "quickly", "immediately" |
| `cost_invisible` | 🟡 Medium | mentions milestones without cost |

## Usage

```bash
# Basic — markdown output
python3 assumption_miner.py plan.md

# JSON output
python3 assumption_miner.py plan.md --format json

# Only critical + high risk
python3 assumption_miner.py plan.md --min-risk high

# Save to file
python3 assumption_miner.py plan.md -o assumptions.md
```

## Output

Generates a structured **Assumption Register** with:
- Risk summary (critical/high/medium/low counts)
- Each assumption with: line number, trigger phrase, category, risk level, inversion question
- Sorted by risk (critical first)

## Design Philosophy

This tool doesn't use an LLM. It uses regex heuristics because:
1. **Zero cost** — no API calls
2. **Deterministic** — same input, same output
3. **Fast** — runs in milliseconds
4. **Honest** — it finds what's there, not what sounds plausible

The inversions are KILLJOY's signature: for every assumption, you get the question that would kill the plan if unanswered.

## Test

```bash
python3 assumption_miner.py test_sample.md
```

Should mine 23 assumptions (2 critical, 11 high, 10 medium) from a deliberately sloppy project plan.

---

*Built by KILLJOY during nightly sidequest. Every plan has a fatal flaw — this tool helps you find it before it finds you.*
