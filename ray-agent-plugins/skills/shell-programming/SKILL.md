---
name: shell-programming
description: This skill should be used when the user asks to "write a shell script", "create a bash script", "fix a shell script", "review shell code", "write a bash function", "test shell code", "run shellcheck", "lint bash code", or when implementing any shell/bash code, writing bats tests, or debugging shell syntax issues. Make sure to use this skill whenever the user is working with .sh files, shell hooks, or any bash-related task, even if they don't explicitly mention "shell programming". Provides shell scripting best practices based on Google Shell Style Guide with Bats testing and ShellCheck linting.
---

# Shell Programming

Apply [references/shell-style-guide.md](references/shell-style-guide.md) for all formatting, naming, syntax, and documentation rules.

## Portability

Target bash 3.2 (macOS default). Avoid bash 4+ features:

| Bash 4+ feature | Bash 3.2 alternative |
|---|---|
| `${var,,}` / `${var^^}` | `tr '[:upper:]' '[:lower:]'` / `tr '[:lower:]' '[:upper:]'` |
| `declare -A` (associative arrays) | Separate indexed arrays or temp files |
| `readarray` / `mapfile` | `while IFS= read -r` loop |
| `&>` redirection | `> file 2>&1` |

## Development Workflow

1. **Design** — Define inputs, outputs, exit codes, and dependencies.
2. **Write** — Follow the script structure and style guide.
3. **Lint** — `shellcheck script.sh`
4. **Test** — `bats script.test.bats`
5. **Iterate** — Fix issues, re-lint, re-test until clean.

Requires `shellcheck` and `bats` installed. If either is missing, offer to install via Homebrew (ask user for confirmation first).

## Script Structure

### Executable Script

Key conventions — header, `set -euo pipefail`, functions, `main`, source guard:

```bash
#!/bin/bash
#
# Brief description of what this script does.

set -euo pipefail

readonly MY_CONSTANT="value"

do_work() {
  local input="$1"
  # ...
}

main() {
  # argument parsing, validation, orchestration
  do_work "$1"
}

# Guard allows bats tests to source functions without executing main
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
```

### Library File

Libraries use `.sh` extension, are not executable, and have no shebang or `main`. Use `::` namespace separator:

```bash
# Brief description. Source this file; do not execute directly.

mylib::validate() {
  local input="$1"
  # ...
}
```

## Project Patterns

Use shell parameter expansion for template substitution instead of `sed` (avoids escaping issues with `/`, `&`, `\`):

```bash
content="${template//\{\{PLACEHOLDER\}\}/${value}}"
```

## Testing with Bats

Co-locate test files: `script.sh` paired with `script.test.bats`. The source guard allows bats to source functions without executing `main`.

```bash
#!/usr/bin/env bats

setup() {
  source "${BATS_TEST_DIRNAME}/script.sh"
}

@test "do_work handles normal input" {
  run do_work "valid-input"
  [[ "${status}" -eq 0 ]]
  [[ "${output}" == *"expected"* ]]
}

@test "do_work rejects empty input" {
  run do_work ""
  [[ "${status}" -eq 1 ]]
  [[ "${output}" == *"Error"* ]]
}
```

Use `run` to capture exit code and output without failing the test on non-zero exit. Use `setup` / `teardown` for shared fixtures.
