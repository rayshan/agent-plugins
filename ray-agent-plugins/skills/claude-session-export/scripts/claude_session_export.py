#!/usr/bin/env python3
"""Export a local Claude Code session transcript to a readable markdown file.

Reads a session JSONL transcript and produces a human-readable markdown file
containing only the conversation (user messages and Claude responses).

Dependencies: none (stdlib only)
Usage: python3 export_session.py <project-path> <session-uuid> [output-file]
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

SEPARATOR = "\u2501" * 80  # ━ BOX DRAWINGS HEAVY HORIZONTAL

# System-injected XML tags to strip from user messages.
_SYSTEM_TAGS_RE = re.compile(
    r"<(?:"
    r"system-reminder|local-command-caveat|command-name|"
    r"command-message|command-args|local-command-stdout|"
    r"available-deferred-tools"
    r")>.*?</(?:"
    r"system-reminder|local-command-caveat|command-name|"
    r"command-message|command-args|local-command-stdout|"
    r"available-deferred-tools"
    r")>\s*",
    re.DOTALL,
)


def encode_project_path(project_path: str) -> str:
    """Encode a project path the way Claude Code does internally."""
    absolute = str(Path(project_path).resolve())
    return re.sub(r"[^a-zA-Z0-9]", "-", absolute)


def strip_system_tags(text: str) -> str | None:
    """Strip system-injected XML tags, return None if nothing remains."""
    cleaned = _SYSTEM_TAGS_RE.sub("", text).strip()
    return cleaned if cleaned else None


def extract_user_text(msg: dict) -> str | None:
    """Extract human-authored text from a user message, skipping tool/skill results."""
    if "toolUseResult" in msg or "sourceToolUseID" in msg:
        return None
    content = msg.get("message", {}).get("content")
    if isinstance(content, str):
        return strip_system_tags(content)
    if isinstance(content, list):
        texts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        combined = "\n\n".join(texts) if texts else None
        return strip_system_tags(combined) if combined else None
    return None


def extract_assistant_text(msg: dict) -> str | None:
    """Extract text blocks from an assistant message, skipping thinking/tool_use."""
    content = msg.get("message", {}).get("content", [])
    texts = [
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n\n".join(texts) if texts else None


def format_timestamp(iso_str: str | None) -> str:
    """Format an ISO 8601 timestamp for display. Returns empty string on failure."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return ""


def slugify(name: str) -> str:
    """Convert a name to a filename-safe slug (lowercase, hyphens)."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return slug or "untitled"


def export_session(
    project_path: str, session_uuid: str
) -> tuple[str, int, str | None, str | None]:
    """Export a session transcript to markdown.

    Returns (markdown_text, message_count, agent_name, last_timestamp).

    Raises FileNotFoundError if the transcript file does not exist.
    """
    encoded = encode_project_path(project_path)
    claude_dir = Path.home() / ".claude" / "projects" / encoded
    transcript_file = claude_dir / f"{session_uuid}.jsonl"

    if not transcript_file.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_file}")

    messages = []
    with open(transcript_file) as f:
        for line in f:
            line = line.strip()
            if line:
                messages.append(json.loads(line))

    # Extract metadata and conversation entries.
    title = None
    agent_name = None
    skill_names: dict[str, str] = {}  # tool_use id -> skill name
    entries: list[tuple[str, str, str, str | None]] = []  # (emoji, role, text, ts)

    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp")

        if msg_type == "custom-title":
            title = msg.get("customTitle")
        elif msg_type == "agent-name":
            agent_name = msg.get("agentName")
        elif msg_type == "user":
            source_tool_id = msg.get("sourceToolUseID")
            if source_tool_id and source_tool_id in skill_names:
                skill = skill_names[source_tool_id]
                entries.append(
                    (
                        "\U0001f916",
                        "Claude",
                        f"Loaded \u26a1\ufe0f Skill `{skill}`",
                        timestamp,
                    )
                )
            else:
                text = extract_user_text(msg)
                if text:
                    entries.append(("\U0001f464", "User", text, timestamp))
        elif msg_type == "assistant":
            # Index any Skill tool_use calls for later matching.
            for block in msg.get("message", {}).get("content", []):
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_use"
                    and block.get("name") == "Skill"
                ):
                    skill_names[block["id"]] = block.get("input", {}).get(
                        "skill", "unknown"
                    )
            text = extract_assistant_text(msg)
            if text:
                entries.append(("\U0001f916", "Claude", text, timestamp))

    # Build markdown output.
    lines: list[str] = []

    display_title = title or agent_name or "Untitled Session"
    lines.append(f"# {display_title}")
    lines.append("")

    meta = [
        f"**Session:** `{session_uuid}`",
        f"**Project:** `{project_path}`",
    ]
    if agent_name and title:
        meta.append(f"**Agent:** {agent_name}")
    meta.append(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    for m in meta:
        lines.append(f"> {m}  ")
    lines.append("")

    for emoji, role, text, timestamp in entries:
        lines.append(SEPARATOR)
        lines.append("")
        ts_str = format_timestamp(timestamp)
        if ts_str:
            lines.append(f"### {emoji} {role}  \u00b7  {ts_str}")
        else:
            lines.append(f"### {emoji} {role}")
        lines.append("")
        lines.append(text)
        lines.append("")

    last_ts = entries[-1][3] if entries else None
    return "\n".join(lines), len(entries), agent_name, last_ts


def main() -> None:
    if len(sys.argv) < 3:
        print(
            f"Usage: {sys.argv[0]} <project-path> <session-uuid> [output-file]",
            file=sys.stderr,
        )
        sys.exit(1)

    project_path = sys.argv[1]
    session_uuid = sys.argv[2]

    try:
        markdown, count, agent_name, last_ts = export_session(
            project_path, session_uuid
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) >= 4:
        output_path = Path(sys.argv[3])
    else:
        name_part = slugify(agent_name) if agent_name else session_uuid
        date_part = format_timestamp(last_ts)[:10] if last_ts else "unknown"
        output_path = Path(f"claude-transcript-{name_part}-{date_part}.md")

    output_path.write_text(markdown)
    print(f"Exported {count} messages to {output_path}")


if __name__ == "__main__":
    main()
