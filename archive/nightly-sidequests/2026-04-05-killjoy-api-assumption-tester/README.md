# Assumption Hunter - API Assumption Testing Tool

KILLJOY Edition: Where reality meets your assumptions head-on.

## Overview

A simple but powerful tool that validates API assumptions against reality. Teams often make assumptions about APIs:
- "This endpoint always returns 200"
- "The response always contains these fields" 
- "This endpoint never returns forbidden keys"

But do these assumptions hold up when actually tested? That's what Assumption Hunter finds out.

## Features

- 🧪 **Tests API endpoints** with actual HTTP requests
- ✅ **Validates status codes** against expectations
- 🔍 **Checks response structure** for required/forbidden fields
- 📊 **Generates reports** on which assumptions are valid/invalid
- 🎯 **Zero dependencies** - Uses only Python standard library
- 📝 **Supports YAML/JSON** configuration files

## Quick Start

1. **Create a sample assumptions file:**
   ```bash
   python3 assumption-hunter.py --create-sample
   ```

2. **Test your assumptions:**
   ```bash
   python3 assumption-hunter.py sample_assumptions.yaml
   ```

3. **See detailed results:**
   ```bash
   python3 assumption-hunter.py sample_assumptions.yaml --verbose
   ```

## Assumptions File Format

### YAML Format
```yaml
assumptions:
  - name: "GitHub API Test"
    url: "https://api.github.com"
    method: "GET"
    expected_status: 200
    expected_keys:
      - "current_user_url"
      - "emojis_url"
    forbidden_keys:
      - "error"
```

### JSON Format
```json
{
  "assumptions": [
    {
      "name": "API Health Check",
      "url": "https://api.example.com/health",
      "method": "GET",
      "expected_status": 200,
      "expected_keys": ["status", "timestamp"]
    }
  ]
}
```

## Options

```bash
# Basic usage
python3 assumption-hunter.py assumptions.yaml

# Verbose output with details
python3 assumption-hunter.py assumptions.yaml --verbose

# JSON output for automation
python3 assumption-hunter.py assumptions.yaml --json

# Custom timeout (default: 10s)
python3 assumption-hunter.py assumptions.yaml --timeout 5

# Create sample file
python3 assumption-hunter.py --create-sample
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All assumptions passed ✅ |
| 1 | Some assumptions failed ❌ |
| 2 | Error (file not found, invalid format, etc.) |

## Sample Output

```
🔍 Testing 5 API assumptions...
============================================================

📊 Assumption Hunter Report
============================================================
Total Tests: 5
Passed: 4 ✅
Failed: 1 ❌
Pass Rate: 80.0%

❌ Failed Assumptions:
  • Public API Health Check: https://api.publicapis.org/random
    Error: HTTP 404: NOT FOUND
```

## Use Cases

### 1. API Contract Testing
Validate that third-party APIs still meet your expectations after updates.

### 2. Regression Testing
Catch API changes that might break your application.

### 3. Dependency Monitoring
Monitor external APIs that your service depends on.

### 4. Documentation Validation
Ensure your API documentation matches reality.

## Why This Matters

**KILLJOY Perspective**: Every assumption is a potential point of failure. This tool finds the gap between "what we think" and "what actually happens." When your API starts returning 500 instead of 200, or removes a field you depend on, that's not a surprise - it's a finding.

## Security Note

This tool only makes GET requests by default. It does not:
- Write any data
- Modify any state
- Execute untrusted code
- Require API keys

Safe to use in production environments.

## License

Provided as-is for testing and educational purposes.