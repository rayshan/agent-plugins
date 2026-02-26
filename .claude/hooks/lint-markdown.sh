#!/bin/bash
# Formats and lints markdown files after Write/Edit operations.
# Runs rumdl fmt (auto-fix) then rumdl check (lint) on the file.
#
# Globals:
#   None
# Arguments:
#   None (reads JSON from stdin)
# Outputs:
#   Stdout: status message if formatting was applied (exit 0, shown in transcript).
#   Stderr: lint errors for Claude to fix (exit 2, fed back to Claude).

set -euo pipefail

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

  # Only process markdown files
  if [[ "$file_path" != *.md ]]; then
    exit 0
  fi

  # Skip if rumdl is not installed
  if ! command -v rumdl &>/dev/null; then
    exit 0
  fi

  # Skip if file doesn't exist (e.g. failed Write)
  if [[ ! -f "$file_path" ]]; then
    exit 0
  fi

  local filename
  filename=$(basename "$file_path")

  # Format the file (auto-fix what's possible)
  local fmt_output
  fmt_output=$(rumdl fmt "$file_path" 2>&1) || true

  # Lint the file (catch remaining issues)
  local check_output
  local check_exit=0
  check_output=$(rumdl check "$file_path" 2>&1) || check_exit=$?

  # If unfixable lint issues remain, feed back to Claude
  if [[ "$check_exit" -ne 0 ]]; then
    {
      echo "rumdl: unfixable markdown lint issues in ${filename}:"
      echo "$check_output"
      echo ""
      echo "Fix these issues, then re-read the file before further edits (rumdl may have also auto-formatted it)."
    } >&2
    exit 2
  fi

  # If formatting was applied, notify Claude
  if [[ -n "$fmt_output" && "$fmt_output" == *"Fixed"* ]]; then
    echo "rumdl auto-formatted ${filename}. Re-read the file before further edits."
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
