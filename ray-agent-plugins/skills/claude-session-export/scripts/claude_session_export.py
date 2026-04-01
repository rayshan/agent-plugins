#!/usr/bin/env python3
"""Export a local Claude Code session transcript to a readable markdown file.

Reads a session JSONL transcript and produces a human-readable markdown file
containing only the conversation (user messages and Claude responses).

Dependencies: none (stdlib only)
Usage: python3 claude_session_export.py <project-path> <session-name-or-uuid> [output-file]
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


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def resolve_session(project_path: str, identifier: str) -> str:
    """Resolve a session name or UUID to a session UUID.

    If identifier looks like a UUID, return it directly. Otherwise, scan
    transcript files for a matching custom-title or agent-name
    (case-insensitive substring match).

    Raises FileNotFoundError if no match is found.
    Raises ValueError if multiple sessions match.
    """
    if _UUID_RE.match(identifier):
        return identifier

    encoded = encode_project_path(project_path)
    proj_dir = Path.home() / ".claude" / "projects" / encoded
    if not proj_dir.is_dir():
        raise FileNotFoundError(f"Project directory not found: {proj_dir}")

    query = identifier.lower()
    matches: list[tuple[str, str]] = []  # (uuid, display_name)

    for path in proj_dir.glob("*.jsonl"):
        title = agent = None
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                msg = json.loads(line)
                msg_type = msg.get("type")
                if msg_type == "custom-title":
                    title = msg.get("customTitle")
                elif msg_type == "agent-name":
                    agent = msg.get("agentName")
        name = title or agent
        if name and query in name.lower():
            matches.append((path.stem, name))

    if not matches:
        raise FileNotFoundError(f'No session matching "{identifier}" in {proj_dir}')
    if len(matches) > 1:
        listing = "\n".join(f"  {uuid}  {name}" for uuid, name in matches)
        raise ValueError(f'Multiple sessions match "{identifier}":\n{listing}')
    return matches[0][0]


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


def parse_mcp_tool(name: str) -> tuple[str, str] | None:
    """Parse an MCP tool name into (server_display, tool_name), or None."""
    parts = name.split("__")
    if len(parts) < 3 or parts[0] != "mcp":
        return None
    server = parts[1]
    tool = "__".join(parts[2:])
    # Clean up server display name.
    for prefix in ("plugin_", "claude_ai_"):
        if server.startswith(prefix):
            server = server[len(prefix) :]
    # Deduplicate "X_X" → "X" (e.g., "context7_context7" → "context7").
    halves = server.split("_")
    if len(halves) == 2 and halves[0] == halves[1]:
        server = halves[0]
    return server, tool


def format_mcp_notes(content: list) -> str | None:
    """Extract MCP tool_use blocks and format as blockquote summary lines.

    Groups tools by server, counts duplicates.
    Returns a blockquote string or None if no MCP tools found.
    """
    # Collect (server, tool) pairs in order.
    server_tools: dict[str, list[str]] = {}
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        parsed = parse_mcp_tool(block.get("name", ""))
        if not parsed:
            continue
        server, tool = parsed
        server_tools.setdefault(server, []).append(tool)

    if not server_tools:
        return None

    lines = []
    for server, tools in server_tools.items():
        # Count occurrences, preserve first-seen order.
        counts: dict[str, int] = {}
        for t in tools:
            counts[t] = counts.get(t, 0) + 1
        parts = []
        for t, n in counts.items():
            parts.append(f"`{t}` (\u00d7{n})" if n > 1 else f"`{t}`")
        lines.append(f"> Used MCP \U0001f50c `{server}` \u2192 {', '.join(parts)}")
    return "\n".join(lines)


_MCP_LINE_RE = re.compile(r"> Used MCP \U0001f50c `([^`]+)` \u2192 (.+)")
_MCP_TOOL_RE = re.compile(r"`([^`]+)`(?:\s*\(\u00d7(\d+)\))?")


def _format_tool_counts(counts: dict[str, int]) -> str:
    """Format a {tool: count} dict into a comma-separated display string."""
    parts = []
    for tool, n in counts.items():
        parts.append(f"`{tool}` (\u00d7{n})" if n > 1 else f"`{tool}`")
    return ", ".join(parts)


def consolidate_mcp_lines(text: str) -> str:
    """Merge MCP blockquote lines from the same server into one line."""
    body_parts: list[str] = []
    # server -> {tool: count}, preserving server insertion order.
    server_tools: dict[str, dict[str, int]] = {}

    for line in text.split("\n"):
        m = _MCP_LINE_RE.match(line)
        if m:
            server, tools_str = m.group(1), m.group(2)
            counts = server_tools.setdefault(server, {})
            for tm in _MCP_TOOL_RE.finditer(tools_str):
                tool = tm.group(1)
                n = int(tm.group(2)) if tm.group(2) else 1
                counts[tool] = counts.get(tool, 0) + n
        else:
            body_parts.append(line)

    if not server_tools:
        return text

    # Strip trailing blank lines from body before appending MCP lines.
    while body_parts and not body_parts[-1].strip():
        body_parts.pop()

    mcp_lines = []
    for server, counts in server_tools.items():
        mcp_lines.append(
            f"> Used MCP \U0001f50c `{server}` \u2192 {_format_tool_counts(counts)}"
        )

    parts = []
    if body_parts:
        parts.append("\n".join(body_parts))
    parts.append("\n".join(mcp_lines))
    return "\n\n".join(parts)


def extract_assistant_text(msg: dict) -> str | None:
    """Extract text and MCP notes from an assistant message."""
    content = msg.get("message", {}).get("content", [])
    texts = [
        block["text"]
        for block in content
        if isinstance(block, dict)
        and block.get("type") == "text"
        and block["text"].strip() != "No response requested."
    ]
    mcp_notes = format_mcp_notes(content)
    parts = []
    if texts:
        parts.append("\n\n".join(texts))
    if mcp_notes:
        parts.append(mcp_notes)
    return "\n\n".join(parts) if parts else None


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

    # Merge MCP-only Claude entries into the preceding Claude entry.
    merged: list[tuple[str, str, str, str | None]] = []
    for emoji, role, text, ts in entries:
        if (
            role == "Claude"
            and text.startswith("> Used MCP")
            and merged
            and merged[-1][1] == "Claude"
        ):
            combined = consolidate_mcp_lines(merged[-1][2] + "\n\n" + text)
            merged[-1] = (
                merged[-1][0],
                merged[-1][1],
                combined,
                merged[-1][3],
            )
        else:
            merged.append((emoji, role, text, ts))
    entries = merged

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
            f"Usage: {sys.argv[0]} <project-path> <session-name-or-uuid> [output-file]",
            file=sys.stderr,
        )
        sys.exit(1)

    project_path = sys.argv[1]
    identifier = sys.argv[2]

    try:
        session_uuid = resolve_session(project_path, identifier)
        markdown, count, agent_name, last_ts = export_session(
            project_path, session_uuid
        )
    except (FileNotFoundError, ValueError) as e:
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
