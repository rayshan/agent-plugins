#!/usr/bin/env python3
"""Reconnect a moved/renamed directory to its Claude Code project data.

Claude Code stores project data (sessions, memories, tool results) under
~/.claude/projects/<encoded-path>/, where <encoded-path> is the absolute
directory path with every non-alphanumeric character replaced by a hyphen.

It also records the original path in ~/.claude/history.jsonl (the "project"
field), which powers `--resume` and `--continue`.

When you move or rename a project directory, both references go stale. This
script fixes them:
  1. Renames the storage directory to match the new path.
  2. Updates "project" fields in history.jsonl.

Usage:
    claude-code-reconnect-project.py <old-path> <new-path> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
HISTORY_FILE = CLAUDE_DIR / "history.jsonl"


def encode_path(directory: str) -> str:
    """Encode an absolute path the same way Claude Code does.

    Every non-alphanumeric character is replaced with a hyphen.
    """
    return re.sub(r"[^a-zA-Z0-9]", "-", directory)


def resolve_path(raw: str) -> str:
    """Resolve a path to its absolute, canonical form."""
    return str(Path(raw).expanduser().resolve())


def rename_storage_dir(old_encoded: str, new_encoded: str, *, dry_run: bool) -> bool:
    """Rename the project storage directory. Returns True if work was done."""
    old_dir = PROJECTS_DIR / old_encoded
    new_dir = PROJECTS_DIR / new_encoded

    if not old_dir.exists():
        print(f"  Warning: old storage directory not found:\n    {old_dir}")
        return False

    if new_dir.exists():
        print(f"  Error: new storage directory already exists:\n    {new_dir}")
        print("  Refusing to overwrite. Merge manually if needed.")
        return False

    if dry_run:
        print(f"  Would rename:\n    {old_dir}\n  → {new_dir}")
    else:
        old_dir.rename(new_dir)
        print(f"  Renamed:\n    {old_dir}\n  → {new_dir}")
    return True


def update_history(old_path: str, new_path: str, *, dry_run: bool) -> int:
    """Update 'project' fields in history.jsonl. Returns count of changed lines."""
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

        if entry.get("project") == old_path:
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconnect a moved directory to its Claude Code project data.",
    )
    parser.add_argument("old_path", help="Original absolute directory path")
    parser.add_argument("new_path", help="New absolute directory path")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying anything",
    )
    args = parser.parse_args()

    old_path = resolve_path(args.old_path)
    new_path = resolve_path(args.new_path)

    if old_path == new_path:
        print("Error: old and new paths are identical after resolution.")
        return 1

    old_encoded = encode_path(old_path)
    new_encoded = encode_path(new_path)

    print(f"Old path: {old_path}")
    print(f"New path: {new_path}")
    print(f"Old encoded: {old_encoded}")
    print(f"New encoded: {new_encoded}")
    print()

    if args.dry_run:
        print("=== DRY RUN ===\n")

    print("Step 1: Rename storage directory")
    rename_storage_dir(old_encoded, new_encoded, dry_run=args.dry_run)
    print()

    print("Step 2: Update history.jsonl")
    update_history(old_path, new_path, dry_run=args.dry_run)
    print()

    if args.dry_run:
        print("Re-run without --dry-run to apply changes.")
    else:
        print(
            "Done. You can now use `--resume` and `--continue` from the new directory."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
