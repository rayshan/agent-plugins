"""Shared primitives: paths, encoding, history rewrite, active-session set."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
HISTORY_FILE = CLAUDE_DIR / "history.jsonl"
SESSIONS_DIR = CLAUDE_DIR / "sessions"


def encode_path(directory: str) -> str:
    """Encode an absolute path the same way Claude Code does.

    Every non-alphanumeric character is replaced with a hyphen.
    """
    return re.sub(r"[^a-zA-Z0-9]", "-", directory)


def resolve_path(raw: str) -> str:
    """Resolve a path to its absolute, canonical form (existing or not)."""
    return str(Path(raw).expanduser().resolve())


def active_session_ids() -> set[str]:
    """Return UUIDs of currently-running Claude Code sessions.

    Reads ~/.claude/sessions/<pid>.json files and collects sessionId fields.
    Used to refuse moves of live sessions.
    """
    if not SESSIONS_DIR.exists():
        return set()
    active: set[str] = set()
    for entry in SESSIONS_DIR.iterdir():
        if not entry.is_file():
            continue
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sid = data.get("sessionId") or data.get("session_id")
        if isinstance(sid, str):
            active.add(sid)
    return active


def update_history(
    old_path: str,
    new_path: str,
    *,
    dry_run: bool,
    session_ids: set[str] | None = None,
) -> int:
    """Rewrite the 'project' field of matching history.jsonl entries.

    An entry matches when its 'project' equals old_path. If session_ids is
    given, the entry must additionally have a sessionId in that set.

    Returns the number of rewritten entries. Writes a backup at
    history.jsonl.bak before modifying the file.
    """
    if not HISTORY_FILE.exists():
        print(f"  Warning: history file not found: {HISTORY_FILE}")
        return 0

    lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
    changed = 0
    updated_lines: list[str] = []

    for line in lines:
        if not line.strip():
            updated_lines.append(line)
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            updated_lines.append(line)
            continue

        matches = entry.get("project") == old_path
        if matches and session_ids is not None:
            matches = entry.get("sessionId") in session_ids

        if matches:
            entry["project"] = new_path
            updated_lines.append(json.dumps(entry, ensure_ascii=False))
            changed += 1
        else:
            updated_lines.append(line)

    if changed == 0:
        print("  No matching entries in history.jsonl.")
        return 0

    if dry_run:
        print(f"  Would update {changed} entries in history.jsonl.")
    else:
        backup = HISTORY_FILE.with_suffix(".jsonl.bak")
        shutil.copy2(HISTORY_FILE, backup)
        HISTORY_FILE.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        print(f"  Updated {changed} entries in history.jsonl.")
        print(f"  Backup saved to {backup}")

    return changed
