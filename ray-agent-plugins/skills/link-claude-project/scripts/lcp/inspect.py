"""Session listing helpers: SessionInfo, first-message extraction, gathering."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import core


@dataclass
class SessionInfo:
    """Metadata about a single session in a project's storage directory."""

    uuid: str
    mtime: float
    size: int
    first_user_msg: str
    has_tool_results: bool
    has_subagents: bool


def first_user_message(jsonl_path: Path, max_chars: int = 80) -> str:
    """Return the first user message in a session jsonl, truncated."""
    try:
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "user":
                    continue
                msg = entry.get("message")
                if not isinstance(msg, dict) or msg.get("role") != "user":
                    continue
                text = _extract_user_text(msg.get("content"))
                if text:
                    return _truncate(text, max_chars)
    except OSError:
        return ""
    return ""


def _extract_user_text(content: object) -> str:
    """Pull the first text part out of a user message content payload."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = block.get("text", "")
                if isinstance(text, str) and text:
                    return text
    return ""


def _truncate(s: str, max_chars: int) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1] + "…"


def gather_session_info(project_path: str) -> list[SessionInfo]:
    """Return SessionInfo for every session in a project's storage dir.

    Sessions are returned newest-first by mtime. Empty list if the storage
    directory does not exist.
    """
    storage = core.PROJECTS_DIR / core.encode_path(project_path)
    if not storage.exists():
        return []

    infos: list[SessionInfo] = []
    for entry in storage.iterdir():
        if not entry.is_file() or entry.suffix != ".jsonl":
            continue
        uuid = entry.stem
        stat = entry.stat()
        sub = storage / uuid
        infos.append(
            SessionInfo(
                uuid=uuid,
                mtime=stat.st_mtime,
                size=stat.st_size,
                first_user_msg=first_user_message(entry),
                has_tool_results=(sub / "tool-results").exists(),
                has_subagents=(sub / "subagents").exists(),
            )
        )

    infos.sort(key=lambda i: i.mtime, reverse=True)
    return infos


def select_last_n_sessions(project_path: str, n: int) -> list[str]:
    """Return UUIDs of the N most recently modified sessions, newest first."""
    return [info.uuid for info in gather_session_info(project_path)[:n]]


def format_size(n: int) -> str:
    """Render a byte count as a short human-readable string."""
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f}KB"
    if n < 1024**3:
        return f"{n / (1024 * 1024):.1f}MB"
    return f"{n / (1024**3):.1f}GB"
