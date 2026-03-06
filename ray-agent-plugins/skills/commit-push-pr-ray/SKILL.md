---
name: commit-push-pr-ray
description: This skill should be used when the user asks to "commit and push",
  "create a PR", "open a pull request", "push and create PR", "submit a PR",
  "commit push and PR", or wants to commit, push, and open a pull request with
  structured PR content including executive summary, change summary, and test
  coverage delta.
disable-model-invocation: true
---

# Commit, Push, and Open a PR

First, invoke the `commit-commands:commit-push-pr` skill with the Skill() tool to establish the base git and GitHub CLI workflow. The instructions below supplement and override the base skill where they conflict.

## Guardrails

- NEVER commit, push, or create a PR without explicit user permission at each step.
- If the user has not specified whether to push to an existing branch and update an existing PR, or push to a new branch and create a new PR, ask before proceeding. Never edit an existing PR without permission.

## PR Message Workflow

Before submitting the PR, always draft the full PR message and present it for user review. Do not create the PR until the user approves the message.

### PR Content Template

Structure the PR body with these sections:

1. **Exec Summary** — A succinct summary of the business and technical impact, and why. Position for an audience that is non-technical. If user provided you their company info, tailor to user's company's internal audience.
2. **Summary of Changes** — A list of all changes. Prioritize by business impact and scope (e.g., if the PR ships a major feature and fixes a minor bug, lead with the feature). Do not simply list commits or files changed — the reader can get that from GitHub natively. Synthesize the changes into meaningful descriptions.
3. **Test Coverage Delta** — What test coverage changed: new tests added, tests modified, coverage increase/decrease.
4. **Related Work** — Description of related work done, if any (e.g., documentation updates, config changes, migrations).
5. **Referenced Implementations** — Other implementations referenced or consulted, if any (e.g., upstream libraries, design docs, RFCs).
6. **Other** — Any other material information (breaking changes, deployment notes, rollback plan, etc.). Omit this section if empty.

Omit sections 4-6 if they have no content. Do not include empty sections.

## Addressing PR Feedback

When addressing PR review feedback, take a critical eye. Reassess the whole issue independently — do not accept recommendations as-is without evaluating whether they are the best solution in context.
