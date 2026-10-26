# ShipCheck

**Trust, but verify: open-source skills that tell you whether an agent-written change is safe to ship.**

Coding agents write code faster than humans can review it. ShipCheck is a small pack of [Alan](https://tryalan.ai) skills that turns "I hope this is fine" into evidence a reviewer can read in two minutes, and keeps work resumable between people and agents.

| Skill | What it does | Run it with |
|---|---|---|
| [`pr-trust-report`](skills/pr-trust-report/SKILL.md) | Scans a PR for risk (migrations, auth, deps, deleted or skipped tests, secrets), maps each task requirement to evidence, and saves a one-page report as a task artifact | Review Agent |
| [`plan-lint`](skills/plan-lint/SKILL.md) | Scores a plan or PRD on 7 dimensions, quotes the vague lines, and gives paste-ready rewrites before any code is written | PM Agent |
| [`task-handoff`](skills/task-handoff/SKILL.md) | Writes a handoff artifact (state, decisions and reasons, dead ends, how to verify, next three actions) so another person or agent can continue without the chat | Any agent |

## See it work

Here is a PR where an agent added a retry feature. `pr-trust-report` found what a skim would miss: a hard-coded key, TLS verification switched off, a deleted test, and a skipped test.

```
Overall risk: HIGH
6 files (+19 / -8), 2 test file(s) touched.

| high   | Database schema or migration files changed        | migrations/0042_add_retry.sql |
| high   | Files in auth/security-sensitive paths changed    | src/auth/session.py           |
| high   | Test files were deleted                           | tests/test_checkout.py        |
| high   | Tests were skipped, focused (.only) or disabled   | tests/test_session.py         |
| high   | Added code that disables TLS verification or auth | src/auth/session.py           |
| high   | Possible secret added (hard-coded credential)     | src/auth/session.py           |
| medium | Dependency manifest or lockfile changed           | package.json                  |
| medium | Errors are caught and silently ignored            | src/auth/session.py           |
```

The full agent-written report, with requirement-by-requirement verdicts, is in [`examples/sample-trust-report.md`](examples/sample-trust-report.md).

## Install in Alan

1. Open **Skills** in your team sidebar and choose **Team skills**.
2. Choose **Import**, then **From GitHub**.
3. Paste the link to this repo (`https://github.com/dhanwalkarjay/shipcheck`), or to a single skill folder such as `.../shipcheck/tree/main/skills/pr-trust-report`.
4. Choose **Review skill**, read the files, then **Add to team**.

Then, in any session, type `/` and pick a skill, or just ask. Agents load a matching skill on their own when your request fits its description:

> Run a trust report on this branch against the task requirements.
> Lint the plan artifact before we start building.
> Write a handoff for this task, I'm stopping for today.

## How it works

Most of the work is judgement, which the agent does. The part that must be reliable is not left to a model:

- `pr-trust-report` bundles [`scripts/risk_scan.py`](skills/pr-trust-report/scripts/risk_scan.py), a deterministic scanner (Python standard library only, no network, no model calls). It costs nothing to run and gives the same answer every time.
- The agent then reads the flagged code, decides which signals are real, and maps requirements to evidence. Every verdict needs a `path:line` or test name; no evidence means "Unverified", never "Met".
- Outputs are saved as Alan **artifacts** on the task, so a reviewer or a later agent can find them without the conversation.

## Use the scanner on its own

```bash
python3 skills/pr-trust-report/scripts/risk_scan.py --base main --head HEAD --format md
git diff main...HEAD | python3 skills/pr-trust-report/scripts/risk_scan.py -
python3 skills/pr-trust-report/scripts/risk_scan.py --base main --fail-on high   # exit 2 in CI
```

To run it on every pull request, copy [`examples/github-action.yml`](examples/github-action.yml) into your repo's `.github/workflows/`. The result appears in the job summary.

## What it will not do

The scanner reads text patterns. It cannot find logic bugs, race conditions, or performance regressions, and it does not run your tests. It over-reports by design, and the agent's job is to separate real risk from noise. Reports always include a **Not checked** section so unknowns stay visible.

## Develop

```bash
python3 -m unittest discover -s tests -v
```

Adding a signal: add a pattern and an `add(...)` call in `scan()`, document it in `skills/pr-trust-report/references/risk-signals.md`, and add a test using `tests/fixtures/risky.diff`.

## License

MIT
