---
name: shell-programming
description: This skill should be used when the user asks to "write a shell script", "create a bash script", "fix a shell script", "review shell code", "write a bash function", or when implementing any shell/bash code. Provides shell scripting best practices based on Google Shell Style Guide.
---

# Shell Programming

Follow [shell-style-guide.md](shell-style-guide.md) for all formatting, naming, syntax, and documentation rules.

## Testing

Requires `shellcheck` and `bats` installed. If not available, offer to install via Homebrew (ask user for confirmation first).

Run static analysis and tests:
```bash
shellcheck script.sh
bats script.test.bats
```
