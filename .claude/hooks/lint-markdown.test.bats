#!/usr/bin/env bats

setup() {
  source "${BATS_TEST_DIRNAME}/lint-markdown.sh" 2>/dev/null || true
  TEST_DIR=$(mktemp -d)
}

teardown() {
  rm -rf "$TEST_DIR"
}

# Helper: run main() with JSON input via stdin
run_hook() {
  printf '%s' "$1" | bash "${BATS_TEST_DIRNAME}/lint-markdown.sh"
}

@test "skips non-Write/Edit tools" {
  run run_hook '{"tool_name": "Read", "tool_input": {"file_path": "/tmp/test.md"}}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "skips non-markdown files" {
  run run_hook '{"tool_name": "Write", "tool_input": {"file_path": "/tmp/test.sh"}}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "skips empty file_path" {
  run run_hook '{"tool_name": "Write", "tool_input": {"file_path": ""}}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "skips missing file_path field" {
  run run_hook '{"tool_name": "Edit", "tool_input": {}}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "skips nonexistent file" {
  run run_hook '{"tool_name": "Write", "tool_input": {"file_path": "/tmp/nonexistent-lint-test.md"}}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "passes clean markdown file" {
  local md_file="${TEST_DIR}/clean.md"
  printf '# Clean File\n\nThis is valid markdown.\n' > "$md_file"

  run run_hook "{\"tool_name\": \"Write\", \"tool_input\": {\"file_path\": \"${md_file}\"}}"
  [ "$status" -eq 0 ]
}

@test "auto-formats markdown with fixable issues" {
  # rumdl must be installed for this test
  if ! command -v rumdl &>/dev/null; then
    skip "rumdl not installed"
  fi

  local md_file="${TEST_DIR}/fixable.md"
  # Missing trailing newline (MD047) is auto-fixable
  printf '# Test\n\nSome text' > "$md_file"

  run run_hook "{\"tool_name\": \"Edit\", \"tool_input\": {\"file_path\": \"${md_file}\"}}"
  [ "$status" -eq 0 ]

  # Verify file was actually formatted (trailing newline added)
  local last_char
  last_char=$(tail -c 1 "$md_file" | xxd -p)
  [ "$last_char" = "0a" ]
}

@test "handles Write tool" {
  local md_file="${TEST_DIR}/write-test.md"
  printf '# Write Test\n\nContent here.\n' > "$md_file"

  run run_hook "{\"tool_name\": \"Write\", \"tool_input\": {\"file_path\": \"${md_file}\"}}"
  [ "$status" -eq 0 ]
}

@test "handles Edit tool" {
  local md_file="${TEST_DIR}/edit-test.md"
  printf '# Edit Test\n\nContent here.\n' > "$md_file"

  run run_hook "{\"tool_name\": \"Edit\", \"tool_input\": {\"file_path\": \"${md_file}\"}}"
  [ "$status" -eq 0 ]
}
