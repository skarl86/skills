#!/usr/bin/env python3
"""Convert Claude Code jsonl session logs into readable markdown notes.

Walks Claude Code's session storage (~/.claude/projects/ by default) and emits
one markdown file per session. Subagent (Task tool) child conversations are
nested under <parent-shortid>_subagents/ next to the parent session.

Idempotent: re-running won't rewrite unchanged sessions. A session is rewritten
only if the source jsonl is newer than the output md (e.g., the conversation
continued in a new turn).

Usage:
    python convert.py --out <dest>
    python convert.py --out <dest> --source ~/.claude-envs/pure/projects --label pure
    python convert.py --out <dest> --include-thinking
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def decode_project(name: str) -> tuple[str, str]:
    """
    Convert encoded project dir name back to (folder_name, cwd_path).
    Example: '-Users-foo-bar-repo' -> ('Users-foo-bar-repo', '/Users/foo/bar/repo')
    """
    cwd = "/" + name.lstrip("-").replace("-", "/")
    folder = name.lstrip("-") or "_root_"
    return folder, cwd


def slugify(text: str, max_len: int = 40) -> str:
    text = (text or "").strip().splitlines()[0] if text else ""
    text = re.sub(r"[^\w\s가-힣\-]", "", text).strip()
    text = re.sub(r"\s+", "-", text)
    return text[:max_len] or "session"


def first_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                return item.get("text", "")
    return ""


def render_content(content, include_thinking: bool = False) -> str:
    """Render message content (string or list of blocks) to readable markdown."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts = []
    for item in content:
        if not isinstance(item, dict):
            continue
        t = item.get("type")
        if t == "text":
            parts.append(item.get("text", ""))
        elif t == "thinking" and include_thinking:
            thinking = item.get("thinking", "").strip()
            if thinking:
                quoted = thinking.replace("\n", "\n> ")
                parts.append(f"> **[thinking]**\n>\n> {quoted}")
        elif t == "tool_use":
            name = item.get("name", "?")
            inp = item.get("input", {})
            inp_str = json.dumps(inp, ensure_ascii=False, indent=2)
            if len(inp_str) > 1500:
                inp_str = inp_str[:1500] + "\n... [truncated]"
            parts.append(f"**-> tool: `{name}`**\n\n```json\n{inp_str}\n```")
        elif t == "tool_result":
            result = item.get("content", "")
            if isinstance(result, list):
                result = "\n".join(
                    r.get("text", "") if isinstance(r, dict) else str(r)
                    for r in result
                )
            result = str(result)
            if len(result) > 2000:
                result = result[:2000] + "\n... [truncated]"
            parts.append(f"**<- tool result:**\n\n```\n{result}\n```")
    return "\n\n".join(p for p in parts if p.strip())


def process_session(
    jsonl_path: Path,
    out_dir: Path,
    cwd: str,
    *,
    include_thinking: bool = False,
    is_subagent: bool = False,
    parent_short_id: str = "",
    agent_id: str = "",
) -> Path | None:
    session_id = jsonl_path.stem
    entries = []
    with jsonl_path.open() as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    turns = [e for e in entries if e.get("type") in ("user", "assistant")]
    if not turns:
        return None

    first_ts = next((e.get("timestamp") for e in entries if e.get("timestamp")), None)
    last_ts = next(
        (e.get("timestamp") for e in reversed(entries) if e.get("timestamp")),
        first_ts,
    )

    first_user_prompt = ""
    for e in entries:
        if e.get("type") != "user":
            continue
        msg = e.get("message", {})
        content = msg.get("content", "") if isinstance(msg, dict) else ""
        text = first_text(content)
        if text and not text.startswith("<command-"):
            first_user_prompt = text
            break

    if not first_user_prompt.strip():
        return None

    try:
        start_dt = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
    except Exception:
        start_dt = None

    date_str = start_dt.strftime("%Y-%m-%d") if start_dt else "unknown"
    time_str = start_dt.strftime("%H-%M-%S") if start_dt else "000000"
    slug = slugify(first_user_prompt)
    short_id = (agent_id or session_id)[:8]
    filename = f"{date_str}_{time_str}_{slug}_{short_id}.md"
    out_file = out_dir / filename

    if out_file.exists() and out_file.stat().st_mtime >= jsonl_path.stat().st_mtime:
        return out_file

    out_dir.mkdir(parents=True, exist_ok=True)

    def fm_escape(s: str) -> str:
        return (s or "").replace('"', '\\"')

    lines = ["---"]
    if is_subagent:
        lines.append(f'agent_id: "{agent_id}"')
        lines.append(f'parent_session_short: "{parent_short_id}"')
    else:
        lines.append(f'session_id: "{session_id}"')
    lines.extend([
        f'cwd: "{fm_escape(cwd)}"',
        f'start: "{first_ts or ""}"',
        f'end: "{last_ts or ""}"',
        f"turns: {len(turns)}",
        f'first_prompt: "{fm_escape(first_user_prompt[:200])}"',
        "---",
        "",
    ])

    for e in entries:
        t = e.get("type")
        if t not in ("user", "assistant"):
            continue
        msg = e.get("message", {})
        content = msg.get("content", "") if isinstance(msg, dict) else ""
        rendered = render_content(content, include_thinking=include_thinking).strip()
        if not rendered:
            continue
        role = "User" if t == "user" else "Assistant"
        ts = e.get("timestamp", "")
        lines.append(f"## {role} — {ts}")
        lines.append("")
        lines.append(rendered)
        lines.append("")

    out_file.write_text("\n".join(lines), encoding="utf-8")
    return out_file


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--out", type=Path, required=True,
                    help="Destination directory for markdown output")
    ap.add_argument("--source", type=Path,
                    default=Path.home() / ".claude" / "projects",
                    help="Claude projects directory (default: ~/.claude/projects)")
    ap.add_argument("--label", default=None,
                    help="Optional subfolder under <out>/ to keep multiple sources distinct")
    ap.add_argument("--include-thinking", action="store_true",
                    help="Include assistant thinking blocks (off by default — verbose, low-signal)")
    args = ap.parse_args()

    if not args.source.is_dir():
        print(f"error: source does not exist: {args.source}")
        return 1

    base = args.out / args.label if args.label else args.out
    parents = 0
    subagents = 0
    skipped = 0

    for proj_dir in sorted(args.source.iterdir()):
        if not proj_dir.is_dir():
            continue
        folder, cwd = decode_project(proj_dir.name)
        out_dir = base / folder

        for jsonl in sorted(proj_dir.glob("*.jsonl")):
            result = process_session(
                jsonl, out_dir, cwd,
                include_thinking=args.include_thinking,
            )
            if result:
                parents += 1
            else:
                skipped += 1

        for sub_jsonl in sorted(proj_dir.glob("*/subagents/*.jsonl")):
            parent_uuid = sub_jsonl.parent.parent.name
            parent_short = parent_uuid[:8]
            agent_id = sub_jsonl.stem.removeprefix("agent-")
            sub_out_dir = out_dir / f"{parent_short}_subagents"
            result = process_session(
                sub_jsonl, sub_out_dir, cwd,
                include_thinking=args.include_thinking,
                is_subagent=True,
                parent_short_id=parent_short,
                agent_id=agent_id,
            )
            if result:
                subagents += 1
            else:
                skipped += 1

    print(f"source:    {args.source}")
    print(f"output:    {base}")
    print(f"parents:   {parents}")
    print(f"subagents: {subagents}")
    print(f"skipped:   {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
