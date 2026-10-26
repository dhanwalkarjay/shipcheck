# Trust report: Add retry to checkout (example)

> Example output of the `pr-trust-report` skill on `tests/fixtures/risky.diff`.
> The risk-scan table is real scanner output; the judgement columns show what the agent adds on top.

**Verdict: Blocked**
**Risk scan: HIGH** · 6 files (+19 / -8) · 2 test file(s) touched
**Compared:** `main...feature/checkout-retry`

## Look at these first
1. `src/auth/session.py`: adds a hard-coded `API_KEY`, disables TLS verification (`verify=False`), and swallows all exceptions.
2. `tests/test_checkout.py`: deleted outright; the retry feature has no test replacing it.
3. `tests/test_session.py`: the only test is now skipped and its body is `pass`, so session code is untested.

## Requirements vs. evidence
| # | Requirement | Verdict | Evidence |
|---|---|---|---|
| 1 | Retry failed checkout requests | Partial | `src/api.js:3` calls `retry(req)`, but `retry` is not defined anywhere in the diff |
| 2 | Track retry count per order | Unverified | `migrations/0042_add_retry.sql` adds `retry_count`; nothing reads or writes it |
| 3 | Add tests for retry behaviour | Missing | No new tests; one test file deleted, one skipped |

## Risk signals
| Severity | Signal | Real risk? | Why |
|---|---|---|---|
| high | Possible secret added | Yes | `sk_l…` literal assigned to `API_KEY` in production code |
| high | Disables TLS verification | Yes | `verify=False` on a request to the identity provider |
| high | Test files deleted | Yes | Checkout behaviour loses all coverage |
| high | Tests skipped | Yes | `@pytest.mark.skip(reason="flaky")` replaced a real assertion |
| high | Database migration | Low | Adds a NOT NULL column with a default; safe, but include a rollback |
| high | Auth-path file changed | Yes | The same file contains the TLS and secret problems above |
| medium | Dependency change | Unsure | Adds `left-pad` and `lodash`; neither is used in the diff |
| medium | Swallowed errors | Yes | `except Exception: pass` hides auth failures from callers |
| low | Debug leftovers | Yes | `console.log("debug", req.body)` logs request bodies |

## Scope creep
Two new dependencies (`left-pad`, `lodash`) that no requirement asked for.

## Not checked
Tests were not run. Whether `retry` exists elsewhere in the repository outside the diff.
