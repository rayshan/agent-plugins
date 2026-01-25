---
description: Revise CLAUDE.md and README.md to reflect latest changes
allowed-tools: Read, Edit, Glob, Skill
---

Update project documentation to reflect the current state of the codebase.

## Step 1: Revise CLAUDE.md

Invoke the `/claude-md-management:revise-claude-md` skill using the Skill tool to capture session learnings and update CLAUDE.md files. Complete this step before proceeding.

## Step 2: Review README.md

After CLAUDE.md updates are complete, find all README.md files:

For each README.md, verify:
- **Relevance**: Content reflects the current project state
- **Accuracy**: Installation steps, usage examples, and descriptions are correct
- **No overlap with CLAUDE.md**: README is for humans (installation, usage, features); CLAUDE.md is for Claude (development patterns, commands, gotchas)

## Step 3: Propose README Changes

Show proposed changes in diff format:

```
### Update: ./README.md

**Why:** [one-line reason]

\`\`\`diff
- [removed content]
+ [added content]
\`\`\`
```

## Step 4: Apply with Approval

Present all proposed changes and request user approval before editing files.

## Guidelines

- Keep docs minimal - only material and critical information
- One line per concept where possible
- Remove outdated or redundant content
