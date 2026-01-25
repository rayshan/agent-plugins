# ray-plugins

Safety hooks and productivity commands for Claude Code.

## Installation

```bash
/plugin install ray-plugins@ray-agent-plugins
```

## Commands

| Command | Description |
|---------|-------------|
| `/update-docs` | Revise CLAUDE.md and README.md to reflect latest changes |

## Hooks

### block-dangerous-commands

Intercepts bash commands and blocks:

| Command | Risk | Alternative |
|---------|------|-------------|
| `rm` | Data loss | Move to `TRASH/` folder, log to `TRASH-FILES.md` |
| `sudo` | Privilege escalation | Check if elevated privileges are needed |
| `chmod 777` | Insecure permissions | Use `755` (dirs) or `644` (files) |
