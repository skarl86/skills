# ralph-bootstrap

Bootstraps the **scaffold** for a [Ralph loop](https://ghuntley.com/ralph/) — Claude in a fixed-prompt `while`-loop that picks up the next TODO each iteration. The skill writes seven state files; the loop body comes after.

## What gets created

```
<subdir>/
├── specs/
│   ├── overview.md       # goal, why, users, success criteria, out of scope
│   ├── architecture.md   # shape, components, data, tech stack
│   └── constraints.md    # must / must not / perf / deadline / style
├── TODO.md               # priority-ordered, loop-sized work items
├── PROMPT.md             # fixed harness (no goal-specific text — that lives in specs)
├── decisions.md          # empty (loop appends)
└── progress.md           # empty (loop appends)
```

Every guess Claude makes is tagged inline with `[ASSUMPTION]` so you can grep them: `grep -rn '\[ASSUMPTION\]' <subdir>/specs/`.

## Quick use

In Claude Code, type a one-sentence goal. The skill triggers on Ralph-loop language and the "fixed-prompt → state files" shape — even without the word "Ralph":

> `/ralph-bootstrap PDF 분석 마이크로서비스를 만들어`
>
> `/ralph-bootstrap build a CLI that exports my GitHub stars to a SQLite DB`

The skill picks a kebab-case subdirectory name, writes the seven files, and reports back with `[ASSUMPTION]` counts and the top 3 TODO items so you can sanity-check decomposition before starting the loop.

## Starting the loop

Two modes — both bind the agent to the same `PROMPT.md` rules:

**Wrapper (canonical, fresh-Claude per iteration):**

```bash
while true; do
  claude -p "$(cat <subdir>/PROMPT.md)" --add-dir <subdir> | tee -a <subdir>/loop.log
  grep -q 'ALL DONE' <subdir>/loop.log && break
done
```

**In-session (current Claude becomes the loop body):**

> `<subdir>의 PROMPT.md 규칙대로 TODO 끝까지 자율 실행해 — phase 경계에서 멈추지 말고`
>
> `run the loop in <subdir> per PROMPT.md until ALL DONE — no phase-boundary check-ins`

The PROMPT.md `## Activation` section codifies both modes; in-session, the agent treats P0→P1 (and other natural seams) as **non**-checkin points.

## Anti-patterns the skill protects against

- Writing project source code during bootstrap (the loop's job, not the skill's)
- Asking the user follow-up questions about scope/stack/audience (everything ambiguous becomes `[ASSUMPTION]`)
- Customizing `PROMPT.md` to the current goal (it's the *fixed* harness)
- Splitting work too coarsely — each TODO must fit one iteration
