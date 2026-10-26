---
name: plan-lint
description: Lint an implementation plan or PRD before any code is written. Scores the plan on outcome clarity, scope, testable acceptance criteria, verification steps, risk and rollback, open decisions, and sizing, then quotes each weak line and proposes a concrete rewrite. Use this whenever the user asks to review, critique, sanity-check, or improve a plan, spec, PRD, or task breakdown, or before handing a plan to a coding agent, or when a plan artifact has just been written and the user says "is this plan good", "what's missing", "ready to build?", or "tighten this up".
---

# Plan Lint

Catch the problems that make agents build the wrong thing, **before** they build it. A vague plan costs a full agent run to discover; a lint pass costs seconds.

This skill is read-only. It never changes the plan itself. It produces findings and suggested rewrites for a human or planning agent to apply.

## Inputs

The plan to review: a Plan artifact, a document, or text the user pastes. If the task has a plan artifact, read it. If you cannot find one, ask the user to point to it once, then stop.

## Steps

1. **Read the whole plan** before judging any part of it.
2. **Score each dimension 0, 1 or 2** using `references/rubric.md`. 0 = absent or unusable, 1 = present but weak, 2 = solid. Do not give a 2 unless you can point to the text that earns it.
3. **Quote, don't paraphrase.** For every dimension scored below 2, quote the weak line(s) exactly and say in one sentence why they are weak.
4. **Rewrite.** For each weak line, give a concrete replacement the author could paste in. A rewrite must be specific enough to be tested. "Handle errors gracefully" is not a rewrite; "Return HTTP 400 with `{error: 'invalid_duration'}` when the input does not match `^\d+[smh]$`" is.
5. **Check for missing questions.** List up to five questions the plan should answer but does not, each tied to a decision an agent would otherwise guess.
6. **Give the verdict**: Ready to build (score 13 or more, no 0s), Fix first (8 to 12, or any 0), or Rework (under 8).
7. **Save the result** as a **Document artifact** on the current task, titled `Plan lint: <plan title>`, using Alan's artifact tools. If artifact tools are unavailable, reply in chat.

## Output format

```markdown
# Plan lint: <plan title>

**Verdict: <Ready to build | Fix first | Rework>** · Score <n>/14

| Dimension | Score | Note |
|---|---|---|
| Outcome | 0-2 | <one line> |
| ... | | |

## Findings
### <Dimension> (<score>/2)
> "<exact quote from the plan>"

Why it is weak: <one sentence>
Suggested rewrite: <paste-ready text>

## Questions the plan does not answer
1. <question> (an agent would have to guess: <what>)

## Strengths
<One or two things the plan does well. Be honest; skip if there are none.>
```

## Rules

- Be direct and specific, not harsh. The goal is a better plan.
- Never invent requirements the author did not imply. If something seems missing, ask it as a question.
- Do not score down for style or length. Score only whether an agent could execute the plan correctly.
- A short plan can score 14/14. Do not demand ceremony.

## Good fit

Run it with the **PM Agent** profile (read-only, plans and scopes work) right after a plan artifact is created, and again after revisions.
