# Import rules

- Global software development rules: @~/.claude/AGENTS-global.md

# Project rules

## Tech stack

- Primary language: shell scripts and markdown instructions

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
- `agents/<agent-name>.md` - agents (auto-discovered, require name/description/model/color in frontmatter)

Skill frontmatter tips:
- `disable-model-invocation: true` - use for manual workflows with side effects (file edits, deploys, commits)
- Skills are auto-discovered from `skills/` directory; no need to add to plugin.json

Large skill organization:
- `SKILL.md` - workflow instructions only, reference supporting files
- `templates/` - template files with `{{PLACEHOLDER}}` syntax
- `scripts/` - shell scripts (testable with shellcheck/bats)

## Testing

- Shell scripts: `shellcheck <script>` then `bats <script>.test.bats`
- Co-locate test files with source files

## Shell patterns

- Template substitution: use `${var//\{\{PLACEHOLDER\}\}/${value}}` (shell builtins) instead of sed to avoid escaping issues with `/`, `&`, `\` in values

## Hook patterns

- Auto-skill activation: PreToolUse hooks can output plain text instructions telling Claude to use `Skill()` - simpler than injecting skill content via JSON `additionalContext`
- Reference: https://github.com/spences10/claude-code-toolkit for hook examples

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
	- Review the plugin manifest schema at https://code.claude.com/docs/en/plugins-reference.md, then update `plugin.json`.