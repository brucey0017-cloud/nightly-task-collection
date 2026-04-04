# Tone & Rhythm Text Analyzer

A brand voice linter for soul designers.

## What it does

Checks your copy for:
- **Forbidden corporate words** (赋能, 一站式, leverage, innovative, etc.)
- **Sentence rhythm** (length variation - monotonous writing puts people to sleep)
- **Weak words** (very, really, just, hopefully - words that dilute your message)
- **Readability issues** (sentences that are too long or too repetitive)

## Usage

```bash
# Analyze text from a file
python3 tone_analyzer.py my_copy.txt

# Analyze text from stdin
echo "Your text here" | python3 tone_analyzer.py

# Interactive mode
python3 tone_analyzer.py
# Then type your text and press Ctrl+D to finish
```

## The Verdicts

- **CORPORATE BULLSHIT DETECTED** → Contains forbidden words. Rewrite.
- **BORING** → Sentences are all the same length. Add some rhythm.
- **OK but punch it up** → Has weak words. Remove them.
- **SOLID** → Good voice, clean rhythm, no bullshit.

## Why this exists

Because "赋能用户的全方位解决方案，极致体验引领未来" makes me want to claw my eyes out.

And because good copy has rhythm. Short punchy sentences mixed with longer flowing ones. Like music.
