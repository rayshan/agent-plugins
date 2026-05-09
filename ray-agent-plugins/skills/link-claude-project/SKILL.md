---
name: link-claude-project
description: This skill should be used when the user asks to "link a project",
  "rename a project", "rename Claude Code project", "give my project a new name",
  "reconnect project data", "fix project sessions", "recover old sessions",
  "migrate Claude Code project", "moved my project directory", "can't find my old
  sessions", "resume not working after move", "move a session between projects",
  "transfer a Claude Code session", "list sessions in a project", or mentions
  losing Claude Code session history, memories, or project data after moving or
  renaming a directory. Also use when the user mentions `--resume` or `--continue`
  not finding old conversations after a directory change.
argument-hint: <subcommand> [args...]
allowed-tools: Bash(python3 *), Bash(ls *), Bash(find *), Bash(mv *), Read, Grep, Glob
---

# Link Claude Code Project

Manage Claude Code project storage and history. Claude Code stores project
data under `~/.claude/projects/<encoded-path>/` and references the original
absolute path in the `project` field of `~/.claude/history.jsonl`. Both go
stale when a directory moves or sessions need to be reattributed, breaking
`--resume`, `--continue`, and project memory.

The skill exposes three subcommands:

| Subcommand | Purpose |
| ---------- | ------- |
| `rename`   | Move all of a project's data and history to a new path. Optionally `mv` the disk dir. |
| `move`     | Move specific session(s) from one project to another. Both projects continue to exist. |
| `list`     | Show sessions in a project so the user can pick UUIDs to feed into `move`. |

## Picking the right subcommand

| User intent                                                                | Use      |
| -------------------------------------------------------------------------- | -------- |
| "I moved/renamed my project, fix Claude Code"                              | `rename` |
| "Rename project X to Y" (do the `mv` for me too)                           | `rename` with `--rename-disk` |
| "Move my last session from project A to project B"                         | `move --last 1` |
| "Move session UUID … to project X"                                         | `move --sessions <uuid>` |
| "What sessions does project X have?"                                       | `list` |

If the user wants every session of A moved to B, that's `rename` (semantically
A becomes B), not `move`.

## Subcommand: `rename`

### Workflow

1. Resolve the new path (and old path; help the user identify it from
   `ls ~/.claude/projects/`).
2. Run with `--dry-run`. The script prints a `State:` line.
3. Pick the action based on state (table below).
4. Confirm with the user, then run without `--dry-run`.
5. Relay the script's authoritative final output.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/link-claude-project/scripts/link-claude-project.py" \
  rename "<old-path>" "<new-path>" --dry-run
```

### Rename states

| State                     | Action                                                              |
| ------------------------- | ------------------------------------------------------------------- |
| `relink_only`             | Disk dir already at new path. Run without flags.                    |
| `needs_disk_rename`       | Disk dir still at old path. Re-run with `--rename-disk`.            |
| `already_linked`          | Storage already at new path. Nothing to do.                         |
| `identical`               | Old and new resolve to the same path. Halt.                         |
| `old_storage_missing`     | No project storage for old path. Halt — check the old path.         |
| `target_storage_occupied` | Storage already exists at new path. Halt — manual merge needed.     |
| `ambiguous`               | Both disk dirs exist. Halt — user must pick the truth.              |
| `both_disk_missing`       | Neither disk dir exists. Halt — restore one first.                  |

### Order of operations (rename)

1. Disk `mv` (only when `--rename-disk` is set; reversible by `mv` back).
2. Storage directory rename (reversible by `mv` back).
3. `history.jsonl` rewrite (backed up to `~/.claude/history.jsonl.bak`).

If a step fails, the script halts before the next one runs.

## Subcommand: `move`

Move one or more sessions from one project's storage to another's. Both
projects keep existing — only the named sessions migrate.

### Workflow

1. Run `list` on the source project so the user can see UUIDs and pick.
2. Run `move --dry-run` with either explicit UUIDs or `--last N`.
3. Confirm the planned moves with the user.
4. Run without `--dry-run`.

```bash
# Pick UUIDs explicitly:
python3 "${CLAUDE_PLUGIN_ROOT}/skills/link-claude-project/scripts/link-claude-project.py" \
  move "<src>" "<dst>" --sessions "<uuid1>,<uuid2>" --dry-run

# Or take the N most recent:
python3 "${CLAUDE_PLUGIN_ROOT}/skills/link-claude-project/scripts/link-claude-project.py" \
  move "<src>" "<dst>" --last 1 --dry-run
