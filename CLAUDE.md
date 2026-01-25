# Import rules

- Global software development rules: @~/.claude/AGENTS-global.md
- Global shell script development rules: @~/.claude/AGENTS-global-shell.md

# Project rules

## Marketplace structure

- `.claude-plugin/marketplace.json` - marketplace catalog (name, owner, plugins array)
- Official docs: https://code.claude.com/docs/en/plugin-marketplaces.md

## Plugin structure

Each plugin follows Claude Code plugin conventions:
- `.claude-plugin/plugin.json` - manifest (name, version, description, hooks path)
- `hooks/hooks.json` - hook configuration (use `${CLAUDE_PLUGIN_ROOT}` for paths)
- `hooks/*.sh` - hook scripts (co-locate tests as `*.test.bats`)

## Testing

- Shell scripts: `shellcheck <script>` then `bats <script>.test.bats`
- Co-locate test files with source files