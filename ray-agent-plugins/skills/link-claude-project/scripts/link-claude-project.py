#!/usr/bin/env python3
"""Reconnect a moved/renamed directory to its Claude Code project data.

Claude Code stores project data (sessions, memories, tool results) under
~/.claude/projects/<encoded-path>/, where <encoded-path> is the absolute
directory path with every non-alphanumeric character replaced by a hyphen.

It also records the original path in ~/.claude/history.jsonl (the "project"
field), which powers `--resume` and `--continue`.

When you move or rename a project directory, both references go stale. This
script fixes them by detecting the on-disk state and routing to the right
flow:

  - Already-moved (disk dir is at new path): relink only.
  - Pending rename (disk dir is at old path): pass --rename-disk to mv it,
    then relink.

The user-facing intent ("I moved it" vs. "rename it for me") is only a
tiebreaker — disk state is authoritative.

Operations are ordered so any failure leaves a recoverable state:
    1. disk mv      (reversible by mv'ing back)
    2. storage mv   (reversible by mv'ing back)
    3. history rewrite (backed up to history.jsonl.bak)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from enum import Enum
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
HISTORY_FILE = CLAUDE_DIR / "history.jsonl"


class State(Enum):
    """Detected on-disk state for an (old_path, new_path) pair."""

    IDENTICAL = "identical"
    OLD_STORAGE_MISSING = "old_storage_missing"
    TARGET_STORAGE_OCCUPIED = "target_storage_occupied"
    ALREADY_LINKED = "already_linked"
    AMBIGUOUS = "ambiguous"
    BOTH_DISK_MISSING = "both_disk_missing"
    NEEDS_DISK_RENAME = "needs_disk_rename"
    RELINK_ONLY = "relink_only"


def encode_path(directory: str) -> str:
    """Encode an absolute path the same way Claude Code does.

    Every non-alphanumeric character is replaced with a hyphen.
    """
    return re.sub(r"[^a-zA-Z0-9]", "-", directory)


def resolve_path(raw: str) -> str:
    """Resolve a path to its absolute, canonical form (existing or not)."""
    return str(Path(raw).expanduser().resolve())


def detect_state(old_path: str, new_path: str) -> State:
    """Classify the (old, new) pair against on-disk state.

    Storage-side conditions take priority over disk-side conditions because
    storage absence/conflict makes any disk action moot.
    """
    if old_path == new_path:
        return State.IDENTICAL

    old_enc_exists = (PROJECTS_DIR / encode_path(old_path)).exists()
    new_enc_exists = (PROJECTS_DIR / encode_path(new_path)).exists()

    if not old_enc_exists and new_enc_exists:
        return State.ALREADY_LINKED
    if not old_enc_exists:
        return State.OLD_STORAGE_MISSING
    if new_enc_exists:
        return State.TARGET_STORAGE_OCCUPIED

    old_disk_exists = Path(old_path).exists()
    new_disk_exists = Path(new_path).exists()

    if old_disk_exists and new_disk_exists:
        return State.AMBIGUOUS
    if not old_disk_exists and not new_disk_exists:
        return State.BOTH_DISK_MISSING
    if old_disk_exists:
        return State.NEEDS_DISK_RENAME
    return State.RELINK_ONLY


def rename_disk_dir(old_path: str, new_path: str, *, dry_run: bool) -> bool:
    """Rename the on-disk project directory. Returns True if work was done."""
    old_dir = Path(old_path)
    new_dir = Path(new_path)

    if not old_dir.exists():
        print(f"  Error: old disk directory does not exist:\n    {old_dir}")
        return False
    if new_dir.exists():
        print(f"  Error: new disk directory already exists:\n    {new_dir}")
        return False
    if not new_dir.parent.exists():
        print(f"  Error: parent of new path does not exist:\n    {new_dir.parent}")
        return False

    if dry_run:
        print(f"  Would rename disk directory:\n    {old_dir}\n  → {new_dir}")
    else:
        old_dir.rename(new_dir)
        print(f"  Renamed disk directory:\n    {old_dir}\n  → {new_dir}")
    return True


def rename_storage_dir(old_encoded: str, new_encoded: str, *, dry_run: bool) -> bool:
    """Rename the project storage directory. Returns True if work was done."""
    old_dir = PROJECTS_DIR / old_encoded
    new_dir = PROJECTS_DIR / new_encoded

    if not old_dir.exists():
        print(f"  Error: old storage directory not found:\n    {old_dir}")
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


def print_preflight(old_path: str, new_path: str, state: State) -> None:
    """Print the resolved paths, encoded names, and detected state."""
    old_encoded = encode_path(old_path)
    new_encoded = encode_path(new_path)
    print(f"Old path:    {old_path}")
    print(f"New path:    {new_path}")
    print(f"Old encoded: {old_encoded}")
    print(f"New encoded: {new_encoded}")
    print(f"State:       {state.value}")
    print()


def explain_blocking_state(state: State) -> str:
    """Return a one-line explanation for a state that blocks execution."""
    return {
        State.IDENTICAL: "Old and new paths are identical after resolution.",
        State.OLD_STORAGE_MISSING: (
            "No project storage exists for the old path. Nothing to relink — "
            "check that the old path is correct."
        ),
        State.TARGET_STORAGE_OCCUPIED: (
            "Project storage already exists at the new path. The new directory "
            "has its own sessions; merge manually before relinking."
        ),
        State.ALREADY_LINKED: (
            "Project storage already lives at the new path. Looks already linked."
        ),
        State.AMBIGUOUS: (
            "Both old and new disk directories exist. Resolve this manually "
            "(decide which one is the truth) before relinking."
        ),
        State.BOTH_DISK_MISSING: (
            "Neither disk directory exists. Restore one of them before relinking."
        ),
    }[state]


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
    parser.add_argument(
        "--rename-disk",
        action="store_true",
        help=(
            "Also mv the project directory on disk from old to new path. "
            "Required when the disk dir hasn't been renamed yet."
        ),
    )
    args = parser.parse_args()

    old_path = resolve_path(args.old_path)
    new_path = resolve_path(args.new_path)
    state = detect_state(old_path, new_path)
    print_preflight(old_path, new_path, state)

    if args.dry_run:
        print("=== DRY RUN ===\n")

    # Blocking states: print the reason and exit.
    blocking = {
        State.IDENTICAL,
        State.OLD_STORAGE_MISSING,
        State.TARGET_STORAGE_OCCUPIED,
        State.AMBIGUOUS,
        State.BOTH_DISK_MISSING,
    }
    if state in blocking:
        print(f"Halting: {explain_blocking_state(state)}")
        return 1

    if state is State.ALREADY_LINKED:
        print(f"Nothing to do: {explain_blocking_state(state)}")
        return 0

    if state is State.NEEDS_DISK_RENAME and not args.rename_disk:
        print(
            "Disk directory has not been moved yet.\n"
            "  - If you want this script to do the rename, re-run with "
            "--rename-disk.\n"
            "  - If you'll mv the directory yourself, do that first then "
            "re-run without --rename-disk."
        )
        return 1

    step = 1
    if state is State.NEEDS_DISK_RENAME:
        print(f"Step {step}: Rename disk directory")
        if not rename_disk_dir(old_path, new_path, dry_run=args.dry_run):
            print("Halting before storage/history changes.")
            return 1
        print()
        step += 1

    print(f"Step {step}: Rename storage directory")
    if not rename_storage_dir(
        encode_path(old_path), encode_path(new_path), dry_run=args.dry_run
    ):
        print("Halting before history changes.")
        return 1
    print()
    step += 1

    print(f"Step {step}: Update history.jsonl")
    update_history(old_path, new_path, dry_run=args.dry_run)
    print()

    if args.dry_run:
        print("Re-run without --dry-run to apply changes.")
    else:
        print("Done. `--resume` and `--continue` will work from the new directory.")
        print(
            "Note: editors, terminals, or shells with the old path cached may "
            "need to be reopened."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
