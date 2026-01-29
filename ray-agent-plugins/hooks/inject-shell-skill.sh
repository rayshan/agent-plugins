#!/bin/bash
# Instructs Claude to load shell-programming skill when writing/editing shell scripts.
#
# Detects shell scripts by:
# - File extensions: .sh, .bash, .zsh, .ksh, .bats
# - Shebang patterns: #!/bin/bash, #!/usr/bin/env bash, etc.
#
# Outputs instructions for Claude to use the Skill tool.

set -euo pipefail

readonly SHELL_EXTENSIONS="sh|bash|zsh|ksh|bats"
readonly SHEBANG_PATTERN="^#!.*/(bash|sh|zsh|ksh|fish)|^#!/usr/bin/env[[:space:]]+(bash|sh|zsh|ksh|fish)"

main() {
  local input
  input=$(cat)

  local tool_name
  tool_name=$(printf '%s' "$input" | jq -r '.tool_name // ""')

  if [[ "$tool_name" != "Write" && "$tool_name" != "Edit" ]]; then
    exit 0
  fi

  local file_path
  file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')

  if [[ -z "$file_path" ]]; then
    exit 0
  fi

  local is_shell_script=false

  # Check file extension
  if [[ "$file_path" =~ \.($SHELL_EXTENSIONS)$ ]]; then
    is_shell_script=true
  fi

  # For Write tool, also check shebang in content
  if [[ "$is_shell_script" == "false" && "$tool_name" == "Write" ]]; then
    local content
    content=$(printf '%s' "$input" | jq -r '.tool_input.content // ""')

    if [[ -n "$content" ]]; then
      local first_line
      first_line=$(printf '%s' "$content" | head -n 1)

      if [[ "$first_line" =~ $SHEBANG_PATTERN ]]; then
        is_shell_script=true
      fi
    fi
  fi

  if [[ "$is_shell_script" == "false" ]]; then
    exit 0
  fi

  local filename
  filename=$(basename "$file_path")

  cat <<EOF
SHELL SCRIPT DETECTED: ${filename}

Before proceeding with this shell script operation, ensure the "shell-programming" skill is active.

IF you have NOT already loaded the "shell-programming" skill in this session:
→ Use Skill() tool to load it NOW

THEN proceed with the ${tool_name} operation.
EOF
}

main "$@"
