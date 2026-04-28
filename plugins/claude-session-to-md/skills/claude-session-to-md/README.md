# claude-session-to-md

Convert Claude Code session jsonl logs into readable markdown notes — one file per session, with subagent (Task tool) child conversations nested next to their parent. Idempotent on re-run.

Built for accumulating Claude Code conversations into Obsidian / Logseq / any markdown vault for archival and search.

## Why use this skill instead of letting Claude figure it out

Claude can technically write a converter from scratch every time you ask. But the data format has tricky details — `tool_use` / `tool_result` rendering, `thinking` block noise, subagent path nesting (`<parent-uuid>/subagents/agent-*.jsonl`), idempotent rewrite based on mtime, command-only sessions to skip — and rolling these by hand misses things.

A formal eval against a 3-task benchmark (single-source backup, multi-source labeling, subagent grouping) shows:

| Metric | with skill | baseline (Claude rolls own converter) | delta |
|---|---:|---:|---:|
| Pass rate | **94.4%** (17/18 assertions) | 72.2% (13/18) | **+22.2 pp** |
| Median time | **28 s** | 123 s | **4.4× faster** |
| Median tokens | **17.6 k** | 33.1 k | **−47%** |

The skill wins on every axis. Where the baseline lost points:

- **Multi-source labels:** wrote its own header format instead of standard YAML frontmatter, so other tools (Obsidian dataview, scripts) can't parse the metadata.
- **Subagents:** flattened parent + child into the same directory with `__` filename joins, breaking visual grouping. No frontmatter linkage between parent ↔ child.

Eval set, fixtures, and benchmark.json live under [`claude-session-to-md-workspace/iteration-1/`](../../) (gitignored, but reproducible — see workspace contents in repo history if needed).

## Quick use

In Claude Code, just ask:

> "내 Claude 세션을 ~/Documents/Vault/claude-logs/ 에 마크다운으로 백업해줘"
>
> "Convert my Claude Code history under ~/.claude/projects to markdown at ~/claude-archive"
>
> "I have two Claude environments — merge them into one folder with labels"

Claude will read this `SKILL.md` and run the bundled `scripts/convert.py`.

## Manual use

```bash
# Single source → flat output
python scripts/convert.py --out ~/claude-archive

# Multiple environments, kept distinct
python scripts/convert.py --out ~/claude-archive --source ~/.claude/projects --label main
python scripts/convert.py --out ~/claude-archive --source ~/.claude-envs/pure/projects --label pure

# Include thinking blocks (off by default — verbose, low-signal)
python scripts/convert.py --out ~/claude-archive --include-thinking
```

## Output structure

```
<out>/[<label>/]<project>/<YYYY-MM-DD>_<HH-MM-SS>_<slug>_<short-id>.md
<out>/[<label>/]<project>/<parent-shortid>_subagents/<agent-session>.md
```

Each file has YAML frontmatter (`session_id` / `agent_id` + `parent_session_short`, `cwd`, `start`, `end`, `turns`, `first_prompt`) and body sections of `## User — <ts>` / `## Assistant — <ts>` with rendered content. Tool calls render as JSON code blocks; tool results as text code blocks (truncated above 1.5–2 KB).

See [`SKILL.md`](SKILL.md) for the full workflow Claude follows.
