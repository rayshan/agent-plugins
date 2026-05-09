"""Rename mode: classify a (old, new) pair and apply rename primitives.

Order of operations is most-reversible-first so any failure leaves a
recoverable state:
    1. disk mv (optional)         — reversible by mv'ing back
    2. storage directory rename   — reversible by mv'ing back
    3. history.jsonl rewrite      — backup at history.jsonl.bak
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from . import core


class RenameState(Enum):
    """Detected on-disk state for a rename (old_path, new_path) pair."""

    IDENTICAL = "identical"
    OLD_STORAGE_MISSING = "old_storage_missing"
    TARGET_STORAGE_OCCUPIED = "target_storage_occupied"
    ALREADY_LINKED = "already_linked"
    AMBIGUOUS = "ambiguous"
    BOTH_DISK_MISSING = "both_disk_missing"
    NEEDS_DISK_RENAME = "needs_disk_rename"
    RELINK_ONLY = "relink_only"


def detect_rename_state(old_path: str, new_path: str) -> RenameState:
    """Classify a (old, new) pair against on-disk state.

    Storage-side conditions take priority over disk-side conditions because
    storage absence/conflict makes any disk action moot.
    """
    if old_path == new_path:
        return RenameState.IDENTICAL

    old_enc_exists = (core.PROJECTS_DIR / core.encode_path(old_path)).exists()
    new_enc_exists = (core.PROJECTS_DIR / core.encode_path(new_path)).exists()

    if not old_enc_exists and new_enc_exists:
        return RenameState.ALREADY_LINKED
    if not old_enc_exists:
        return RenameState.OLD_STORAGE_MISSING
    if new_enc_exists:
        return RenameState.TARGET_STORAGE_OCCUPIED

    old_disk_exists = Path(old_path).exists()
    new_disk_exists = Path(new_path).exists()

    if old_disk_exists and new_disk_exists:
        return RenameState.AMBIGUOUS
    if not old_disk_exists and not new_disk_exists:
        return RenameState.BOTH_DISK_MISSING
    if old_disk_exists:
        return RenameState.NEEDS_DISK_RENAME
    return RenameState.RELINK_ONLY


def rename_disk_dir(old_path: str, new_path: str, *, dry_run: bool) -> bool:
    """Rename the on-disk project directory."""
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
    """Rename the project storage directory."""
    old_dir = core.PROJECTS_DIR / old_encoded
    new_dir = core.PROJECTS_DIR / new_encoded

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


def explain_blocking_state(state: RenameState) -> str:
    """One-line explanation for a state that blocks execution."""
    return {
        RenameState.IDENTICAL: "Old and new paths are identical after resolution.",
        RenameState.OLD_STORAGE_MISSING: (
            "No project storage exists for the old path. Nothing to relink — "
            "check that the old path is correct."
        ),
        RenameState.TARGET_STORAGE_OCCUPIED: (
            "Project storage already exists at the new path. The new directory "
            "has its own sessions; merge manually before relinking."
        ),
        RenameState.ALREADY_LINKED: (
            "Project storage already lives at the new path. Looks already linked."
        ),
        RenameState.AMBIGUOUS: (
            "Both old and new disk directories exist. Resolve this manually "
            "(decide which one is the truth) before relinking."
        ),
        RenameState.BOTH_DISK_MISSING: (
            "Neither disk directory exists. Restore one of them before relinking."
        ),
    }[state]
