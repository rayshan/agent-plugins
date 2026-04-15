# Import rules

- Global python development rules: @~/.claude/AGENTS-global-python.md

## Project rules

## Tech stack

- Primary language: markdown files, shell scripts and python scripts
- For scripting, prefer shell, but evaluate both shell and python
- Use the `shell-programming` skill for working with shell scripts.

## Marketplace structure

- `.claude-plugin/marketplace.json` - marketplace catalog (name, owner, plugins array)
- Official docs: <https://code.claude.com/docs/en/plugin-marketplaces.md>

## Plugin structure

Each plugin follows Claude Code plugin conventions:

- `.claude-plugin/plugin.json` - manifest (name, version, description, hooks paths)
- `hooks/hooks.json` - hook configuration (use `${CLAUDE_PLUGIN_ROOT}` for paths)
- `hooks/*.sh` - hook scripts (co-locate tests as `*.test.bats`)
- `skills/<skill-name>/SKILL.md` - skills (NOT `.claude/skills/` which is for standalone/personal skills)
- `agents/<agent-name>.md` - agents (auto-discovered, require name/description/model/color in frontmatter)

Commands (`commands/*.md`) are deprecated — write Skills (`skills/<name>/SKILL.md`) instead.

Skill frontmatter tips:

- `disable-model-invocation: true` - use for manual workflows with side effects (file edits, deploys, commits)
- Skills are auto-discovered from `skills/` directory; no need to add to plugin.json
- Testing local skill edits: `/skill-name` loads from `~/.claude/plugins/cache/`, not the local working copy. Use `cc --plugin-dir /path/to/plugin` to test local changes.

Large skill organization:

- `SKILL.md` - workflow instructions only, reference supporting files
- `templates/` - template files with `{{PLACEHOLDER}}` syntax
- `scripts/` - shell scripts (testable with shellcheck/bats)

## Testing

- Shell scripts: `shellcheck <script>` then `bats <script>.test.bats`
- Python scripts: `uvx ruff check <script>` then `uvx ruff format <script>` then `uvx pyrefly check <script>` then `uvx pytest <test> -v`
- Co-locate test files with source files
- Shell test files: `<script>.test.bats`
- Python test files: `<script>_test.py`

## Shell patterns

- Template substitution: use `${var//\{\{PLACEHOLDER\}\}/${value}}` (shell builtins) instead of sed to avoid escaping issues with `/`, `&`, `\` in values
- macOS ships bash 3.2: avoid bash 4+ features like `${var,,}` (lowercase), `${var^^}` (uppercase), associative arrays, `readarray`. Use `tr '[:upper:]' '[:lower:]'` for case conversion.
- Script testability: use `if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then main "$@"; fi` (instead of bare `main "$@"`) to allow sourcing functions in bats tests.

## Hook patterns

- Auto-skill activation: PreToolUse hooks can output plain text instructions telling Claude to use `Skill()` - simpler than injecting skill content via JSON `additionalContext`
- Reference: <https://github.com/spences10/claude-code-toolkit> for hook examples
- Project-level hooks: `.claude/settings.json` with `${CLAUDE_PROJECT_DIR}` for paths, scripts in `.claude/hooks/`. Plugin hooks: `hooks/hooks.json` with `${CLAUDE_PLUGIN_ROOT}`, scripts in `hooks/`.

## Markdown formatting

- All markdown files must pass `rumdl` (format then lint).
- A project-level PostToolUse hook (`.claude/hooks/lint-markdown.sh`) auto-formats and lints `.md` files after every Write/Edit. If it reports unfixable issues, fix them. If it reports auto-formatting, re-read the file before further edits.

## Claude Code internals

- Project data stored at `~/.claude/projects/<encoded-path>/` where encoding is `re.sub(r'[^a-zA-Z0-9]', '-', absolute_path)`
- Session transcripts: `<encoded-path>/<uuid>.jsonl`, history index: `~/.claude/history.jsonl`
- Moving a project directory breaks `--resume`/`--continue` — use `/link-claude-project` skill to reconnect
- LSP plugin config: `lspServers` is defined in marketplace catalog (`~/.claude/plugins/marketplaces/<mp>/.claude-plugin/marketplace.json`), not in cached plugin.json. Use `/setup-check-lsp` skill to diagnose LSP issues.

## Other

<EXTREMELY-IMPORTANT>
This project absolutely CANNOT contain PII and company-specific info.
Exceptions: project author name, gitignored files, reference to 1Password objects (must use Vault ID instead of Vault name).
</EXTREMELY-IMPORTANT>

- Go back to default command line tools when developing something that is meant to be shared with others, e.g. Claude Code marketplace plugins, when these better tools may not be present. E.g. use `find` instead of `fd`.
- You MUST load these skills when relevant:
  - `/plugin-dev:agent-development` for developing Agents
  - `/plugin-dev:hook-development` for developing Hooks
  - `/plugin-dev:mcp-integration` for integrating MCP servers
  - `/plugin-dev:plugin-settings` when I ask about Claude Code plugins
  - `/skill-creator:skill-creator` for developing Skills
- When developing Skills, or invoking the `skill-creator` skill, you MUST also read this supplement: @./skill-creator-supplement.md
- Every time you update a plugin:
  - Review the plugin manifest schema at <https://code.claude.com/docs/en/plugins-reference.md>, then update `plugin.json`.
