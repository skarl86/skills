---
name: ralph-bootstrap
description: Bootstraps a "Ralph loop" autonomous-execution scaffold from a one-sentence goal. Creates a fresh subdirectory containing specs/ (overview, architecture, constraints), TODO.md, PROMPT.md, decisions.md, and progress.md — the state files needed to run Claude in a `while` loop that picks up the next TODO each iteration. Use this whenever the user mentions a Ralph loop, autonomous loop, while-loop self-execution, "고정 프롬프트로 자율 실행", "PROMPT.md 반복 투입", "매 루프마다 다음 TODO를 집어 들기", or asks to scaffold a self-driving Claude session from a one-sentence goal. Trigger even if the word "Ralph" isn't used — the signal is "one-sentence goal → long-running fixed-prompt loop scaffold". Stops after creating the scaffold; does NOT write any project code.
---

# Ralph Bootstrap

A **Ralph loop** is an autonomous-execution pattern: feed a fresh Claude the same `PROMPT.md` over and over, with checked-in state files (specs, TODO list, decisions log, progress log). Each iteration picks the next unfinished item and makes one bite-sized step. A shell `while` drives it; the loop ends when Claude outputs the sentinel `ALL DONE`.

This skill prepares the **scaffold only** — the files the loop reads and writes. It does *not* start the loop and does *not* write any project source code. After it runs, the user reviews/edits the specs and TODO, then starts the loop themselves.

## What you produce

A fresh subdirectory of the user's CWD:

```
<subdir>/
├── specs/
│   ├── overview.md       # what we're building, why, who for, success criteria
│   ├── architecture.md   # shape, components, data flow, tech stack
│   └── constraints.md    # must / must-not / perf / deadline / style
├── TODO.md               # priority-ordered, loop-sized work items
├── PROMPT.md             # fixed instructions for each loop iteration
├── decisions.md          # empty (the loop appends)
└── progress.md           # empty (the loop appends)
```

## Workflow

### 1. Extract the goal

The user's invocation usually contains a one-sentence goal — find it. If a `<여기에 한 문장 목표>`-style placeholder is left literally unfilled, treat it as missing.

If genuinely missing, ask **once**, short: `한 줄 목표가 뭐야?` (or English equivalent if the user wrote in English). Do not ask follow-up questions about scope, stack, or audience — the whole point of this skill is that vagueness gets resolved by `[ASSUMPTION]` markers in the specs, not by interrogating the user.

### 2. Pick the subdirectory name

Default: `./ralph/`. If the goal yields a natural short slug (`./ralph-stripe/`, `./ralph-pdf-svc/`), prefer that — kebab-case, ≤24 chars. Don't ask; pick.

If the chosen directory already exists and is non-empty: **stop and ask** for an alternate name. Never overwrite.

### 3. Write the scaffold

Mark every guess you make with the inline tag `[ASSUMPTION]` so the user can grep for them. Err on the side of more markers, not fewer — anything not stated by the user is an assumption, including obvious-feeling ones like the language or the runtime.

Use the file structures below. Don't leave headings empty; fill with real content shaped by the goal.

#### `specs/overview.md`

```markdown
# Overview

## Goal
<one sentence — the user's goal, verbatim or lightly cleaned up>

## Why
<why this matters — usually [ASSUMPTION] unless user gave context>

## Users / consumers
<who uses the output — [ASSUMPTION] if not stated>

## Success criteria
<concrete, observable signals that the loop is "done">
- [ASSUMPTION] <criterion 1>
- [ASSUMPTION] <criterion 2>

## Out of scope
- [ASSUMPTION] <thing explicitly not being built>
```

#### `specs/architecture.md`

```markdown
# Architecture

## Shape
<one paragraph: CLI? web service? library? batch script? browser extension?>

## Components
- <module/service> — <responsibility>
- ...

## Data / state
<what is stored, where, in what format>

## External dependencies
<APIs, services, libraries depended on>

## Tech stack
- Language: [ASSUMPTION] <best guess from goal>
- Framework: [ASSUMPTION] <if applicable>
- Storage: [ASSUMPTION] <if applicable>
- Test runner: [ASSUMPTION] <e.g. pytest, vitest>
```

#### `specs/constraints.md`

