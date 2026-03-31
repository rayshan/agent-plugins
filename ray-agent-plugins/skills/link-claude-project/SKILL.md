---
name: link-claude-project
description: This skill should be used when the user asks to "link a project",
  "reconnect project data", "fix project sessions", "recover old sessions",
  "migrate Claude Code project", "moved my project directory", "can't find my old
  sessions", "resume not working after move", or mentions losing Claude Code
  session history, memories, or project data after moving or renaming a directory.
  Also use when the user mentions `--resume` or `--continue` not finding old
  conversations after a directory change.
argument-hint: <new-path> [old-path]
disable-model-invocation: true
allowed-tools: Bash(python3 *), Bash(ls *), Bash(find *), Read, Grep, Glob
---

# Link Claude Code Project

Reconnect a moved or renamed project directory to its existing Claude Code
project data (sessions, memories, tool results). Claude Code stores project data
under `~/.claude/projects/<encoded-path>/` and references the original absolute
path in `~/.claude/history.jsonl`. When a directory moves, both references go
stale, breaking `--resume`, `--continue`, and project memory.

## Arguments

- `$0` — New project path (required). The current location of the project.
- `$1` — Old project path (optional). The original location before the move.

## Workflow

### Step 1: Resolve the new path

Resolve `$0` to an absolute path. Verify the directory exists.

If `$0` is not provided, ask the user for the new (current) project directory
path.

### Step 2: Determine the old path

**If `$1` is provided:** use it directly as the old path.

**If `$1` is not provided:** help the user find it. Ask what they remember about
the original directory — name fragments, parent directory, approximate location.
Then search for matches:

```bash
ls ~/.claude/projects/ | grep -i "<fragment>"
```

Present matching directories decoded back to human-readable paths (reverse the
encoding: leading dash was `/`, internal dashes were `/`, spaces, `~`, `_`, `=`,
or other special characters — the encoding is ambiguous so show the raw encoded
name alongside the decoded guess). Let the user pick.

If there are too many potential matches, narrow down by checking session content:

```bash
# Check first user message in each session for context clues
find ~/.claude/projects/<candidate>/ -maxdepth 1 -name "*.jsonl" -exec head -1 {} \;
```

### Step 3: Verify both paths

Before proceeding, confirm:

1. The new directory exists on disk
2. The old encoded directory exists under `~/.claude/projects/`
3. The new encoded directory does NOT already exist (to avoid overwriting)

If the new encoded directory already has data, warn the user and ask how to
proceed — this means the new location already has its own sessions.

### Step 4: Dry run

Always run the script in dry-run mode first:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/link-claude-project/scripts/link-claude-project.py" \
  "<old-path>" "<new-path>" --dry-run
```

Present the dry-run output to the user. Explain what will happen:

- **Storage directory rename** — moves project data (sessions, subagent logs,
  tool result cache, memories) to the new encoded path
- **History update** — rewrites the `project` field in matching
  `history.jsonl` entries so `--resume` and `--continue` find old sessions from
  the new directory

Ask the user to confirm before proceeding.

### Step 5: Execute

After user confirmation, run without `--dry-run`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/link-claude-project/scripts/link-claude-project.py" \
  "<old-path>" "<new-path>"
```

The script creates a backup at `~/.claude/history.jsonl.bak` before modifying
history.

### Step 6: Verify

After execution, confirm success:

```bash
# Storage directory exists at new location
ls ~/.claude/projects/<new-encoded>/

# History entries updated
grep -c "<new-path>" ~/.claude/history.jsonl
grep -c "<old-path>" ~/.claude/history.jsonl
```

Report to the user:

- Number of session files linked
- Number of history entries updated
- Remind them they can now use `--resume` and `--continue` from the new
  directory
- Note the backup location (`~/.claude/history.jsonl.bak`)

## Background: How Claude Code Stores Project Data

Claude Code encodes directory paths by replacing every non-alphanumeric
character with a hyphen: `/Users/me/My Project` becomes
`-Users-me-My-Project`. This encoded string is the directory name under
`~/.claude/projects/` where all project-specific data lives.

The `project` field in `~/.claude/history.jsonl` stores the original absolute
path and is what powers `--resume` (interactive session picker) and `--continue`
(resume most recent session in current directory). Both filter by matching the
current working directory against this field.

What is stored per project:

| Data | Location | Impact of move |
|---|---|---|
| Session transcripts | `<encoded>/<uuid>.jsonl` | Orphaned — `--resume` cannot find them |
| Subagent logs | `<encoded>/<uuid>/subagents/` | Orphaned with parent session |
| Tool result cache | `<encoded>/<uuid>/tool-results/` | Orphaned with parent session |
| Project memories | `<encoded>/memory/` | Lost — new directory starts fresh |
| History entries | `~/.claude/history.jsonl` | Stale `project` field, no match on new path |

What is NOT affected (no action needed):

- Plan files (`~/.claude/plans/`) — global, not path-keyed
- File history (`~/.claude/file-history/`) — keyed by content hash
- Active sessions (`~/.claude/sessions/`) — only tracks running PIDs
- `cwd` fields inside session transcripts — historical records only, not used
  for lookup

## Troubleshooting

**"Old storage directory not found"** — The old path may not match exactly. List
all project directories and look manually:

```bash
ls ~/.claude/projects/
```

**"New storage directory already exists"** — The user has already started new
sessions from the new directory. The script refuses to overwrite. Options:

1. Manually merge: copy session files from old to new directory
2. Back up the new directory, delete it, then re-run the script

**Encoding ambiguity** — Multiple original characters map to the same hyphen
(`/`, space, `~`, `_`, `=`). The encoded name alone cannot uniquely reconstruct
the original path. When helping users identify old directories, always check
session content for confirmation rather than relying solely on decoding the
directory name.
