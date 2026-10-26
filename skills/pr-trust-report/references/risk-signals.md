# Risk signals reference

What the scanner flags, what it means, and how to judge whether it is real. Use this in step 2.

## High

| Signal id | Meaning | How to judge |
|---|---|---|
| `migration` | A schema or SQL file changed | Real risk if it drops/renames a column or table, adds a NOT NULL column without a default, or has no rollback. Low if it only adds a nullable column or an index. |
| `auth-path` | A file whose path suggests auth, sessions, tokens, crypto or permissions changed | Read the diff. Real if logic that grants or checks access changed. False positive if only a comment or log line changed. |
| `auth-bypass` | Added code disables TLS verification or an auth/CSRF check | Real unless it is clearly confined to local dev or test code behind a flag. |
| `secret` | A string that looks like a key, token or password was added | Treat as real until proven otherwise. Never print the value in full. A placeholder like `changeme` or an example key from docs is a false positive. |
| `deleted-tests` | A test file was removed | Real unless the code it tested was also removed in the same change. |
| `disabled-tests` | `.skip`, `xit`, `@pytest.mark.skip`, `.only` and similar were added | Real: skipped tests hide failures and `.only` makes the rest of the suite silently not run. |

## Medium

| Signal id | Meaning | How to judge |
|---|---|---|
| `deps` | A manifest or lockfile changed | Check for new packages (supply-chain risk), major version bumps, or a lockfile change with no manifest change. |
| `infra` | CI, Docker, Terraform, k8s or `.env` files changed | Real if it changes what runs in production or weakens a CI check. |
| `weakened-tests` | A test file lost more assertions than it gained | Real if the assertions covered behaviour that still exists. |
| `swallowed-errors` | `except: pass` or an empty `catch` was added | Real if it hides failures from callers; fine for best-effort cleanup that is logged. |
| `no-tests` | 40+ source lines changed with no test file touched | Real unless the change is configuration, generated code, or a pure refactor covered by existing tests (say which). |
| `large-diff` | Over 800 changed lines or over 30 files | Not a defect by itself. Recommend splitting, and say where the seams are. |

## Low

| Signal id | Meaning |
|---|---|
| `lint-bypass` | `eslint-disable`, `# noqa`, `@ts-ignore` and similar were added. Check that each has a reason. |
| `debug-leftovers` | `console.log`, `print(`, `debugger`, `breakpoint()` in non-test code. |
| `todo-markers` | New TODO/FIXME/HACK. Check whether it hides unfinished required work. |

## Overall risk

- **HIGH**: any high signal.
- **MEDIUM**: any medium signal, or three or more low signals.
- **LOW**: otherwise.

The scanner is deliberately simple and over-reports. Your job in step 2 is to decide which signals are real. A good report explains why a flagged item is fine just as clearly as why another is dangerous.

## Limits

The scanner reads text patterns only. It cannot see logic bugs, race conditions, performance regressions or whether tests actually pass. Say so under "Not checked".
