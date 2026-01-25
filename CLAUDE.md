# Import rules

- Global software development rules: @~/.claude/AGENTS-global.md
- Global shell script development rules: @~/.claude/AGENTS-global-shell.md

# Project rules

## Marketplace structure

- `.claude-plugin/marketplace.json` - marketplace catalog (name, owner, plugins array)
- Official docs: https://code.claude.com/docs/en/plugin-marketplaces.md

## Plugin structure

Each plugin follows Claude Code plugin conventions:
- `.claude-plugin/plugin.json` - manifest (name, version, description, hooks/commands paths)
- `hooks/hooks.json` - hook configuration (use `${CLAUDE_PLUGIN_ROOT}` for paths)
- `hooks/*.sh` - hook scripts (co-locate tests as `*.test.bats`)
- `commands/*.md` - command files (YAML frontmatter + markdown instructions)
- `skills/<skill-name>/SKILL.md` - skills (NOT `.claude/skills/` which is for standalone/personal skills)

## Testing

- Shell scripts: `shellcheck <script>` then `bats <script>.test.bats`
- Co-locate test files with source files

## Other

- Go back to default command line tools when developing something that is meant to be shared with others, e.g. Claude Code marketplace plugins, when these better tools may not be present. E.g. use `find` instead of `fd`.
- You MUST load these skills when relevant:
	- `/plugin-dev:agent-development` for developing Agents
	- `/plugin-dev:command-development` for developing Commands
	- `/plugin-dev:hook-development` for developing Hooks
	- `/plugin-dev:mcp-integration` for integrating MCP servers
	- `/plugin-dev:plugin-settings` when I ask about Claude Code plugins
	- `/plugin-dev:skill-development` for developing Skills
- When developing Skills and Commands, you MUST also read this official documentation first: https://code.claude.com/docs/en/skills.md
- Every time you update a plugin:
	- Run the `plugin-dev:plugin-validator` agent.
	- Review the plugin manifest schema at https://code.claude.com/docs/en/plugins-reference.md, then update `plugin.json`.