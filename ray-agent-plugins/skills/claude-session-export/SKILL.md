---
name: claude-session-export
description: This skill should be used when the user asks to "export a session",
  "export a transcript", "share a conversation", "save session as markdown",
  "convert transcript to markdown", or wants to create a readable version of a
  Claude Code session for sharing. Also use when the user provides a session UUID
  and wants it exported, or mentions sharing Claude Code conversations with others.
argument-hint: <project-path> <session-name>
disable-model-invocation: true
allowed-tools: Bash(python3 *)
---

Export a local Claude Code session transcript to a human-readable markdown file
for sharing.

## Usage

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/claude-session-export/scripts/claude_session_export.py" \
  "<project-path>" "<session-name-or-uuid>" [output-file]
```

- **project-path**: Absolute path to the project directory (e.g., `/Users/me/my-project`)
- **session-name**: A session name substring (e.g., `"cap table chart"`).
  Case-insensitive, matches against the session's last title. Errors if no match
  or multiple matches. Also accepts a full UUID.
- **output-file** (optional): Override the default filename

Default output filename: `claude-transcript-<agent-name-slug>-<YYYY-MM-DD>.md`,
falling back to session UUID when no agent name exists. Date is taken from the
last message in the session.

## What the script includes

| Included | Excluded |
| --- | --- |
| User-authored messages | Tool calls and results |
| Claude text responses | Extended thinking blocks |
| Session title and agent name (as header) | System-injected XML tags |
| Skill invocation notes (name only) | Skill content |

Skill invocations appear as a short Claude message: `Loaded ⚡️ Skill <name>`.

## Arguments

If the user provides arguments inline (e.g., `/claude-session-export /path "cap table"`),
pass `$0` as the project path and `$1` as the session name.

If no arguments are provided, ask the user for:

1. The project directory path
2. The session name (or UUID for unnamed sessions)

## Output format

The exported markdown uses heavy horizontal rules (`━` x 80) between messages,
with emoji role markers (`👤 User`, `🤖 Claude`) and timestamps.
