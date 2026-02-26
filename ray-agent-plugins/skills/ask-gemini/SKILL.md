---
name: ask-gemini
description: This skill should be used when the user asks to "ask Gemini", "use
  Gemini", "call Gemini", "get Gemini's opinion", "have Gemini review", or wants
  to delegate tasks to Gemini CLI including code review, architecture design, or
  Google Workspace operations (email, calendar, docs, drive).
argument-hint: [task-description]
---

# Ask Gemini

Delegate tasks to Gemini CLI in headless mode. Gemini provides access to Gemini models and Google Workspace services (Gmail, Calendar, Drive, Docs, Sheets, Slides, Chat).

## Prerequisites

Assume Gemini CLI is already installed. If command not found, direct the user to install it first.

## Usage

Pass the prompt as a positional argument:

```bash
gemini "What are the pros and cons of microservices vs monolith?"
```

Pipe content via stdin for code review:

```bash
cat src/auth.py | gemini "Review this code for security vulnerabilities"
```

Add directory context with `--include-directories`:

```bash
gemini "Analyze the authentication flow" --include-directories src/auth,src/middleware
```

### Google Workspace Operations

Add `--allowed-mcp-server-names=google-workspace` for any Workspace operation:

```bash
gemini "What meetings do I have today?" --allowed-mcp-server-names=google-workspace
```

```bash
gemini "Summarize my unread emails from the last 24 hours" --allowed-mcp-server-names=google-workspace
```

```bash
gemini "Create a Google Doc titled 'Meeting Notes' with an agenda template" --allowed-mcp-server-names=google-workspace
```

## Flags Reference

| Flag | Purpose |
|:-----|:--------|
| `--allowed-mcp-server-names=google-workspace` | Enable Workspace extension (Gmail, Calendar, Drive, Docs, Sheets, Slides, Chat) |
| `--include-directories <dirs>` | Comma-separated directories to add as code context |
| `--output-format json\|stream-json\|text` | Control output format (default: `text`). Use `json` for structured output |
| `--model <model>` | Specific Gemini model (default: `auto`) |
| `--approval-mode yolo` | Auto-approve all tool actions without confirmation |
| `--sandbox` | Sandboxed environment for safer execution |

## Exit Codes

| Code | Meaning |
|:-----|:--------|
| `0` | Success |
| `1` | General error or API failure |
| `42` | Input error (invalid prompt or arguments) |
| `53` | Turn limit exceeded |

## Output Handling

Gemini returns markdown-formatted text by default. Return its output as-is unless told to do further processing. Use `--output-format json` when structured output is needed for downstream scripting.

<!-- Reference docs:
- Headless mode: https://raw.githubusercontent.com/google-gemini/gemini-cli/refs/heads/main/docs/cli/headless.md
- CLI reference: https://raw.githubusercontent.com/google-gemini/gemini-cli/refs/heads/main/docs/cli/cli-reference.md
- Workspace extension: https://raw.githubusercontent.com/gemini-cli-extensions/workspace/refs/heads/main/docs/index.md
-->
