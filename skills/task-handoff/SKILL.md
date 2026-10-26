---
name: task-handoff
description: Write a resumable handoff note so another person or another coding agent can pick up a task tomorrow without rereading the conversation. Captures the goal, what is done, what is half-done, decisions and the reasons for them, changed files, how to run and verify, blockers, and the first three next actions, and saves it as a task artifact. Use this whenever the user says "hand this off", "I'm stopping for today", "summarize where we are", "write a handoff", "someone else will continue this", before ending a long session, before switching agents or profiles, or when a task has been paused and needs a record of its state.
---

# Task Handoff

Chat history disappears; artifacts persist. This skill turns the current state of a task into a short record that lets a fresh session continue **without asking you anything**.

## Principle

Write for a capable engineer who has never seen this conversation and has no memory of it. They have the repository and this note. Nothing else.

## Steps

### 1. Gather facts, do not guess

Collect from these sources, in order:

1. The task: title, description, status, subtasks, existing artifacts.
2. The repository: run `git status`, `git log --oneline -n 15`, and `git diff --stat` against the base branch.
3. The conversation: decisions made, things tried and abandoned, user preferences stated.

If a fact is not in any of those, mark it **Unknown**. Never fill gaps with plausible-sounding text.

### 2. Write the handoff

Use the structure in `references/handoff-template.md`. Keep it under about 60 lines. Prefer specifics: file paths, commands, branch names, error messages.

Pay special attention to three things people forget:

- **Decisions and why.** A decision without a reason will be reversed by the next person.
- **Dead ends.** What was tried and failed, so nobody repeats it.
- **How to verify.** The exact commands that show the work is correct.

### 3. Separate done from believed-done

Mark an item **Done** only when the change exists in the repository and you saw evidence (a test run, a command output, a screenshot). Otherwise mark it **Believed done, unverified**.

### 4. State the next three actions

Concrete, ordered, small enough to start immediately. Example: "1. Run `pytest tests/auth -x` and fix the failing `test_refresh_expired`." Not: "Continue working on auth."

### 5. Save it

Save as a **Document artifact** on the current task and conversation, titled `Handoff: <task title> (<date>)`, using Alan's artifact tools. Attach it to the correct task, because an artifact with the wrong `taskId` or `conversationId` is invisible in the expected view. If artifact tools are unavailable, reply with the note and say so.

If the task has subtasks, mention which are complete, in progress, and untouched. Do not change task or subtask status yourself unless the user asks.

## Rules

- Do not include secrets, tokens, or private credentials. Refer to where they live instead.
- Do not editorialize about the work. State facts.
- If the task is actually finished, say "Complete" at the top and keep the note short.