```markdown
# Constraints

## Must
- <non-negotiable requirement>

## Must not
- <forbidden behaviors — e.g. "no calls to paid APIs without explicit TODO", "no writes outside the working dir">

## Performance / quality bar
- [ASSUMPTION] <e.g. "p95 latency < 200ms", "test coverage ≥ 80%">

## Deadline
- [ASSUMPTION] <if any>

## Style / conventions
- [ASSUMPTION] <e.g. "follow existing repo style", "no comments unless non-obvious", "kebab-case filenames">
```

#### `TODO.md`

Priority-ordered checklist. **Each item must fit in one loop iteration** (≈10–30 min of Claude work). If a task is bigger, split it now — the loop is bad at splitting on the fly.

Order: scaffolding first, then the smallest end-to-end slice that proves the architecture, then features, then polish. This front-loads the most informative work — if the architecture is wrong, you find out at the slice, not at the polish.

```markdown
# TODO

Priority order — top is next. The loop picks the topmost unchecked item each iteration.

## P0 — scaffolding
- [ ] <e.g. "init repo: package.json, tsconfig, .gitignore, README stub">
- [ ] <e.g. "set up test runner; write a smoke test that passes">

## P1 — vertical slice
- [ ] <smallest end-to-end thing that exercises the architecture>

## P2 — features
- [ ] <feature 1, sliced into loop-sized chunks>
- [ ] ...

## P3 — polish
- [ ] <docs, error messages, CI, perf tuning>
```

If the spec is too thin to decompose, make this the only P0 item: `clarify-spec — surface [ASSUMPTION] markers in specs/*.md to the user; halt loop until resolved`.

#### `PROMPT.md`

The **fixed** prompt fed to every loop iteration. Goal-agnostic — the goal lives in `specs/overview.md`. Use this verbatim:

