#!/usr/bin/env bats

SCRIPT="$(cd "$(dirname "$BATS_TEST_FILENAME")" && pwd)/validate-filename.sh"

# ---------------------------------------------------------------------------
# Passing cases
# ---------------------------------------------------------------------------

@test "valid filename with extension passes" {
  run bash "$SCRIPT" "valid-filename.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS"* ]]
}

@test "valid filename without extension passes" {
  run bash "$SCRIPT" "readme"
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS"* ]]
}

@test "valid filename with underscores and digits passes" {
  run bash "$SCRIPT" "my_file_v2.md"
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS"* ]]
}

@test "stem at exactly 200 characters passes" {
  local name
  name="$(printf 'a%.0s' $(seq 1 200)).txt"
  run bash "$SCRIPT" "$name"
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS"* ]]
}

@test "single-character stem passes" {
  run bash "$SCRIPT" "a.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS"* ]]
}

# ---------------------------------------------------------------------------
# Rule 1: Safe characters
# ---------------------------------------------------------------------------

@test "FAIL: space in stem" {
  run bash "$SCRIPT" "has spaces.txt"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Safe characters"* ]]
}

@test "FAIL: special characters in stem" {
  run bash "$SCRIPT" "file@name!.txt"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Safe characters"* ]]
}

@test "FAIL: parentheses in stem" {
  run bash "$SCRIPT" "report (final).pdf"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Safe characters"* ]]
}

@test "FAIL: dot in stem (compound extension)" {
  run bash "$SCRIPT" "archive.tar.gz"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Safe characters"* ]]
}

# ---------------------------------------------------------------------------
# Rule 2: Reserved names
# ---------------------------------------------------------------------------

@test "FAIL: CON is reserved" {
  run bash "$SCRIPT" "con.txt"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Reserved name"* ]]
}

@test "FAIL: PRN is reserved" {
  run bash "$SCRIPT" "prn.doc"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Reserved name"* ]]
}

@test "FAIL: NUL without extension is reserved" {
  run bash "$SCRIPT" "nul"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Reserved name"* ]]
}

@test "FAIL: COM1 is reserved" {
  run bash "$SCRIPT" "com1.txt"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Reserved name"* ]]
}

@test "FAIL: LPT3 is reserved" {
  run bash "$SCRIPT" "lpt3.csv"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Reserved name"* ]]
}

@test "FAIL: AUX reserved (case-insensitive)" {
  run bash "$SCRIPT" "AUX.log"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Reserved name"* ]]
}

@test "PASS: prefix matching reserved name is allowed" {
  run bash "$SCRIPT" "console.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS"* ]]
}

# ---------------------------------------------------------------------------
# Rule 3: Clean ends
# ---------------------------------------------------------------------------

@test "FAIL: starts with period" {
  run bash "$SCRIPT" ".hidden"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Clean ends"* ]]
}

@test "FAIL: ends with period" {
  run bash "$SCRIPT" "trailing."
  [ "$status" -eq 1 ]
  [[ "$output" == *"Clean ends"* ]]
}

@test "FAIL: starts with space" {
  run bash "$SCRIPT" " leading.txt"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Clean ends"* ]]
}

# ---------------------------------------------------------------------------
# Rule 4: Lowercase
# ---------------------------------------------------------------------------

@test "FAIL: uppercase in stem" {
  run bash "$SCRIPT" "MyFile.txt"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Lowercase"* ]]
}

@test "FAIL: all uppercase stem" {
  run bash "$SCRIPT" "README.md"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Lowercase"* ]]
}

@test "FAIL: uppercase in extension" {
  run bash "$SCRIPT" "readme.MD"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Lowercase"* ]]
}

# ---------------------------------------------------------------------------
# Rule 5: Length limit
# ---------------------------------------------------------------------------

@test "FAIL: stem exceeds 200 characters" {
  local name
  name="$(printf 'a%.0s' $(seq 1 201)).txt"
  run bash "$SCRIPT" "$name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Length"* ]]
}

# ---------------------------------------------------------------------------
# Rule 6: Unicode warning
# ---------------------------------------------------------------------------

@test "WARN: CJK characters in filename" {
  run bash "$SCRIPT" "文件.txt"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Unicode"* ]]
}

@test "WARN: accented characters in filename" {
  run bash "$SCRIPT" "café.txt"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Unicode"* ]]
}

# ---------------------------------------------------------------------------
# Multiple files
# ---------------------------------------------------------------------------

@test "multiple valid files all pass" {
  run bash "$SCRIPT" "file-a.txt" "file-b.md"
  [ "$status" -eq 0 ]
}

@test "one invalid among multiple files causes failure" {
  run bash "$SCRIPT" "valid.txt" "INVALID.txt"
  [ "$status" -eq 1 ]
}

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

@test "no arguments prints usage and exits 2" {
  run bash "$SCRIPT"
  [ "$status" -eq 2 ]
  [[ "$output" == *"Usage"* ]]
}
