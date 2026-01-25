#!/usr/bin/env bats

# Tests for block-dangerous-commands.sh hook

SCRIPT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")" && pwd)"
SCRIPT="$SCRIPT_DIR/block-dangerous-commands.sh"

# Helper to create JSON input
make_input() {
    local tool_name="$1"
    local command="$2"
    echo "{\"tool_name\": \"$tool_name\", \"tool_input\": {\"command\": \"$command\"}}"
}

# ============== BLOCK CASES ==============

@test "blocks basic rm command" {
    result=$(make_input "Bash" "rm file.txt" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
    [[ "$result" == *'TRASH'* ]]
}

@test "blocks rm -rf" {
    result=$(make_input "Bash" "rm -rf /tmp/test" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}

@test "blocks rm -fr (reversed flags)" {
    result=$(make_input "Bash" "rm -fr /tmp/test" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}

@test "blocks /bin/rm" {
    result=$(make_input "Bash" "/bin/rm file.txt" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}

@test "blocks /usr/bin/rm" {
    result=$(make_input "Bash" "/usr/bin/rm file.txt" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}

@test "blocks chained rm with &&" {
    result=$(make_input "Bash" "ls && rm file.txt" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}

@test "blocks chained rm with ;" {
    result=$(make_input "Bash" "ls; rm file.txt" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}

@test "blocks chained rm with |" {
    result=$(make_input "Bash" "echo test | rm file.txt" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}

@test "blocks sudo command" {
    result=$(make_input "Bash" "sudo apt install foo" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
    [[ "$result" == *'Privilege escalation'* ]]
}

@test "blocks chained sudo" {
    result=$(make_input "Bash" "ls && sudo reboot" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}

@test "blocks chmod 777" {
    result=$(make_input "Bash" "chmod 777 file.txt" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
    [[ "$result" == *'755'* ]]
}

@test "blocks chmod -R 777" {
    result=$(make_input "Bash" "chmod -R 777 /tmp" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}

# ============== APPROVE CASES ==============

@test "approves ls command" {
    result=$(make_input "Bash" "ls -la" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

@test "approves git rm (not bare rm)" {
    result=$(make_input "Bash" "git rm file.txt" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

@test "approves chmod 755" {
    result=$(make_input "Bash" "chmod 755 file.txt" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

@test "approves chmod 644" {
    result=$(make_input "Bash" "chmod 644 file.txt" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

@test "approves non-Bash tool" {
    result=$(make_input "Write" "/test/path" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

@test "approves Read tool" {
    result=$(make_input "Read" "/test/path" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

@test "approves npm commands" {
    result=$(make_input "Bash" "npm install express" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

@test "approves git commands" {
    result=$(make_input "Bash" "git status" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

# ============== EDGE CASES ==============

@test "handles empty command" {
    result=$(make_input "Bash" "" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

@test "handles command with special characters in path" {
    result=$(make_input "Bash" "ls /path/with spaces/file" | bash "$SCRIPT")
    [[ "$result" == '{"decision": "approve"}' ]]
}

@test "blocks rm even with extra spaces" {
    result=$(make_input "Bash" "rm    -rf    /tmp" | bash "$SCRIPT")
    [[ "$result" == *'"decision": "block"'* ]]
}
