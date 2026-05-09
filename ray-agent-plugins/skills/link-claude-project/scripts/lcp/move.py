"""Move mode: classify a session-move request and apply move primitives.

Order of operations halts on first failure:
    1. per-session file moves (rolled back on failure within the batch)
    2. history.jsonl rewrite (backup at history.jsonl.bak)
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from . import core


class MoveState(Enum):
    """Detected state for a session-move operation."""

    OK = "ok"
    SRC_DST_IDENTICAL = "src_dst_identical"
    SRC_STORAGE_MISSING = "src_storage_missing"
    DST_DISK_MISSING = "dst_disk_missing"
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_ALREADY_IN_TARGET = "session_already_in_target"
    ACTIVE_SESSION = "active_session"
    NO_SESSIONS_SELECTED = "no_sessions_selected"


def detect_move_state(
    src_path: str, dst_path: str, uuids: list[str]
) -> tuple[MoveState, list[str]]:
    """Classify a session-move request.

    Returns (state, problematic_uuids). The list is non-empty for
    SESSION_NOT_FOUND, SESSION_ALREADY_IN_TARGET, and ACTIVE_SESSION; empty
    otherwise.
    """
    if not uuids:
        return (MoveState.NO_SESSIONS_SELECTED, [])
    if src_path == dst_path:
        return (MoveState.SRC_DST_IDENTICAL, [])

    src_storage = core.PROJECTS_DIR / core.encode_path(src_path)
    if not src_storage.exists():
        return (MoveState.SRC_STORAGE_MISSING, [])

    if not Path(dst_path).exists():
        return (MoveState.DST_DISK_MISSING, [])

    missing = [u for u in uuids if not (src_storage / f"{u}.jsonl").exists()]
    if missing:
        return (MoveState.SESSION_NOT_FOUND, missing)

    dst_storage = core.PROJECTS_DIR / core.encode_path(dst_path)
    if dst_storage.exists():
        already = [u for u in uuids if (dst_storage / f"{u}.jsonl").exists()]
        if already:
            return (MoveState.SESSION_ALREADY_IN_TARGET, already)

    active = core.active_session_ids()
    in_flight = [u for u in uuids if u in active]
    if in_flight:
        return (MoveState.ACTIVE_SESSION, in_flight)

    return (MoveState.OK, [])


def explain_blocking_state(state: MoveState, bad: list[str]) -> str:
    """One-line explanation for a state that blocks or short-circuits execution."""
    if state is MoveState.NO_SESSIONS_SELECTED:
        return "No sessions selected. Pass --sessions or --last."
    if state is MoveState.SRC_DST_IDENTICAL:
        return "Source and destination paths are identical."
    if state is MoveState.SRC_STORAGE_MISSING:
        return "No project storage exists for the source path."
    if state is MoveState.DST_DISK_MISSING:
        return (
            "Destination path does not exist on disk. Sessions need a real "
            "working directory for `--resume` to filter on."
        )
    if state is MoveState.SESSION_NOT_FOUND:
        return f"Session(s) not found in source: {', '.join(bad)}"
    if state is MoveState.SESSION_ALREADY_IN_TARGET:
        return f"Session(s) already exist in target: {', '.join(bad)}"
    if state is MoveState.ACTIVE_SESSION:
        return f"Session(s) appear active and will not be moved: {', '.join(bad)}"
    return ""


def move_sessions(
    src_path: str, dst_path: str, uuids: list[str], *, dry_run: bool
) -> bool:
    """Move session jsonl files (and per-session subdirs) between storage dirs.

    On any failure during execution, previously-completed moves in this batch
    are rolled back in reverse order. Returns True on success.
    """
    src_storage = core.PROJECTS_DIR / core.encode_path(src_path)
    dst_storage = core.PROJECTS_DIR / core.encode_path(dst_path)

    if not dst_storage.exists():
        if dry_run:
            print(f"  Would create {dst_storage}")
        else:
            dst_storage.mkdir(parents=True)
            print(f"  Created {dst_storage}")

    completed: list[tuple[Path, Path]] = []  # (current_location, original_location)

    def do_move(src: Path, dst: Path) -> None:
        if dry_run:
            print(f"  Would move:\n    {src}\n  → {dst}")
            return
        # Defensive: Path.rename overwrites existing files silently on POSIX.
        # Refuse rather than clobber if a collision slipped past detect_move_state.
        if dst.exists():
            raise FileExistsError(f"destination already exists: {dst}")
        src.rename(dst)
        completed.append((dst, src))
        print(f"  Moved:\n    {src}\n  → {dst}")

    try:
        for uuid in uuids:
            src_jsonl = src_storage / f"{uuid}.jsonl"
            dst_jsonl = dst_storage / f"{uuid}.jsonl"
            do_move(src_jsonl, dst_jsonl)

            src_subdir = src_storage / uuid
            if src_subdir.exists():
                dst_subdir = dst_storage / uuid
                do_move(src_subdir, dst_subdir)
        return True
    except OSError as e:
        print(f"  Error during move: {e}")
        if dry_run:
            return False
        if completed:
            print("  Rolling back…")
            for current, original in reversed(completed):
                try:
                    current.rename(original)
                    print(f"  Restored {original}")
                except OSError as roll_err:
                    print(f"  WARNING: failed to restore {original}: {roll_err}")
        return False
