# ray-plugins

Personal tools to augment AI coding agents.

## Features

### Hooks

- **block-dangerous-commands**: Blocks dangerous bash commands (`rm`, `sudo`, `chmod 777`) and suggests safer alternatives

## Installation

Add to your Claude Code plugins:

```bash
claude --plugin-dir /path/to/ray-plugins
```

Or add to marketplace and install via plugin manager.

## Components

### block-dangerous-commands Hook

Intercepts bash commands and blocks:

| Command | Risk | Alternative |
|---------|------|-------------|
| `rm` (any) | Data loss | Move to `TRASH/` folder, log to `TRASH-FILES.md` |
| `sudo` | Privilege escalation | Check if elevated privileges are needed |
| `chmod 777` | Insecure permissions | Use `755` (dirs) or `644` (files) |
