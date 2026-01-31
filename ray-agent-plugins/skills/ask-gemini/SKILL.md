---
name: ask-gemini
description: This skill should be used when the user asks to "ask Gemini", "use Gemini", "call Gemini", "get Gemini's opinion", "have Gemini review", or wants to delegate tasks to Gemini CLI including code review, architecture design, or Google Workspace operations (email, calendar, docs, drive).
argument-hint: [task-description]
docs-on-gemini-cli-headless-mode: https://raw.githubusercontent.com/google-gemini/gemini-cli/refs/heads/main/docs/cli/headless.m
docs-on-gemini-cli-workspace-extension: https://raw.githubusercontent.com/gemini-cli-extensions/workspace/refs/heads/main/docs/index.m
---

# Ask Gemini

Delegate tasks to Gemini CLI running in headless mode. Gemini CLI provides access to Gemini models and Google Workspace services (Gmail, Calendar, Drive, Docs, Sheets, Slides, Chat).

## Prerequisites

Assume Gemini CLI is already installed. If command not found, direct the user to install Gemini CLI first.

## Usage Patterns

### Simple Queries

For general questions or brainstorming:

```bash
gemini -p "What are the pros and cons of microservices vs monolith?"
```

### Code Review and Analysis

Pipe file content to Gemini for review:

```bash
cat src/auth.py | gemini -p "Review this code for security vulnerabilities"
```

For multiple files or directory context:

```bash
gemini -p "Analyze the authentication flow in this codebase" --include-directories src/auth,src/middleware
```

### Google Workspace Operations

For any Workspace operation (Gmail, Calendar, Drive, Docs, etc.), add the `--allowed-mcp-server-names=google-workspace` flag:

```bash
gemini -p "What meetings do I have today?" --allowed-mcp-server-names=google-workspace
```

```bash
gemini -p "Summarize my unread emails from the last 24 hours" --allowed-mcp-server-names=google-workspace
```

```bash
gemini -p "Create a Google Doc titled 'Meeting Notes' with an agenda template" --allowed-mcp-server-names=google-workspace
```

## Common Tasks

| Task | Command |
|------|---------|
| Code review | `cat file.py \| gemini -p "Review for bugs and improvements"` |
| Architecture design | `gemini -p "Design a system for X" --include-directories src,docs` |
| Email triage | `gemini -p "Summarize unread emails" --allowed-mcp-server-names=google-workspace` |
| Calendar check | `gemini -p "What's on my calendar today?" --allowed-mcp-server-names=google-workspace` |
| Create document | `gemini -p "Create a Google Doc titled X" --allowed-mcp-server-names=google-workspace` |
| Search Drive | `gemini -p "Find documents about project X" --allowed-mcp-server-names=google-workspace` |

## Flags Reference

| Flag | Purpose |
|------|---------|
| `-p` / `--prompt` | Enable headless mode with the given prompt |
| `--allowed-mcp-server-names=google-workspace` | Required for Workspace extension (Gmail, Calendar, Drive, Docs, etc.) |
| `--include-directories` | Add source directories for code context |

## Output Handling

Gemini CLI is a smart AI agent. It returns markdown-formatted text by default. Return its output as-is, unless you're told to do further processing, e.g. saving the output into a file.

## Workspace Extension Capabilities

When using `--allowed-mcp-server-names=google-workspace`, Gemini can:

- **Docs**: Create documents, insert/append/replace text, search
- **Slides**: Extract text, search presentations
- **Sheets**: Extract data, search spreadsheets
- **Drive**: Search files, manage folders, download files
- **Calendar**: View schedule, create events, check availability, RSVP
- **Chat**: Send messages, view threads, navigate spaces
- **Gmail**: Search, read, send emails, manage drafts and labels
