#!/bin/bash
set -euo pipefail

# Block dangerous bash commands and suggest safer alternatives.
# Blocks: rm (any), sudo, chmod 777
#
# Globals:
#   None
# Arguments:
#   None (reads JSON from stdin)
# Outputs:
#   JSON decision to stdout: {"decision": "approve"|"block", "reason": "..."}

# Check if command contains rm (any form).
# Arguments:
#   $1 - command string to check
# Returns:
#   0 if rm found (should block), 1 otherwise
check_rm_command() {
  local command="$1"
  local normalized_cmd
  normalized_cmd=$(echo "$command" | tr -s ' ')

  # Match: rm, /bin/rm, /usr/bin/rm, also after command separators (;&|)
  if [[ "$normalized_cmd" =~ ^rm[[:space:]] ]] \
      || [[ "$normalized_cmd" == "rm" ]] \
      || [[ "$normalized_cmd" =~ (^|[;\&\|][[:space:]]*)(/[^[:space:]]*/)?rm[[:space:]] ]]; then
    return 0
  fi
  return 1
}

# Check if command contains sudo.
# Arguments:
#   $1 - command string to check
# Returns:
#   0 if sudo found (should block), 1 otherwise
check_sudo_command() {
  local command="$1"
  if [[ "$command" =~ (^|[;\&\|][[:space:]]*)sudo[[:space:]] ]]; then
    return 0
  fi
  return 1
}

# Check if command contains chmod 777.
# Arguments:
#   $1 - command string to check
# Returns:
#   0 if chmod 777 found (should block), 1 otherwise
check_chmod_777() {
  local command="$1"
  if [[ "$command" =~ chmod[[:space:]]+(-[^[:space:]]+[[:space:]]+)*777 ]]; then
    return 0
  fi
  return 1
}

# Generate block reason for rm.
# Outputs:
#   Reason text to stdout
get_rm_reason() {
  cat << 'EOF'
rm command blocked. Instead:
- MOVE files to a TRASH/ folder in the current directory (create if needed)
- Log the action in TRASH-FILES.md with: filename, destination, reason

Example entry:
```
test_script.py - moved to TRASH/ - temporary test script
```
EOF
}

# Generate block reason for sudo.
# Outputs:
#   Reason text to stdout
get_sudo_reason() {
  cat << 'EOF'
sudo command blocked. Privilege escalation risk.
- Check if the operation can be done without elevated privileges
- If sudo is truly needed, ask user for explicit permission first
- Explain exactly what system changes will occur
EOF
}

# Generate block reason for chmod 777.
# Outputs:
#   Reason text to stdout
get_chmod_777_reason() {
  cat << 'EOF'
chmod 777 blocked. Insecure permissions risk.
Use minimal permissions instead:
- Directories: chmod 755 (rwxr-xr-x)
- Files: chmod 644 (rw-r--r-)
- Executables: chmod 755 (rwxr-xr-x)
EOF
}

# Escape string for JSON output.
# Arguments:
#   $1 - string to escape
# Outputs:
#   Escaped string to stdout
json_escape() {
  local str="$1"
  str="${str//\\/\\\\}"
  str="${str//\"/\\\"}"
  str="${str//$'\n'/\\n}"
  str="${str//$'\r'/\\r}"
  str="${str//$'\t'/\\t}"
  echo "$str"
}

# Main entry point.
# Reads JSON input from stdin and outputs decision JSON.
main() {
  local input
  input=$(cat)

  # Extract tool_name
  local tool_name
  tool_name=$(echo "$input" \
    | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' \
    | cut -d'"' -f4)

  # Only process Bash tool calls
  if [[ "$tool_name" != "Bash" ]]; then
    echo '{"decision": "approve"}'
    exit 0
  fi

  # Extract command
  local command
  command=$(echo "$input" \
    | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' \
    | cut -d'"' -f4)

  # Check for dangerous patterns
  local reason=""

  if check_rm_command "$command"; then
    reason=$(get_rm_reason)
  elif check_sudo_command "$command"; then
    reason=$(get_sudo_reason)
  elif check_chmod_777 "$command"; then
    reason=$(get_chmod_777_reason)
  fi

  if [[ -n "$reason" ]]; then
    local escaped_reason
    escaped_reason=$(json_escape "$reason")
    echo "{\"decision\": \"block\", \"reason\": \"$escaped_reason\"}"
  else
    echo '{"decision": "approve"}'
  fi

  exit 0
}

main "$@"
