# vibe-tone-lint

Zero-dependency Python copy checker for quick brand-tone guardrails.

## What it catches
- Banned Chinese corporate clichés:
  - 赋能 / 一站式 / 全方位 / 极致体验 / 开启新篇章 / 引领未来 / 匠心打造
- Flat AI opener patterns:
  - Great question / I'd be happy to help / Absolutely

## Usage

```bash
python3 tone_lint.py --text "Great question. 我们提供一站式极致体验。"
```

Check a file:

```bash
python3 tone_lint.py --file sample_bad.md
```

JSON output:

```bash
python3 tone_lint.py --file sample_bad.md --json
```

Exit code:
- `0` = pass
- `2` = needs rewrite (useful in CI hooks)