```

`--sessions` and `--last` are mutually exclusive; one is required.

### Move states

| State                       | Action                                                             |
| --------------------------- | ------------------------------------------------------------------ |
| `ok`                        | Proceed with the move.                                             |
| `no_sessions_selected`      | Empty selection. Pass `--sessions` or `--last`.                    |
| `src_dst_identical`         | Source and destination are the same path. Halt.                    |
| `src_storage_missing`       | No project storage for source. Halt — check the source path.       |
| `dst_disk_missing`          | Destination dir doesn't exist on disk. Halt — `--resume` needs it. |
| `session_not_found`         | A requested UUID isn't in source storage. Halt with the bad list.  |
| `session_already_in_target` | Target already has a session with that UUID. Halt with the list.   |
| `active_session`            | A requested UUID is currently running. Halt — would corrupt state. |

### Order of operations (move)

1. Per-session file moves (jsonl + the optional `<uuid>/` subdir holding
   `tool-results/` / `subagents/`). Rolled back in reverse order if a later
   move in the batch fails.
2. `history.jsonl` rewrite — only entries where both `project == src` and
   `sessionId ∈ {moved UUIDs}` are rewritten. Backup at
   `~/.claude/history.jsonl.bak`.

`~/.claude/session-env/<uuid>/` stays put — it's keyed by session UUID, not
by project path. `--resume` finds it by sessionId regardless of project.

## Subcommand: `list`

Show sessions in a project so UUIDs and first-message context are visible.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/link-claude-project/scripts/link-claude-project.py" \
  list "<project-path>"
```

Columns: UUID, mtime, size, flags, first user message. Flags are three
characters: `T` if `tool-results/` exists, `S` if `subagents/` exists, `A`
if the session is currently running.

## Reporting back

The script's final output is authoritative — relay it. Report:

- Number of history entries rewritten or sessions moved (printed by the script).
- That `--resume` and `--continue` work from the new directory (rename) or
  destination project (move).
- Backup location: `~/.claude/history.jsonl.bak`.
- For `rename`: editors, terminals, and shells with the old path cached may
  need to be reopened.

Do **not** run `grep -c "<old-path>" ~/.claude/history.jsonl` to verify —
substring matches catch user-typed prompt text and produce false positives.
The script counts `project` field rewrites authoritatively.

## Background: How Claude Code Stores Project Data

Claude Code encodes directory paths by replacing every non-alphanumeric
character with a hyphen: `/Users/me/My Project` becomes
`-Users-me-My-Project`. This encoded string is the directory name under
`~/.claude/projects/` where all project-specific data lives.

The `project` field in `~/.claude/history.jsonl` stores the original absolute
path and is what powers `--resume` (interactive session picker) and
`--continue` (resume most recent session in current directory). Both filter
by matching the current working directory against this field.

What is stored per project:

| Data                | Location                              | Impact of move                                  |
| ------------------- | ------------------------------------- | ----------------------------------------------- |
| Session transcripts | `<encoded>/<uuid>.jsonl`              | Orphaned — `--resume` cannot find them          |
| Subagent logs       | `<encoded>/<uuid>/subagents/`         | Orphaned with parent session                    |
| Tool result cache   | `<encoded>/<uuid>/tool-results/`      | Orphaned with parent session                    |
| Project memories    | `<encoded>/memory/`                   | Lost — new directory starts fresh (project-level, not session-level) |
| History entries     | `~/.claude/history.jsonl`             | Stale `project` field, no match on new path     |

What is NOT affected (no action needed):

- Plan files (`~/.claude/plans/`) — global, not path-keyed
- File history (`~/.claude/file-history/`) — keyed by content hash
- Session env (`~/.claude/session-env/<uuid>/`) — UUID-keyed, found by sessionId
- Active session tracker (`~/.claude/sessions/<pid>.json`) — PID-keyed
- `cwd` fields inside session transcripts — historical records only

## Troubleshooting

**`target_storage_occupied`** (rename) — The new location already has its
own sessions. The script refuses to overwrite. Either manually merge session
files into the existing encoded directory, or back up the new encoded
directory, remove it, and re-run.

**`ambiguous`** (rename) — Both old and new disk directories exist. Decide
which is the truth (the other is likely a stale copy), remove or rename the
loser, and re-run.

**`old_storage_missing`** / **`src_storage_missing`** — The path may not
match exactly. Encoding is ambiguous, so paths that look the same may differ
in special characters. List directories manually:

```bash
ls ~/.claude/projects/
```

**`session_already_in_target`** (move) — A session with the same UUID
already exists in the destination. Move it under a different project, or
inspect both files and decide which to keep.

**`active_session`** (move) — A session is currently running. Either pick a
different session, wait for the running session to end, or shut down the
client first.

**Encoding ambiguity** — Multiple original characters map to the same hyphen
(`/`, space, `~`, `_`, `=`). The encoded name alone cannot uniquely
reconstruct the original path. When helping users identify old directories,
check session content rather than relying on decoding the directory name.
