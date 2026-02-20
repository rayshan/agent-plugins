# ray-agent-plugins

Safety hooks and productivity skills for Claude Code.

## Installation

```bash
/plugin install ray-agent-plugins
```

## Skills

| Skill | Description |
|-------|-------------|
| `/ray-agent-plugins:ask-gemini` | Delegate tasks to Gemini CLI (code review, architecture, Google Workspace ops) |
| `/ray-agent-plugins:update-docs` | Update CLAUDE.md and README.md to reflect latest changes |
| `/ray-agent-plugins:bump-plugin-version` | Bump a plugin's version (major/minor/patch/exact) |
| `/ray-agent-plugins:get-markdown` | Convert URLs to markdown (predefined patterns + Tabstack fallback for any URL) |
| `/ray-agent-plugins:shell-programming` | Shell scripting best practices based on Google Shell Style Guide |
| `/ray-agent-plugins:audio-normalize` | Preprocess and normalize audio for speech transcription using ffmpeg |
| `/ray-agent-plugins:macos-app-bootstrap` | Bootstrap a macOS desktop app using Swift Package Manager |

## Agents

| Agent | Description |
|-------|-------------|
| `code-simplifier` | Aggressive code refactoring specialist that reduces complexity and enforces idiomatic patterns |

## Hooks

### block-dangerous-commands

Intercepts bash commands and blocks:

| Command | Risk | Alternative |
|---------|------|-------------|
| `rm` | Data loss | Move to `~/.trash/` with timestamp suffix |
| `sudo` | Privilege escalation | Check if elevated privileges are needed |
| `chmod 777` | Insecure permissions | Use `755` (dirs) or `644` (files) |

### inject-shell-skill

Auto-activates the `shell-programming` skill when writing or editing shell scripts (`.sh`, `.bash`, `.zsh`, `.ksh`, `.bats` or files with shell shebang).
