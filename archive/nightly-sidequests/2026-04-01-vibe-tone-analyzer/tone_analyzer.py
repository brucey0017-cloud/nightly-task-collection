#!/usr/bin/env python3
"""
Tone & Rhythm Text Analyzer
A brand voice linter for soul designers.

Checks text for:
- Sentence rhythm (length variation)
- Forbidden corporate words
- Reading flow score
- Tone consistency indicators
"""

import sys
import re

# Forbidden corporate words (the usual suspects)
FORBIDDEN_WORDS = {
    '赋能', '一站式', '全方位', '极致体验', '开启新篇章',
    '引领未来', '匠心打造', '赋能', '生态圈', '解决方案',
    '数字化转型', '创新突破', '战略升级', '核心价值',
    '用户体验', '智能升级', '行业领先', '标杆',
    'synergy', 'leverage', 'paradigm', 'disruptive',
    'innovative', 'scalable', 'robust', 'streamline',
    'optimization', 'best-in-class', 'world-class',
    'cutting-edge', 'state-of-the-art', 'seamless',
    'holistic', 'actionable', 'boil the ocean',
    'move the needle', 'circle back', 'touch base',
    'think outside the box', 'low-hanging fruit',
}

# Words that suggest weak/passive voice
WEAK_INDICATORS = {
    'very', 'really', 'quite', 'rather', 'pretty',
    'just', 'simply', 'basically', 'actually',
    'hopefully', 'maybe', 'perhaps', 'might',
    'could', 'would', 'should', 'think', 'believe',
}


def analyze_text(text):
    """Analyze text and return report."""
    sentences = split_sentences(text)
    
    return {
        'sentence_count': len(sentences),
        'word_count': len(text.split()),
        'sentence_lengths': [len(s.split()) for s in sentences],
        'forbidden_found': find_forbidden(text),
        'weak_words': find_weak_words(text),
        'avg_sentence_length': sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0,
        'rhythm_score': calculate_rhythm(sentences),
        'readability': assess_readability(text, sentences),
    }


def split_sentences(text):
    """Split text into sentences (naive but functional)."""
    # Handle common sentence endings
    text = re.sub(r'([.!?。！？])\s+', r'\1|SPLIT|', text)
    sentences = [s.strip() for s in text.split('|SPLIT|') if s.strip()]
    return sentences


def find_forbidden(text):
    """Find forbidden corporate words."""
    text_lower = text.lower()
    found = []
    for word in FORBIDDEN_WORDS:
        if word.lower() in text_lower:
            # Find positions
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            matches = list(pattern.finditer(text))
            for match in matches:
                found.append({
                    'word': word,
                    'position': match.start(),
                    'context': get_context(text, match.start(), len(word))
                })
    return found


def find_weak_words(text):
    """Find weak/modifier words."""
    words = re.findall(r'\b\w+\b', text.lower())
    found = []
    for word in words:
        if word in WEAK_INDICATORS:
            found.append(word)
    return found


def get_context(text, pos, length, window=20):
    """Get context around a position."""
    start = max(0, pos - window)
    end = min(len(text), pos + length + window)
    return text[start:end].replace('\n', ' ')


def calculate_rhythm(sentences):
    """Calculate rhythm score based on sentence length variation."""
    if len(sentences) < 2:
        return 0
    
    lengths = [len(s.split()) for s in sentences]
    avg = sum(lengths) / len(lengths)
    
    # Calculate variance
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    std_dev = variance ** 0.5
    
    # Score: higher variation = better rhythm (within reason)
    # Ideal: mix of short punchy and longer flowing sentences
    if std_dev < 2:
        return 'monotonous - vary your sentence lengths'
    elif std_dev > 10:
        return 'chaotic - some consistency helps readability'
    else:
        return 'good variation'


def assess_readability(text, sentences):
    """Assess overall readability."""
    issues = []
    
    # Check for very long sentences
    long_sentences = [s for s in sentences if len(s.split()) > 25]
    if long_sentences:
        issues.append(f'{len(long_sentences)} very long sentences (>25 words)')
    
    # Check for very short sentences
    short_sentences = [s for s in sentences if len(s.split()) < 3]
    if len(short_sentences) > len(sentences) * 0.3:
        issues.append('too many very short sentences - feels choppy')
    
    # Check for repetitive starts
    starts = [s.split()[0].lower() if s.split() else '' for s in sentences]
    unique_starts = len(set(starts))
    if unique_starts < len(sentences) * 0.5:
        issues.append('repetitive sentence starts - vary your openings')
    
    return issues if issues else ['clean']


def print_report(text, analysis):
    """Print formatted analysis report."""
    print('=' * 60)
    print('TONE & RHYTHM ANALYZER')
    print('=' * 60)
    print()
    print(f'Statistics:')
    print(f'  Sentences: {analysis["sentence_count"]}')
    print(f'  Words: {analysis["word_count"]}')
    print(f'  Avg sentence length: {analysis["avg_sentence_length"]:.1f} words')
    print()
    
    print(f'Sentence lengths: {analysis["sentence_lengths"]}')
    print(f'Rhythm: {analysis["rhythm_score"]}')
    print()
    
    print('Readability:')
    for item in analysis['readability']:
        print(f'  • {item}')
    print()
    
    if analysis['forbidden_found']:
        print(f'⚠️  FORBIDDEN WORDS ({len(analysis["forbidden_found"])} found):')
        for item in analysis['forbidden_found']:
            print(f'  • "{item["word"]}"')
            print(f'    Context: "...{item["context"]}..."')
        print()
    else:
        print('✓ No forbidden corporate words')
        print()
    
    if analysis['weak_words']:
        print(f'⚠️  Weak words: {", ".join(set(analysis["weak_words"]))}')
        print()
    
    print('=' * 60)
    print('Verdict:', end=' ')
    if analysis['forbidden_found']:
        print('CORPORATE BULLSHIT DETECTED. Rewrite.')
    elif analysis['rhythm_score'] == 'monotonous - vary your sentence lengths':
        print('BORING. Add some rhythm.')
    elif analysis['weak_words']:
        print('OK but punch it up. Remove weak words.')
    else:
        print('SOLID. This has a voice.')
    print('=' * 60)


def main():
    if len(sys.argv) > 1:
        # Read from file
        with open(sys.argv[1], 'r') as f:
            text = f.read()
    else:
        # Read from stdin
        print('Enter text (Ctrl+D to finish):')
        text = sys.stdin.read()
    
    if not text.strip():
        print('No text provided.')
        sys.exit(1)
    
    analysis = analyze_text(text)
    print_report(text, analysis)


if __name__ == '__main__':
    main()
