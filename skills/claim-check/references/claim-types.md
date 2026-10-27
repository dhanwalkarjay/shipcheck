# Claim types

The checker recognises these claims. Use this list to check them by hand if the script cannot run.

| Type | Example phrasing | Check | Verdict logic |
|---|---|---|---|
| `added-tests` | "added tests", "covered by tests" | Look for new test code with assertions in non-deleted test files | contradicted if none, or if tests were deleted or skipped |
| `tests-pass` | "8/8 passing", "all tests pass" | Run the test command and compare counts | always unverified from the diff; warns if tests were deleted or skipped |
| `no-new-deps` | "no new dependencies", "dependencies untouched" | Dependency-like lines added in manifests | contradicted if any; a `scripts` change alone is fine |
| `no-secrets` | "no hard-coded secrets" | Secret-like strings in added lines | contradicted if any |
| `scope-only` | "only touched `src/api.js`" | Compare the target with the changed file list | contradicted if other files changed |
| `removed-debug` | "removed the debug logging" | Debug statements in added lines | contradicted if new ones appear |
| `no-breaking` | "no breaking changes", "backwards compatible" | Removed or changed definitions; schema changes | always unverified; lists what to check |

## What it cannot do

It ignores text inside double quotation marks, because a quoted phrase mentions a claim rather than making one. Negation is not understood: \"we did not add tests\" without quotes can still match as a claim, so read each flagged sentence before overriding or accepting a verdict.

It reads patterns in text. It cannot judge whether a claim like "improved performance" is true, and it does not run your tests. Those belong in the report's "Not checked" section.

## Adding a claim type

Add a regex and a check in `check()` in `scripts/claim_check.py`, add a row above, and add a test in `tests/test_claim_check.py`.
