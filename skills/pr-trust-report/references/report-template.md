# Report template

Copy this structure. Replace everything in angle brackets. Delete sections that do not apply, but never delete "Not checked".

```markdown
# Trust report: <task title>

**Verdict: <Ready for human review | Needs changes | Blocked>**
**Risk scan: <LOW | MEDIUM | HIGH>** · <N> files (+<added> / -<removed>) · <T> test file(s) touched
**Compared:** `<base>...<head>` · **Task:** <task id or link>

## Look at these first
1. `<path>`: <why a human must read this, one sentence>
2. `<path>`: <...>
3. `<path>`: <...>

## Requirements vs. evidence
| # | Requirement | Verdict | Evidence |
|---|---|---|---|
| 1 | <requirement text> | Met / Partial / Missing / Unverified | `path:line`, `test_name` |

## Risk signals
| Severity | Signal | Real risk? | Why |
|---|---|---|---|
| high | <signal> | Yes / No / Unsure | <one sentence after reading the code> |

## Scope creep
<Changes no requirement asked for, or "None found".>

## Not checked
<What you did not run or could not verify. Always include this section.>
```

## Style

- One sentence per cell. Reviewers skim tables.
- "Look at these first" must name real files, ordered by risk.
- If the verdict is Blocked or Needs changes, the first item under "Look at these first" is the blocker.
