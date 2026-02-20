---
name: get-markdown
description: This skill should be used when the user provides a URL to fetch web content. Automatically converts URLs to their raw markdown versions to reduce context window usage and eliminate HTML noise. Handles URLs from GitHub, Claude/Anthropic docs, Gemini CLI docs, Firebase docs, Google dev docs, OpenAI docs via rules, and any other URL via Tabstack extraction.
---

Fetch the markdown version of a URL to save context and reduce noise.

## Usage

Run the script via Bash, passing the URL as the argument:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/get-markdown/scripts/get-markdown.sh" "$ARGUMENTS"
```

Present the script's stdout output to the user. On non-zero exit, display the stderr message prominently.

## How It Works

The script applies the following logic in order:

1. **Binary files**: Rejects URLs pointing to non-text files (images, videos, archives, etc.).
2. **Known URL patterns**: Transforms documentation site URLs to their raw markdown equivalents and fetches via `curl`.
3. **Plain text files**: Fetches URLs with text file extensions directly — no transformation needed.
4. **Tabstack fallback**: Extracts markdown from all other URLs via the Tabstack API.

Pattern matching runs before the plain text extension check so that URLs like GitHub blob paths (which have text extensions but return HTML) are handled correctly. If a transformed URL returns HTML instead of markdown, the script automatically falls through to Tabstack.

## Dependencies

- `curl` — HTTP requests
- `jq` — JSON parsing (Tabstack fallback)
- `op` — 1Password CLI (Tabstack API key retrieval)
