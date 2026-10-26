# Plan lint rubric

Seven dimensions, each scored 0, 1 or 2. Maximum 14.

## 1. Outcome
- **2**: One or two sentences state what will be true when the work is done, from the user's or system's point of view. A stranger could tell whether it happened.
- **1**: The goal is stated but as an activity ("improve search") rather than a result.
- **0**: No goal, or several unrelated goals.

## 2. Scope
- **2**: Says what is in and explicitly what is out. Names the files, modules or surfaces involved.
- **1**: In-scope is clear; out-of-scope is silent.
- **0**: Open-ended ("clean up the auth code").

## 3. Acceptance criteria
- **2**: Each criterion is observable and binary: a person or test can answer yes or no. Includes concrete inputs and expected outputs for the main cases.
- **1**: Criteria exist but contain words like "properly", "gracefully", "fast", "intuitive", "robust" without numbers or examples.
- **0**: No criteria.

## 4. Verification
- **2**: Names the exact commands, tests, or manual checks that prove each criterion, and says which new tests to add.
- **1**: Says "add tests" or "verify manually" without specifics.
- **0**: No verification step.

## 5. Risk and rollback
- **2**: Names what could break (data, auth, performance, other callers) and how to undo or contain it. For migrations: the down path.
- **1**: Mentions risk generally.
- **0**: Ignores risk on a change that touches data, auth, payments, or public interfaces. (Score 2 by default for trivially safe changes, and say so.)

## 6. Decisions and unknowns
- **2**: Open questions are listed with an owner or a default assumption. Decisions already made include the reason.
- **1**: Some unknowns are visible; others are buried in prose.
- **0**: The plan hides major choices (library, schema, API shape) that an agent would silently make.

## 7. Size and sequencing
- **2**: Work is broken into steps small enough to review one at a time, in a sensible order, with dependencies noted. Fits one reviewable PR or is split into several.
- **1**: Steps exist but are uneven, or one step hides a large change.
- **0**: One undifferentiated blob, or an order that cannot work.

## Vague-word watchlist

Flag these when they stand in for a measurable condition: *properly, gracefully, appropriately, robust, scalable, user-friendly, clean, improve, optimize, handle, support, as needed, etc., and so on, should work, similar to*.

## Verdict bands

- 13 or 14, no dimension at 0: **Ready to build**
- 8 to 12, or any dimension at 0: **Fix first**
- below 8: **Rework**
