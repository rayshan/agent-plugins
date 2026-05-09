---
name: link-claude-project
description: This skill should be used when the user asks to "link a project",
  "rename a project", "rename Claude Code project", "give my project a new name",
  "reconnect project data", "fix project sessions", "recover old sessions",
  "migrate Claude Code project", "moved my project directory", "can't find my old
  sessions", "resume not working after move", or mentions losing Claude Code
  session history, memories, or project data after moving or renaming a directory.
  Also use when the user mentions `--resume` or `--continue` not finding old
  conversations after a directory change.
argument-hint: <new-path> [old-path]
allowed-tools: Bash(python3 *), Bash(ls *), Bash(find *), Bash(mv *), Read, Grep, Glob
---

# Link Claude Code Project

Reconnect a moved or renamed project directory to its existing Claude Code
project data (sessions, memories, tool results). Claude Code stores project
data under `~/.claude/projects/<encoded-path>/` and references the original
absolute path in `~/.claude/history.jsonl`. When a directory moves, both
references go stale, breaking `--resume`, `--continue`, and project memory.

The skill handles two flows symmetrically:

- **Already moved/renamed.** The user has already `mv`'d the directory and now
  wants the Claude Code data relinked.
- **Pending rename.** The user wants the rename done and the data relinked in
  one go.

The script detects which case applies from on-disk state. The user's wording
is only a tiebreaker.

## Arguments

- `$0` — New project path (required). The intended/current location of the
  project.
- `$1` — Old project path (optional). The previous location.

## Workflow

### Step 1: Resolve paths

Resolve `$0` to an absolute path. If `$0` is not provided, ask the user.

If `$1` is provided, use it. Otherwise help the user identify the old path:

```bash
ls ~/.claude/projects/ | grep -i "<fragment>"
```

The encoding replaces every non-alphanumeric character with a hyphen, so it
is ambiguous (`/`, space, `~`, `_`, `=` all collapse). Show the encoded names
alongside best-guess decoded paths and let the user pick. If multiple
candidates remain, peek at session content:

```bash
find ~/.claude/projects/<candidate>/ -maxdepth 1 -name "*.jsonl" -exec head -1 {} \;
```

### Step 2: Preflight (dry-run)

Always start with a dry run. The script detects the on-disk state and prints
exactly what it would do:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/link-claude-project/scripts/link-claude-project.py" \
  "<old-path>" "<new-path>" --dry-run
```

The script prints a `State:` line. Possible states and the action each
implies:

| State                      | Action                                                                |
| -------------------------- | --------------------------------------------------------------------- |
| `relink_only`              | Disk dir already at new path. Relink storage + history.               |
| `needs_disk_rename`        | Disk dir still at old path. Re-run with `--rename-disk`.              |
| `already_linked`           | Storage already at new path. Nothing to do.                           |
| `identical`                | Old and new resolve to the same path. Halt.                           |
| `old_storage_missing`      | No project storage for old path. Halt — check the old path.           |
| `target_storage_occupied`  | Storage already exists at new path. Halt — manual merge needed.       |
| `ambiguous`                | Both disk dirs exist. Halt — user must pick the truth.                |
| `both_disk_missing`        | Neither disk dir exists. Halt — restore one first.                    |

### Step 3: Confirm and execute

Present the dry-run output and the planned changes (storage rename, history
entry count, optional disk rename) to the user. Wait for confirmation.

For `relink_only`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/link-claude-project/scripts/link-claude-project.py" \
  "<old-path>" "<new-path>"
```

For `needs_disk_rename`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/link-claude-project/scripts/link-claude-project.py" \
  "<old-path>" "<new-path>" --rename-disk
```

The script runs steps in this order so any failure leaves a recoverable
state:

1. Disk `mv` (only when `--rename-disk` is set; reversible by `mv` back).
2. Storage directory rename (reversible by `mv` back).
3. `history.jsonl` rewrite (backed up to `~/.claude/history.jsonl.bak`).

If a step fails, the script halts before the next one runs.

### Step 4: Report

The script's final output is authoritative — relay it. Report:

- The number of history entries rewritten (printed by the script).
- That `--resume` and `--continue` will work from the new directory.
- The backup location: `~/.claude/history.jsonl.bak`.
- Reminder: editors, terminals, and shells with the old path cached may need
  to be reopened.

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
| Project memories    | `<encoded>/memory/`                   | Lost — new directory starts fresh               |
| History entries     | `~/.claude/history.jsonl`             | Stale `project` field, no match on new path     |

What is NOT affected (no action needed):

- Plan files (`~/.claude/plans/`) — global, not path-keyed
- File history (`~/.claude/file-history/`) — keyed by content hash
- Active sessions (`~/.claude/sessions/`) — only tracks running PIDs
- `cwd` fields inside session transcripts — historical records only, not used
  for lookup

## Troubleshooting

**State `target_storage_occupied`** — The new location already has its own
sessions. The script refuses to overwrite. Options:

1. Manually merge: copy session files from the old encoded directory into
   the new one.
2. Back up the new encoded directory, remove it, then re-run the script.

**State `ambiguous`** — Both old and new disk directories exist. Decide which
is the truth (the other is likely a stale copy), remove or rename the loser,
and re-run.

**State `old_storage_missing`** — The old path may not match exactly. Encoding
is ambiguous, so paths that look the same may differ in special characters.
List all directories and look manually:

```bash
ls ~/.claude/projects/
```

**Encoding ambiguity** — Multiple original characters map to the same hyphen
(`/`, space, `~`, `_`, `=`). The encoded name alone cannot uniquely
reconstruct the original path. When helping users identify old directories,
check session content rather than relying on decoding the directory name.