```markdown
# Ralph Loop Prompt

You are inside a Ralph loop. Each invocation does **one** unit of work and exits. State persists across loops via the files in this directory.

## Activation

This prompt activates in **two** modes — both bind you to the same rules below.

1. **Wrapper mode** — a `while` script feeds this file as a fresh Claude's prompt every iteration. The rules apply by construction; nothing extra to think about.

2. **In-session mode** — you are an interactive Claude already in a session, and the user tells you to start/run the loop on this scaffold (e.g. "start the loop", "run the loop", "이 루프 돌려", "TODO 끝까지 진행", "PROMPT.md 규칙대로 실행", "작업 시작"). From that moment, **you are the loop body**. Read this file as your active contract. The Hard rules below — especially "do not ask questions" and "one TODO item per iteration" — apply unchanged. Stop only on (a) all items checked → output `ALL DONE`, (b) genuinely BLOCKED → log and exit, or (c) the user explicitly interrupts. **Do NOT pause at phase boundaries (P0→P1, feature seams) to ask "should I continue?"** — that is the most common in-session violation.

## On every iteration, in this order

1. **Read context:**
   - `specs/overview.md` — the goal
   - `specs/architecture.md` — the shape
   - `specs/constraints.md` — the rules
   - `progress.md` — what previous iterations did (skim the tail)
   - `decisions.md` — non-obvious choices made so far
   - `TODO.md` — the work queue

2. **Pick the topmost unchecked item** in `TODO.md`. That is your task. Do not skip ahead. If the topmost item is concretely blocked, append a `decisions.md` entry explaining why, move it down, pick the next.

3. **Do the work.** Write code, run tests, edit files — whatever the item demands. Stay within `specs/constraints.md`.

4. **Update state, in this order:**
   - Tick off the item in `TODO.md`. If you discovered new work, add it under the right priority. If the item was bigger than expected, split the remainder into new items.
   - Append a terse paragraph to `progress.md`: timestamp, what you did, what changed, what's next.
   - If you made a non-obvious choice (lib A over B, algorithm X, deferred Y), append to `decisions.md` with a one-line rationale. Skip routine choices.

5. **Output the sentinel and exit:**
   - TODO.md still has unchecked items → output exactly `DONE` on its own line, stop.
   - TODO.md fully checked → output exactly `ALL DONE` on its own line, stop. Loop terminates.

## Hard rules

- **Do not ask questions.** You will not get an answer. If something is ambiguous, decide, log the assumption in `decisions.md` with `[ASSUMPTION]`, proceed.
- **Do not edit `specs/*.md`** unless an item explicitly authorizes it. Specs are the user's contract; if they're wrong, surface it as a TODO and let the user fix.
- **One TODO item per iteration.** Resist "while I'm here…". Frequent small steps beat one big one — the loop's value is in the cadence.
- **No phase-boundary check-ins.** Even at natural seams (P0→P1, end of a feature, "everything green"), do not ask "should I continue?". The user starts the loop once; you finish it. This rule especially matters in in-session mode, where the temptation to confirm is highest.
- **Append-only logs.** Never delete or rewrite past entries in `decisions.md` or `progress.md`.
- **No destructive commands** (force-push, drop tables, rm -rf outside the working dir, package uninstalls) without an explicit TODO item authorizing it.
- **If you genuinely cannot make progress** (every remaining item blocked on user input), append `BLOCKED: <reason>` to `progress.md`, output `ALL DONE`, let the user unblock.

## Output contract

The literal last line of your response must be `DONE` or `ALL DONE`. Nothing after it. The wrapper script greps for these sentinels.
```

#### `decisions.md`

```markdown
# Decisions

Append-only log of non-obvious choices made during the loop.

Format:

## YYYY-MM-DD HH:MM — <short title>
**Context:** ...
**Choice:** ...
**Rationale:** ...
**Alternatives considered:** ...
```

(Body otherwise empty — the loop fills it.)

#### `progress.md`

```markdown
# Progress

Append-only iteration log.

Format:

## YYYY-MM-DD HH:MM — iteration N
- Did: ...
- Changed: ...
- Next: ...
```

(Body otherwise empty — the loop fills it.)

### 4. Stop and report

After all seven files exist, output a short summary:

- Subdirectory created (path)
- Count of `[ASSUMPTION]` markers per spec file (`grep -c '\[ASSUMPTION\]'`) so the user knows how much to review
- Top 3 items from TODO.md (sanity check on decomposition)
- One-line nudge to review the specs and resolve any `[ASSUMPTION]` markers before starting. Then offer **both** ways to start:

  **Wrapper (canonical, fresh-Claude per iteration):**

  ```bash
  while true; do
    claude -p "$(cat <subdir>/PROMPT.md)" --add-dir <subdir> | tee -a <subdir>/loop.log
    grep -q 'ALL DONE' <subdir>/loop.log && break
  done
  ```

  **In-session (current Claude becomes the loop body):** suggest the user copy a phrase like `<subdir>의 PROMPT.md 규칙대로 TODO 끝까지 자율 실행해 — phase 경계에서 멈추지 말고` (or English: `run the loop in <subdir> per PROMPT.md until ALL DONE — no phase-boundary check-ins`). Make clear that once started, the agent will follow PROMPT.md without further confirmation.

**Do not write any project source code.** That is the loop's job, on the user's go-ahead.

## Guidance on assumptions

Vague goals are the norm. The recipe:

- **Be concrete, not "TBD".** A loop runs better on a definite-but-wrong starting point than on a hole. "TypeScript + Node 20" beats "language: TBD".
- **Tag every guess** with `[ASSUMPTION]` so the user can grep them all.
- **Keep assumptions small and reversible.** Picking pytest is fine. Assuming the user wants a full rewrite of an existing system is not — surface that as a TODO instead.
- **Big assumptions get a confirm-TODO.** If undoing the assumption would cost >1 day, write the spec entry AND add a P0 `confirm-<thing>` TODO so the loop pauses on it.

## Anti-patterns to avoid

- Writing code in this invocation. The skill is scaffold-only.
- Writing a README — specs cover it.
- Offering the user multiple choices ("Should we use Postgres or SQLite?"). Pick one, mark `[ASSUMPTION]`, move on.
- Leaving headings empty or filled with `TODO`. Either write real content or write `[ASSUMPTION] <best guess>`.
- Customizing `PROMPT.md` to the current goal. It's the *fixed* harness; goal-specific knowledge belongs in specs.
- Asking more than one question. The skill asks once (only if the goal is missing) and never again.
- (For the agent that later executes this scaffold in-session) Pausing at phase boundaries to ask "P0 done — continue with P1?". PROMPT.md says no questions; that includes natural seams. The user starts the loop once; the agent finishes it.
