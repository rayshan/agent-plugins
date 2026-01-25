# agent-plugins

Personal Claude Code plugin marketplace.

## Plugins

### ray-plugins

Personal tools to augment AI coding agents.

**Hooks:**
- `block-dangerous-commands` - Blocks `rm`, `sudo`, `chmod 777` with safer alternatives

## Installation

```bash
claude --plugin-dir /path/to/plugin-name
```

Or add plugins to `~/.claude/plugins/`.
