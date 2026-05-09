"""Argparse wiring and top-level command dispatch."""

from __future__ import annotations

import argparse
from datetime import datetime

from . import core, inspect, move, rename


# ---- command handlers ----


def cmd_rename(args: argparse.Namespace) -> int:
    old_path = core.resolve_path(args.old_path)
    new_path = core.resolve_path(args.new_path)
    state = rename.detect_rename_state(old_path, new_path)

    print(f"Old path:    {old_path}")
    print(f"New path:    {new_path}")
    print(f"Old encoded: {core.encode_path(old_path)}")
    print(f"New encoded: {core.encode_path(new_path)}")
    print(f"State:       {state.value}")
    print()

    if args.dry_run:
        print("=== DRY RUN ===\n")

    blocking = {
        rename.RenameState.IDENTICAL,
        rename.RenameState.OLD_STORAGE_MISSING,
        rename.RenameState.TARGET_STORAGE_OCCUPIED,
        rename.RenameState.AMBIGUOUS,
        rename.RenameState.BOTH_DISK_MISSING,
    }
    if state in blocking:
        print(f"Halting: {rename.explain_blocking_state(state)}")
        return 1

    if state is rename.RenameState.ALREADY_LINKED:
        print(f"Nothing to do: {rename.explain_blocking_state(state)}")
        return 0

    if state is rename.RenameState.NEEDS_DISK_RENAME and not args.rename_disk:
        print(
            "Disk directory has not been moved yet.\n"
            "  - If you want this script to do the rename, re-run with "
            "--rename-disk.\n"
            "  - If you'll mv the directory yourself, do that first then "
            "re-run without --rename-disk."
        )
        return 1

    step = 1
    if state is rename.RenameState.NEEDS_DISK_RENAME:
        print(f"Step {step}: Rename disk directory")
        if not rename.rename_disk_dir(old_path, new_path, dry_run=args.dry_run):
            print("Halting before storage/history changes.")
            return 1
        print()
        step += 1

    print(f"Step {step}: Rename storage directory")
    if not rename.rename_storage_dir(
        core.encode_path(old_path), core.encode_path(new_path), dry_run=args.dry_run
    ):
        print("Halting before history changes.")
        return 1
    print()
    step += 1

    print(f"Step {step}: Update history.jsonl")
    core.update_history(old_path, new_path, dry_run=args.dry_run)
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


def cmd_move(args: argparse.Namespace) -> int:
    src = core.resolve_path(args.src_path)
    dst = core.resolve_path(args.dst_path)

    if args.sessions:
        uuids = [u.strip() for u in args.sessions.split(",") if u.strip()]
    else:
        if args.last < 1:
            print("Error: --last must be a positive integer.")
            return 1
        uuids = inspect.select_last_n_sessions(src, args.last)
        available = len(uuids)
        if args.last > available:
            print(
                f"Note: requested --last {args.last}, "
                f"only {available} session(s) available."
            )

    state, bad = move.detect_move_state(src, dst, uuids)

    print(f"Source:      {src}")
    print(f"Destination: {dst}")
    print(f"Sessions:    {len(uuids)}")
    for u in uuids:
        print(f"  - {u}")
    print(f"State:       {state.value}")
    if bad:
        print(f"Affected:    {', '.join(bad)}")
    print()

    if args.dry_run:
        print("=== DRY RUN ===\n")

    if state is not move.MoveState.OK:
        print(f"Halting: {move.explain_blocking_state(state, bad)}")
        return 1

    print("Step 1: Move session files")
    if not move.move_sessions(src, dst, uuids, dry_run=args.dry_run):
        print("Halting before history changes.")
        return 1
    print()

    print("Step 2: Update history.jsonl")
    core.update_history(src, dst, dry_run=args.dry_run, session_ids=set(uuids))
    print()

    if args.dry_run:
        print("Re-run without --dry-run to apply changes.")
    else:
        print(f"Done. Moved {len(uuids)} session(s).")
        print(
            "Note: ~/.claude/session-env/<uuid>/ is UUID-keyed and stays in "
            "place — `--resume` finds it by sessionId regardless of project."
        )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    project = core.resolve_path(args.project_path)
    infos = inspect.gather_session_info(project)
    if not infos:
        print(f"No sessions found in storage for {project}.")
        return 1

    active = core.active_session_ids()
    print(f"Sessions in {project}:")
    print()
    print(f"{'UUID':<36}  {'mtime':<19}  {'size':>8}  flags  first user message")
    print(f"{'-' * 36}  {'-' * 19}  {'-' * 8}  -----  ---")
    for info in infos:
        ts = datetime.fromtimestamp(info.mtime).strftime("%Y-%m-%d %H:%M:%S")
        flags = (
            ("T" if info.has_tool_results else "-")
            + ("S" if info.has_subagents else "-")
            + ("A" if info.uuid in active else "-")
        )
        print(
            f"{info.uuid}  {ts}  {inspect.format_size(info.size):>8}  "
            f"{flags:>5}  {info.first_user_msg}"
        )
    print()
    print("Flags: T=tool-results, S=subagents, A=active")
    return 0


# ---- argparse wiring ----


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Claude Code project storage and history.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rename = sub.add_parser(
        "rename",
        help="Rename a project: move all data and history to a new path.",
    )
    p_rename.add_argument("old_path", help="Original absolute directory path")
    p_rename.add_argument("new_path", help="New absolute directory path")
    p_rename.add_argument(
        "--rename-disk",
        action="store_true",
        help=(
            "Also mv the project directory on disk. Required when the disk "
            "dir hasn't been renamed yet."
        ),
    )
    p_rename.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying anything",
    )
    p_rename.set_defaults(func=cmd_rename)

    p_move = sub.add_parser(
        "move",
        help="Move sessions from one project to another.",
    )
    p_move.add_argument("src_path", help="Source project absolute path")
    p_move.add_argument("dst_path", help="Destination project absolute path")
    selection = p_move.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--sessions",
        help="Comma-separated session UUIDs to move",
    )
    selection.add_argument(
        "--last",
        type=int,
        help="Move the N most recently modified sessions",
    )
    p_move.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying anything",
    )
    p_move.set_defaults(func=cmd_move)

    p_list = sub.add_parser(
        "list",
        help="List sessions in a project (UUID, mtime, size, flags, first message).",
    )
    p_list.add_argument("project_path", help="Project absolute path")
    p_list.set_defaults(func=cmd_list)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)
