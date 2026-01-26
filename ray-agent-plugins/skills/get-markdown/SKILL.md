---
name: get-markdown
description: This skill should be used when the user provides a URL to fetch documentation or web content. Automatically converts URLs to their raw markdown versions to reduce context window usage and eliminate HTML noise. Use when given URLs from GitHub, Claude/Anthropic docs, Gemini CLI docs, Firebase docs, Google dev docs, or OpenAI docs.
---

Fetch the markdown version of a URL to save context and reduce noise.

## Process

1. Identify the URL pattern from the table below
2. Transform to the markdown URL
3. Fetch using WebFetch
4. Warn if content is a 404 page or cannot be read

## URL Transformation Rules

| Source | Pattern | Transformation | Example |
|--------|---------|----------------|---------|
| **GitHub** | `github.com/{owner}/{repo}/blob/{branch}/{path}` (text files: .md, .txt, .json, .adoc, .rst, etc.) | `raw.githubusercontent.com/{owner}/{repo}/refs/heads/{branch}/{path}` | `github.com/google-gemini/gemini-cli/blob/main/docs/cli/headless.md` → `raw.githubusercontent.com/google-gemini/gemini-cli/refs/heads/main/docs/cli/headless.md` |
| **Claude Code docs** | `code.claude.com/docs/en/{page}` or `code.claude.com/docs/en/{page}#{anchor}` | `code.claude.com/docs/en/{page}.md` (strip anchor) | `code.claude.com/docs/en/skills#pass-arguments-to-skills` → `code.claude.com/docs/en/skills.md` |
| **Anthropic API docs** | `platform.claude.com/docs/en/{path}` | `platform.claude.com/docs/en/{path}.md` | `platform.claude.com/docs/en/api/overview` → `platform.claude.com/docs/en/api/overview.md` |
| **Gemini CLI docs** | `geminicli.com/docs/{path}` | First convert to `github.com/google-gemini/gemini-cli/blob/main/docs/{path}.md`, then apply GitHub rule | `geminicli.com/docs/cli/headless/` → `raw.githubusercontent.com/google-gemini/gemini-cli/refs/heads/main/docs/cli/headless.md` |
| **Firebase docs** | `firebase.google.com/docs/{path}` | `firebase.google.com/docs/{path}.md.txt` | `firebase.google.com/docs/ai-logic` → `firebase.google.com/docs/ai-logic.md.txt` |
| **Google dev docs** | `ai.google.dev/{path}` | `ai.google.dev/{path}.md.txt` | `ai.google.dev/gemini-api/docs` → `ai.google.dev/gemini-api/docs.md.txt` |
| **OpenAI docs** | `platform.openai.com/docs/{path}` | `platform.openai.com/docs/{path}.md` | `platform.openai.com/docs/guides/prompt-engineering` → `platform.openai.com/docs/guides/prompt-engineering.md` |

## Edge Cases

- **Trailing slashes**: Strip before transformation (e.g., `geminicli.com/docs/cli/headless/` → `headless`)
- **URL anchors**: Strip `#anchor` fragments before adding `.md` extension
- **Query parameters**: Strip `?params` before transformation
- **Unknown patterns**: If URL does not match any pattern, fetch as-is with WebFetch and inform user that no markdown conversion was available

## Error Handling

After fetching, check for:

1. **404 responses**: Warn "The markdown URL returned a 404. The page may not exist or the URL pattern may have changed."
2. **Empty content**: Warn "The markdown URL returned empty content."
3. **HTML instead of markdown**: If response contains `<!DOCTYPE` or `<html`, warn "The URL returned HTML instead of markdown. The transformation pattern may be incorrect."

## Output

After successful fetch, present the content to the user. If there were warnings, display them prominently before the content.
