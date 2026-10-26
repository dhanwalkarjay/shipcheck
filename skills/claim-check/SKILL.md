---
name: claim-check
description: Audit what a coding agent SAID it did against what it ACTUALLY did. Extracts verifiable claims from an agent's final message or PR description (tests added, N tests passing, no new dependencies, no secrets, only touched X, debug code removed, no breaking changes), checks each against the real diff, and runs the checks the diff cannot prove. Use this whenever the user asks "did the agent really do that", "verify the agent's summary", "is this claim true", "check what the agent told me", before trusting or merging an agent's work, or right after an agent reports it finished a task.
---

# Claim Check

Agents report success confidently. Sometimes the report is wrong: "tests added" while a test file was deleted, "dependencies untouched" while a package was added. This skill compares the **words** to the **diff** and tells the reviewer which sentences to believe.

This skill is read-only. Do not edit code, commit, or push.

## Inputs

1. **The claims**: the agent's final message, a PR description, or text the user pasted. If the user does not provide it, use the last summary the agent wrote in this conversation. Save it to a temporary text file **outside the repository** (for example in the system temp directory), so the working tree stays clean.
2. **The change**: a branch or working tree compared with the default branch.

## Steps

### 1. Run the deterministic checker

```bash
python3 <skill-dir>/scripts/claim_check.py --summary-file <summary.txt> --base <default-branch> --head HEAD --format json
```

It uses only the Python standard library. It returns each claim it recognised with a verdict:

- **supported**: the diff backs it (for example, new test code with assertions exists).
- **contradicted**: the diff shows the opposite. This is the most important output.
- **unverified**: the diff alone cannot prove it. Go to step 2.

If `python3` is unavailable, read `references/claim-types.md` and check each claim by hand with `git diff`.

### 2. Settle every "unverified" claim yourself

For each unverified claim, find real evidence, then change its verdict:

- **"N tests passing"**: run the project's test command if it is obvious and cheap, and compare the actual count with the claim. If you cannot run it, say so.
- **"No breaking changes"**: search the repository for callers of each removed or changed definition the checker listed.
- **Anything the checker did not recognise**: pick the 3 most important sentences in the summary that a reviewer would rely on, and check them the same way.

Never upgrade a claim to **supported** without citing a command output or `path:line`.

### 3. Report

Save a **Document artifact** titled `Claim check: <task title>` on the current task using Alan's artifact tools (attach it to the correct task and conversation). If artifact tools are unavailable, reply in chat.

Use this structure, with contradicted claims first:

```markdown
# Claim check: <task title>

**<n> contradicted · <n> unverified · <n> supported**
**Bottom line:** <one sentence: can the reviewer trust the agent's summary?>

| Verdict | What the agent said | What is true | Evidence |
|---|---|---|---|
| contradicted | "<quote>" | <one sentence> | `path:line` or command output |

## Not checked
<claims you could not verify and why>
```

Finish with a short chat reply: the bottom line and the single most serious contradiction.

## Rules

- Quote the agent's words exactly in the first column; do not paraphrase them.
- A contradiction needs evidence you can point to. If you are unsure, mark it unverified.
- Do not judge code quality. This skill only checks whether statements are true.
- Never print a suspected secret in full; show the first 4 characters and the file.

## Good fit

Run it right after an agent says it is done, before `/pr-trust-report`. Claim Check answers "is the summary honest?"; PR Trust Report answers "is the change safe?".
