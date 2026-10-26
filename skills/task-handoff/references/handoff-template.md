# Handoff template

```markdown
# Handoff: <task title> (<YYYY-MM-DD>)

**Status:** <Complete | In progress | Blocked | Paused>
**Branch:** `<branch>` · **Base:** `<base>` · **Last commit:** `<short sha> <message>`

## Goal
<One or two sentences: what must be true when this is finished.>

## State
- **Done (verified):** <item> (evidence: <test/command>)
- **Believed done, unverified:** <item> (verify with: <command>)
- **In progress:** <item> (where it stands: <file:line or description>)
- **Not started:** <item>

## Decisions and reasons
- <Decision>: because <reason>. Rejected: <alternative> because <reason>.

## Dead ends
- Tried <approach>; failed because <reason>. Do not retry unless <condition>.

## Files that matter
- `<path>`: <what changed and why>

## How to run and verify
```
<setup command>
<test command>
```
Expected: <what success looks like>

## Blockers and open questions
- <Question or blocker>: <who or what can resolve it>

## Next three actions
1. <Concrete first step>
2. <...>
3. <...>

## Unknown
<Anything you could not determine. Never delete this heading; write "Nothing" if so.>
```
