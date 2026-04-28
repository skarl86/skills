---
name: claude-session-to-md
description: Convert Claude Code session jsonl logs (from ~/.claude/projects/ or ~/.claude-envs/*/projects/) into readable per-session markdown files for archiving, search, or knowledge accumulation. Use this skill whenever the user wants to back up Claude Code conversations, import Claude history into Obsidian/Logseq/any markdown vault, browse past sessions in human-readable form, accumulate Claude sessions as searchable knowledge, sync Claude logs across machines, or work with the .jsonl files Claude Code stores per project. Also trigger on phrases like "export my Claude sessions", "convert Claude logs to md", "turn jsonl into markdown", "I want to keep my Claude history", or any mention of session UUIDs, sessions-index.json, ~/.claude/projects, or parent-subagent log structure. Prefer this over hand-rolling JSON parsing — the bundled script already handles tool calls, tool results, subagent nesting, idempotent re-runs, and noise filtering (thinking blocks, command-only sessions).
---

# claude-session-to-md

Convert Claude Code session transcripts (jsonl) into readable per-session markdown files. The bundled `scripts/convert.py` walks Claude Code's storage, parses each conversation, and emits one md file per session — preserving user/assistant turns, tool calls, and tool results. Subagent (Task tool) child conversations are nested under `<parent-shortid>_subagents/` next to the parent session for easy navigation.

## When to use

Common scenarios:

- User wants to **accumulate Claude sessions** in their Obsidian/Logseq vault for later search
- User wants to **back up** their Claude Code history before clearing or moving machines
- User has **multiple Claude environments** (e.g., `~/.claude/` and `~/.claude-envs/<name>/`) and wants to merge them
- User wants to **browse past conversations** in a human-readable form (jsonl is unreadable)
- User wants the **subagent's full conversation**, not just the parent session's tool result

## Workflow

1. **Confirm destination.** Ask the user where the markdown should go. Common destinations:
   - An Obsidian vault folder (e.g., `~/Documents/Vault/claude-logs/`)
   - A backup directory (e.g., `~/backups/claude/`)
   - A new dedicated folder — offer to `mkdir -p` it

2. **Identify sources.** By default the script reads `~/.claude/projects/`. If the user has multiple environments (look at `~/.claude-envs/`), ask whether to merge them. Each `--source` invocation can be run separately with its own `--label` to keep them distinguished.

3. **Decide subfolder label.** When merging multiple sources or labeling by machine (work vs home), pass `--label <name>` so output goes to `<out>/<label>/...`. Otherwise omit it and output goes directly under `<out>/`.

4. **Run the script.** It lives next to this SKILL.md:

   ```bash
   python <skill-dir>/scripts/convert.py --out <dest>
   python <skill-dir>/scripts/convert.py --out <dest> --source ~/.claude-envs/<env>/projects --label <env>
   ```

5. **Report counts.** The script prints `parents`, `subagents`, and `skipped` counts. Pass these to the user. Skipped sessions are typically command-only or empty — no real conversation worth recording.

## Output format

```
<dest>/[<label>/]<project>/<YYYY-MM-DD>_<HH-MM-SS>_<slug>_<short-id>.md
<dest>/[<label>/]<project>/<parent-shortid>_subagents/<YYYY-MM-DD>_<HH-MM-SS>_<slug>_<agent-shortid>.md
```

The project folder name decodes Claude's encoded path (e.g., `-Users-foo-bar-myrepo` → `Users-foo-bar-myrepo/`).

Each markdown file has:

- **Frontmatter:** `session_id` (or `agent_id` + `parent_session_short` for subagents), `cwd`, `start`, `end`, `turns`, `first_prompt`
- **Body:** alternating `## User — <ts>` and `## Assistant — <ts>` sections

Tool calls render as `**-> tool: \`Bash\`**` followed by JSON input. Tool results render as `**<- tool result:**` followed by output. Both are truncated above 1500/2000 chars to keep files reviewable.

## Defaults and trade-offs

- **Thinking blocks excluded by default.** Assistant `thinking` content is typically 3× the token cost of the actual answer and mostly low-signal for archival review. Pass `--include-thinking` if the user explicitly wants them (debugging, model-behavior research, etc.).
- **Subagents always included.** They live in `<parent-shortid>_subagents/` next to the parent. The first user message in a subagent's jsonl is the Task prompt the parent sent; the rest is the subagent's actual work.
- **Idempotent.** Re-running won't rewrite unchanged sessions. A session is rewritten only if its source jsonl is newer than the output md (e.g., the conversation continued in a new turn).
- **Empty/command-only skipped.** Sessions where the first user message starts with `<command-` (slash command invocation only) or has no real prompt are skipped — zero archival value.

## Common patterns

**Single source, simple destination:**
```bash
python scripts/convert.py --out ~/Documents/Vault/claude-logs
```

**Multiple environments, labeled:**
```bash
# Default env labeled 'main'
python scripts/convert.py --out ~/claude-archive --source ~/.claude/projects --label main

# A separate env (e.g., a 'pure' setup)
python scripts/convert.py --out ~/claude-archive --source ~/.claude-envs/pure/projects --label pure
```

**By machine (work vs home):**
```bash
# On work machine
python scripts/convert.py --out ~/Documents/Vault/claude-logs --label work
# On home machine (sync the vault first, then run)
python scripts/convert.py --out ~/Documents/Vault/claude-logs --label home
```

## Re-running

The script is fast and only writes changed sessions. Suggest the user run it manually whenever they want to sync, or set up a cron / launchd job. A simple alias:

```bash
alias claude-sync='python ~/path/to/skills/claude-session-to-md/scripts/convert.py --out ~/Documents/Vault/claude-logs'
```

## Edge cases

- **Source dir doesn't exist** → script prints `error: source does not exist: ...` and exits non-zero. Verify the path; some users have only `~/.claude-envs/<env>/projects/` and no default `~/.claude/projects/`.
- **Permission errors on output** → suggest `mkdir -p <dest>` first or pick a writable location.
- **Very large sessions (100MB+ jsonl)** → still work but may take a moment. Tool-result truncation keeps output sizes reviewable.
- **Sessions with no user text** (e.g., pure tool-call sessions or session_start hook payloads only) → skipped silently. They have no human-readable content.

## Why this exists

Claude Code stores sessions as jsonl — one JSON object per line, with nested message content arrays mixing user text, assistant text, thinking blocks, tool calls, and tool results. It's machine-readable but useless to grep through directly. Markdown with stable filenames + YAML frontmatter makes the same data searchable in Obsidian, browseable in any editor, and committable to git for cross-machine sync. The bundled script encodes the conventions — folder structure, slug + short-id naming, idempotent rewrite, subagent nesting — so each invocation reuses the same patterns rather than reinventing them.
