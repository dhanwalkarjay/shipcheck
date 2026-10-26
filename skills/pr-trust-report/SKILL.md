---
name: pr-trust-report
description: Produce an evidence-based trust report for a pull request or branch written by a coding agent or a human. Runs a deterministic risk scan (migrations, auth changes, dependency changes, deleted or skipped tests, leaked secrets), maps every task requirement to concrete evidence in the diff, and saves a one-page report as a task artifact. Use this whenever the user asks to review a PR, check whether agent-written code is safe to merge, verify a task is actually done, assess risk of a change, or says things like "can I trust this PR", "is this ready to merge", "did the agent finish the task", or "what should I look at in this diff".
---

# PR Trust Report

Answer one question for a human reviewer: **"Can I trust this change, and where should I spend my attention?"**

This skill is read-only. Never edit, commit, or push code while using it.

## Inputs

You need two things. Get them from the task or conversation first; ask the user only if they are truly missing.

1. **The requirements**: the task title, description, and any acceptance criteria. If there is no task, use the user's request as the requirement.
2. **The change**: a PR, a branch, or the current working tree. Default to `HEAD` compared with the repository's default branch (`main` or `master`).

## Steps

### 1. Run the deterministic risk scan

From the repository root, run the script bundled with this skill. Adjust the path to wherever this skill is installed:

```bash
python3 <skill-dir>/scripts/risk_scan.py --base <default-branch> --head HEAD --format json
```

It uses only the Python standard library and makes no network calls. If `python3` or `git` is unavailable, fall back to `git diff --stat` and `git diff` and apply the checklist in `references/risk-signals.md` by hand.

### 2. Verify each flagged signal

For every **high** signal, open the actual changed lines and decide whether it is a real risk or a false positive. Examples: a `verify=False` inside a test helper is not the same as one in production code; a migration that only adds a nullable column is not the same as one that drops a table. Say which it is and why, in one sentence. Do not repeat the scanner output verbatim.

Read `references/risk-signals.md` for what each signal means and how to judge it.

### 3. Map requirements to evidence

List every requirement from the task as a separate row. For each one, give a verdict:

- **Met**: you can point to specific changed code **and** a test or run result that covers it.
- **Partial**: code exists but is untested, or only part of the requirement is covered.
- **Missing**: you cannot find the change anywhere in the diff.
- **Unverified**: the code looks right but nothing demonstrates it. Say what would verify it.

Every verdict needs evidence as `path:line` or a test name. If you cannot cite evidence, the verdict is **Unverified**, never **Met**. Do not assume tests pass: run them only if the command is obvious and cheap, otherwise state that you did not run them.

Also list anything the diff changes that **no requirement asked for** (scope creep).

### 4. Decide the verdict

Choose exactly one:

- **Ready for human review**: no high signals that survive step 2, and all requirements Met or explicitly low-risk Partial.
- **Needs changes**: at least one real high-risk signal, or a Missing requirement.
- **Blocked**: a leaked secret, a deleted or disabled test with no replacement, or a destructive migration without a rollback.

### 5. Write the report

Use the exact structure in `references/report-template.md`. Keep it to roughly one page: a reviewer should be able to read it in two minutes.

Save it as a **Document artifact** on the current task and conversation, titled `Trust report: <task title>`, using Alan's artifact tools. Attach it to the correct task; an artifact attached to the wrong `taskId` or `conversationId` becomes invisible. If artifact tools are unavailable, post the report in the reply and tell the user so.

Finish with a short chat reply: the verdict, the top three things the reviewer should look at, and the artifact name.

## Rules

- Evidence over opinion. No "looks good", no "seems fine" without a citation.
- Be specific about what you did not check. Unknowns belong in the report.
- Do not pad. If the change is clean, say so in a few lines.
- Never print a suspected secret in full; show only the first 4 characters and the file path.

## Good fit

This skill pairs well with the **Review Agent** profile, which cannot edit files, so the report stays analytical.
