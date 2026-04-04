# Assumption Hunter

A simple tool to find hidden assumptions and risks in project files - perfect for killjoy-style risk assessment.

## What It Does

Scans files in a directory looking for:
- **Assumptions**: Words like "assume", "suppose", "expect", "hopefully"
- **Risk indicators**: Words like "should", "would", "could", "probably", "likely"  
- **Overconfidence markers**: Words like "obviously", "clearly", "certainly"
- **Time pressure**: Words like "quickly", "fast", "urgent", "deadline"

## Usage

```bash
# Scan current directory
python3 assumption_hunter.py

# Scan specific directory  
python3 assumption_hunter.py /path/to/project

# Scan specific file extensions
python3 assumption_hunter.py --extensions .md .txt .yaml

# Save report to file
python3 assumption_hunter.py --output report.md
```

## Example Output

```
# Assumption Hunter Report

## Summary
- High severity findings: 3
- Medium severity findings: 5
- Total findings: 8

## 🔴 HIGH SEVERITY - ASSUMPTIONS FOUND
**project/README.md:12**
> We assume users will naturally understand the interface.
  - Pattern: `we assume`

**project/PLAN.md:24**  
> Hopefully the API will be ready on time.
  - Keyword: `hopefully`

## 🟡 MEDIUM SEVERITY - RISK INDICATORS
**project/DESIGN.md:8**
> The integration should be straightforward.
  - Keyword: `should`

**project/PROPOSAL.md:15**
> Users probably want this feature.
  - Keyword: `probably`
```

## Why This Is Useful for Killjoy

As a Chief Questioner, this tool helps you:
- Find the "fatal flaws" before they kill the project
- Surface unvalidated assumptions that could lead to failure
- Identify overconfidence that ignores real risks
- Quickly assess project health by looking at language used

The tool prioritizes the files that matter most (README.md, PLAN.md, DESIGN.md) and gives you clear severity levels to focus on what's actually dangerous.