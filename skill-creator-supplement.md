---
updated_at: 2026-02-25
---

# Skill Creator Supplement

Supplementary reference for the `skill-creator:skill-creator` skill. Contains detailed information from the official Claude Code skills documentation and the `plugin-dev:skill-development` skill that skill-creator does not cover.

## Sources

- [Official docs](https://code.claude.com/docs/en/skills.md)
- `plugin-dev:skill-development` skill

## Additional Frontmatter Fields

Skill-creator covers `name`, `description`, and `compatibility`. These additional fields are also available:

| Field                      | Description                                                                                                             |
| :------------------------- | :---------------------------------------------------------------------------------------------------------------------- |
| `argument-hint`            | Hint shown during autocomplete for expected arguments. Example: `[issue-number]` or `[filename] [format]`.              |
| `disable-model-invocation` | `true` prevents Claude from automatically loading this skill. For manual-only workflows like `/commit`, `/deploy`.      |
| `user-invocable`           | `false` hides from the `/` menu. For background knowledge Claude should use but users shouldn't invoke directly.        |
| `allowed-tools`            | Tools Claude can use without asking permission when this skill is active. Example: `Read, Grep, Glob`.                  |
| `model`                    | Model to use when this skill is active.                                                                                 |
| `context`                  | Set to `fork` to run in a forked subagent context.                                                                      |
| `agent`                    | Which subagent type to use when `context: fork` is set. Options: `Explore`, `Plan`, `general-purpose`, or custom agent. |
| `hooks`                    | Hooks scoped to this skill's lifecycle.                                                                                 |

Note: `name` defaults to the directory name if omitted. Lowercase letters, numbers, hyphens only (max 64 chars).

## Invocation Control

`disable-model-invocation` and `user-invocable` control who can trigger a skill:

| Frontmatter                      | User can invoke | Claude can invoke | When loaded into context                                     |
| :------------------------------- | :-------------- | :---------------- | :----------------------------------------------------------- |
| (default)                        | Yes             | Yes               | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes             | No                | Description not in context, full skill loads when user invokes |
| `user-invocable: false`          | No              | Yes               | Description always in context, full skill loads when invoked |

Use `disable-model-invocation: true` for workflows with side effects (deploys, commits, sending messages). Use `user-invocable: false` for background knowledge that isn't actionable as a command.

## Arguments and String Substitutions

Skills support these placeholders in the markdown body:

| Variable               | Description                                                            |
| :--------------------- | :--------------------------------------------------------------------- |
| `$ARGUMENTS`           | All arguments passed when invoking. If absent, arguments are appended. |
| `$ARGUMENTS[N]`        | Specific argument by 0-based index (e.g., `$ARGUMENTS[0]`).           |
| `$N`                   | Shorthand for `$ARGUMENTS[N]` (e.g., `$0`, `$1`).                     |
| `${CLAUDE_SESSION_ID}` | Current session ID. Useful for logging or session-specific files.      |

Example with positional arguments:

```yaml
---
name: migrate-component
description: Migrate a component from one framework to another
---

Migrate the $0 component from $1 to $2.
Preserve all existing behavior and tests.
```

Running `/migrate-component SearchBar React Vue` replaces `$0` with `SearchBar`, `$1` with `React`, `$2` with `Vue`.

## Dynamic Context Injection

The `` !`command` `` syntax runs shell commands before the skill content is sent to Claude. The command output replaces the placeholder.

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

Each `` !`command` `` executes immediately (before Claude sees anything). Claude only receives the final rendered content with actual data.

Include the word "ultrathink" anywhere in skill content to enable extended thinking.

## Subagent Execution

Add `context: fork` to run a skill in an isolated subagent. The skill content becomes the prompt that drives the subagent — it won't have access to conversation history.

`context: fork` only makes sense for skills with explicit task instructions. Guidelines-only skills (e.g., "use these API conventions") won't produce meaningful output in a subagent since there's no actionable prompt.

The `agent` field specifies which subagent configuration to use: built-in agents (`Explore`, `Plan`, `general-purpose`) or any custom subagent from `.claude/agents/`. Defaults to `general-purpose`.

### Skills vs Subagents

| Approach                     | System prompt                             | Task                        | Also loads                   |
| :--------------------------- | :---------------------------------------- | :-------------------------- | :--------------------------- |
| Skill with `context: fork`   | From agent type (`Explore`, `Plan`, etc.) | SKILL.md content            | CLAUDE.md                    |
| Subagent with `skills` field | Subagent's markdown body                  | Claude's delegation message | Preloaded skills + CLAUDE.md |

## Restrict Tool Access

Use `allowed-tools` to limit which tools Claude can use when a skill is active. This creates scoped permissions — for example, a read-only exploration skill:

```yaml
---
name: safe-reader
description: Read files without making changes
allowed-tools: Read, Grep, Glob
---
```

Tool-specific patterns are also supported:

```yaml
allowed-tools: Bash(gh *), Bash(python *)
```

## Visual Output Pattern

Skills can bundle scripts that generate interactive HTML files opened in the browser. The pattern: a bundled script does the heavy lifting, Claude handles orchestration.

````yaml
---
name: codebase-visualizer
description: Generate an interactive tree visualization of the codebase.
allowed-tools: Bash(python *)
---

# Codebase Visualizer

Run the visualization script from the project root:

```bash
python ~/.claude/skills/codebase-visualizer/scripts/visualize.py .
```
````

The bundled `scripts/visualize.py` generates a self-contained HTML file and opens it in the browser. This pattern works for dependency graphs, test coverage reports, API documentation, or database schema visualizations.

## Skill Location and Discovery

### Location Hierarchy

Where a skill is stored determines scope and priority:

| Location   | Path                                     | Applies to                     |
| :--------- | :--------------------------------------- | :----------------------------- |
| Enterprise | Managed settings                         | All users in your organization |
| Personal   | `~/.claude/skills/<name>/SKILL.md`       | All your projects              |
| Project    | `.claude/skills/<name>/SKILL.md`         | This project only              |
| Plugin     | `<plugin>/skills/<name>/SKILL.md`        | Where plugin is enabled        |

Priority: enterprise > personal > project. Plugin skills use `plugin-name:skill-name` namespace and cannot conflict with other levels.

### Nested Discovery

Claude Code discovers skills from nested `.claude/skills/` directories. Editing a file in `packages/frontend/` also searches `packages/frontend/.claude/skills/`. This supports monorepo setups.

### Additional Directories

Skills in `.claude/skills/` within `--add-dir` directories are loaded automatically with live change detection — editable during a session without restart.

### Commands Backward Compatibility

Files in `.claude/commands/` still work and support the same frontmatter. If a skill and command share the same name, the skill takes precedence. Skills are recommended since they support supporting files.

## Permission Control

Three ways to control which skills Claude can invoke:

**Disable all skills** by denying the Skill tool in `/permissions`:

```text
Skill
```

**Allow or deny specific skills** using permission rules:

```text
Skill(commit)          # Allow exact match
Skill(review-pr *)     # Allow prefix match with any arguments
Skill(deploy *)        # Deny prefix match
```

**Hide individual skills** with `disable-model-invocation: true` in frontmatter — removes the skill from Claude's context entirely.

### Character Budget

Skill descriptions are loaded into context so Claude knows what's available. Many skills may exceed the character budget (2% of context window, fallback 16,000 chars). Run `/context` to check for excluded skills. Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var.

## Types of Skill Content

### Reference Content

Adds knowledge Claude applies to current work (conventions, patterns, style guides). Runs inline alongside conversation context.

```yaml
---
name: api-conventions
description: API design patterns for this codebase
---

When writing API endpoints:
- Use RESTful naming conventions
- Return consistent error formats
- Include request validation
```

### Task Content

Step-by-step instructions for a specific action. Often paired with `disable-model-invocation: true` for manual-only invocation.

```yaml
---
name: deploy
description: Deploy the application to production
context: fork
disable-model-invocation: true
---

Deploy the application:
1. Run the test suite
2. Build the application
3. Push to the deployment target
```

## Plugin-Specific Guidance

### Plugin Skill Directory Structure

Plugin skills live in the plugin's `skills/` directory, not `.claude/skills/`:

```text
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── agents/
└── skills/
    └── my-skill/
        ├── SKILL.md
        ├── references/
        └── scripts/
```

### Auto-Discovery

Claude Code automatically discovers plugin skills:

- Scans `skills/` directory for subdirectories containing `SKILL.md`
- Loads skill metadata (name + description) always
- Loads SKILL.md body when skill triggers
- Loads references when needed
- No need to register skills in plugin.json

### No Packaging Needed

Plugin skills are distributed as part of the plugin. Users get skills when they install the plugin. Do not use `package_skill.py` for plugin skills.

### Testing Plugin Skills

```bash
cc --plugin-dir /path/to/plugin
# Then ask questions that should trigger the skill
```

### Plugin-Dev Skills as Study Examples

The `plugin-dev` plugin's own skills demonstrate best practices for plugin skill development:

- **hook-development**: Lean SKILL.md (~1,650 words), 3 reference files, 3 example files, 3 utility scripts. Strong trigger phrases.
- **agent-development**: Focused SKILL.md (~1,440 words). References include the AI generation prompt from Claude Code.
- **plugin-settings**: Specific triggers ("plugin settings", ".local.md files"). References show real implementations with working parsing scripts.

## Writing Style Guide

### Imperative/Infinitive Form

Write skill instructions using verb-first form, not second person:

**Correct (imperative):**

```text
To create a hook, define the event type.
Configure the MCP server with authentication.
Validate settings before use.
Parse the frontmatter using sed.
Start by reading the configuration file.
```

**Incorrect (second person):**

```text
You should create a hook by defining the event type.
You need to configure the MCP server.
You must validate settings before use.
You can parse the frontmatter...
Claude should extract fields...
```

### Third-Person in Description

The frontmatter description must use third person with specific trigger phrases:

**Good:**

```yaml
description: This skill should be used when the user asks to "create a hook",
  "add a PreToolUse hook", "validate tool use", or mentions hook events
  (PreToolUse, PostToolUse, Stop). Provides comprehensive hooks API guidance.
```

**Bad:**

```yaml
description: Provides guidance for working with hooks.
# Vague, no trigger phrases, not third person

description: Use this skill when you want to create X...
# Wrong person

description: Load this skill when user asks...
# Not third person
```

### Objective, Instructional Language

Focus on what to do, not who should do it:

**Correct:**

```text
Parse the frontmatter using sed.
Extract fields with grep.
Validate values before use.
```

**Incorrect:**

```text
You can parse the frontmatter...
Claude should extract fields...
The user might validate values...
```

## Validation Checklist

Before finalizing a skill:

**Structure:**

- [ ] SKILL.md file exists with valid YAML frontmatter
- [ ] Frontmatter has `name` and `description` fields
- [ ] Markdown body is present and substantial
- [ ] Referenced files actually exist

**Description Quality:**

- [ ] Uses third person ("This skill should be used when...")
- [ ] Includes specific trigger phrases users would say
- [ ] Lists concrete scenarios ("create X", "configure Y")
- [ ] Not vague or generic

**Content Quality:**

- [ ] SKILL.md body uses imperative/infinitive form (see Writing Style Guide above)
- [ ] Ideal body length is 1,500-2,000 words (supplementary to skill-creator's <500 lines guidance)
- [ ] Examples are complete and working
- [ ] Scripts are executable and documented
- [ ] No duplicated information between SKILL.md and references files

**Large Reference Files:**

- [ ] Files >10k words include grep search patterns in SKILL.md so Claude can find specific sections without loading the whole file

**Testing:**

- [ ] Skill triggers on expected user queries
- [ ] Content is helpful for intended tasks
- [ ] References load when needed

## Common Mistakes

### Weak Trigger Description

**Bad:**

```yaml
description: Provides guidance for working with hooks.
```

Why: Vague, no specific trigger phrases, not third person.

**Good:**

```yaml
description: This skill should be used when the user asks to "create a hook",
  "add a PreToolUse hook", "validate tool use", or mentions hook events. Provides
  comprehensive hooks API guidance.
```

Why: Third person, specific phrases, concrete scenarios.

### Information Duplication Across Files

Information should live in either SKILL.md or references files, not both. Duplicating content wastes context and creates drift when one copy is updated but not the other. Keep only essential procedural instructions in SKILL.md; move detailed reference material, schemas, and examples to references files.

## Troubleshooting

### Skill Not Triggering

1. Check the description includes keywords users would naturally say
2. Verify the skill appears in "What skills are available?"
3. Try rephrasing the request to match the description more closely
4. Invoke directly with `/skill-name` to verify it works at all
5. Simple one-step queries may not trigger skills — Claude handles them directly. Skills trigger reliably on complex, multi-step, or specialized queries.

### Skill Triggers Too Often

1. Make the description more specific
2. Add `disable-model-invocation: true` for manual-only invocation

### Claude Doesn't See All Skills

Many skills may exceed the character budget. Run `/context` to check for excluded skills. Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var.
