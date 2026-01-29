#!/usr/bin/env bats
# Tests for inject-shell-skill.sh hook

setup() {
  export CLAUDE_PLUGIN_ROOT="${BATS_TEST_DIRNAME}/.."
}

@test "detects .sh extension on Write" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.sh","content":"echo hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -n "$output" ]]
  [[ "$output" == *"SHELL SCRIPT DETECTED"* ]]
}

@test "detects .bash extension on Write" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/script.bash","content":"echo hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -n "$output" ]]
  [[ "$output" == *"SHELL SCRIPT DETECTED"* ]]
}

@test "detects .zsh extension on Edit" {
  local input='{"tool_name":"Edit","tool_input":{"file_path":"/tmp/script.zsh","old_string":"x","new_string":"y"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -n "$output" ]]
  [[ "$output" == *"SHELL SCRIPT DETECTED"* ]]
}

@test "detects .ksh extension" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/script.ksh","content":"echo hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -n "$output" ]]
}

@test "detects .bats extension" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.bats","content":"@test \"x\" { true; }"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -n "$output" ]]
}

@test "detects bash shebang in Write content" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/myscript","content":"#!/bin/bash\necho hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -n "$output" ]]
  [[ "$output" == *"SHELL SCRIPT DETECTED"* ]]
}

@test "detects env bash shebang" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/myscript","content":"#!/usr/bin/env bash\necho hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -n "$output" ]]
}

@test "detects zsh shebang" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/myscript","content":"#!/bin/zsh\necho hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -n "$output" ]]
}

@test "detects sh shebang" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/myscript","content":"#!/bin/sh\necho hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -n "$output" ]]
}

@test "ignores non-shell file extensions" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.py","content":"print(1)"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -z "$output" ]]
}

@test "ignores non-shell content without extension" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/myscript","content":"console.log(1)"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -z "$output" ]]
}

@test "ignores Read tool" {
  local input='{"tool_name":"Read","tool_input":{"file_path":"/tmp/test.sh"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -z "$output" ]]
}

@test "ignores Bash tool" {
  local input='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -z "$output" ]]
}

@test "handles missing file_path gracefully" {
  local input='{"tool_name":"Write","tool_input":{"content":"echo hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ -z "$output" ]]
}

@test "output contains Skill tool instruction" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.sh","content":"echo hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ "$output" == *"Skill('ray-agent-plugins:shell-programming')"* ]]
}

@test "output contains filename" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/my-script.sh","content":"echo hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ "$output" == *"my-script.sh"* ]]
}

@test "output mentions tool name for Write" {
  local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.sh","content":"echo hello"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ "$output" == *"Write"* ]]
}

@test "output mentions tool name for Edit" {
  local input='{"tool_name":"Edit","tool_input":{"file_path":"/tmp/test.sh","old_string":"x","new_string":"y"}}'
  local output
  output=$(echo "$input" | bash "${BATS_TEST_DIRNAME}/inject-shell-skill.sh")

  [[ "$output" == *"Edit"* ]]
}
