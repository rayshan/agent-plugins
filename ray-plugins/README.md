# ray-plugins

Safety hooks to block dangerous bash commands.

## Installation

```bash
/plugin install ray-plugins@ray-agent-plugins
```

## Hooks

### block-dangerous-commands

Intercepts bash commands and blocks:

| Command | Risk | Alternative |
|---------|------|-------------|
| `rm` | Data loss | Move to `TRASH/` folder, log to `TRASH-FILES.md` |
| `sudo` | Privilege escalation | Check if elevated privileges are needed |
| `chmod 777` | Insecure permissions | Use `755` (dirs) or `644` (files) |
