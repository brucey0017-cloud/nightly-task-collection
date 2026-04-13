# Test Commit Messages for commit_bs_lint.py

These are intentionally bad commit messages to test all pattern categories.

## false_confidence (should flag)
- "just a quick fix"
- "simply update the config"
- "minor change to auth"
- "should work now"
- "WIP: refactoring"

## scope_creep (should flag)
- "fix login and also update the dashboard"
- "cleanup the codebase"
- "while at it, refactor the utils"

## blame_deflection (should flag)
- "legacy code was broken"
- "had to do this because of old API"
- "as per John's request"

## missing_info (should flag)
- "fix"
- "update"
- "stuff"
- "see #1234"

## risky_language (should flag)
- "temp workaround for tests"
- "skip test validation for now"
- "TODO: fix this later"
- "hotfix disable the guard"

## optimism (should flag)
- "should now work properly"
- "finally fixed it for real this time"
- "properly implemented payments"

## Clean messages (should NOT flag)
- "Add JWT token refresh endpoint with 15-min expiry"
- "Fix race condition in payment processing by adding mutex lock"
- "Update Node.js from 18 to 20 in CI pipeline"
- "Refactor user service to use repository pattern (refs #456)"
