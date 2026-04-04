# Memory File Organizer

A Python tool for parsing, indexing, and searching OpenClaw memory files.

## Features

- **File Analysis**: Parses memory files to extract structured information
- **Search**: Quickly search across all memory files for specific content
- **Mentions Tracking**: Track user mentions across sessions
- **Topic Indexing**: Automatically identifies and indexes frequently mentioned topics
- **Summary Reports**: Generate comprehensive reports of memory file content

## Usage

### Basic Commands

```bash
# Generate summary report
python3 memory_organizer.py summary

# Search for specific content
python3 memory_organizer.py search --query "your search term"

# Find mentions of a specific user
python3 memory_organizer.py mentions --user-id "USER_ID"

# Build/update index
python3 memory_organizer.py index
```

### Example Usage

```bash
# Search for mentions of a specific user
python3 memory_organizer.py mentions --user-id "1470262775006625990"

# Search for specific topics
python3 memory_organizer.py search --query "project"
python3 memory_organizer.py search --query "technical"

# Generate JSON report
python3 memory_organizer.py summary --output-format json
```

## Output Examples

### Summary Report
```
# Memory Files Summary Report
Generated: 2026-04-02 03:06:50

## Overview
- Total files: 35
- Total words: 7899
- Unique mentions: 5
- Unique file paths: 131
- Date range: 2026-02-10 to 2026-04-01

## Top Topics
- MAKER: 30 mentions
- COMMANDER: 28 mentions
- Discord: 22 mentions
- Conversation: 19 mentions
- Bruce: 18 mentions
```

### Search Results
```
Search results for 'commander':
--------------------------------------------------

📁 2026-04-01.md (2026-04-01)
   Matches: 1
   📂 夜间自动构建（Bruce 新偏好）

📁 2026-03-31-vibe-rootcause.md (2026-03-31)
   Matches: 1
   📂 Conversation Summary
```

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library)

## Tool Status

✅ **Complete** - Working tool that successfully:
- Parses 35 memory files (7,899 words total)
- Extracts user mentions and file paths
- Provides search functionality across all content
- Tracks topics and generates comprehensive reports
- Follows commander-sidequest requirements (small scope, self-contained, useful)