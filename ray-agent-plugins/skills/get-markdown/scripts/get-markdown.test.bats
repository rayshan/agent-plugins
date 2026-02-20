#!/usr/bin/env bats
# Tests for get-markdown.sh
#
# Tests cover URL extension detection, binary/plaintext classification,
# and URL transformation logic. No live API calls are made.

setup() {
  source "${BATS_TEST_DIRNAME}/get-markdown.sh"
}

# -- get_path_extension --

@test "get_path_extension: extracts simple extension" {
  run get_path_extension "https://example.com/file.md"
  [[ "${output}" == "md" ]]
}

@test "get_path_extension: extracts multi-char extension" {
  run get_path_extension "https://example.com/file.json"
  [[ "${output}" == "json" ]]
}

@test "get_path_extension: ignores query params" {
  run get_path_extension "https://example.com/file.md?v=1&foo=bar"
  [[ "${output}" == "md" ]]
}

@test "get_path_extension: ignores anchors" {
  run get_path_extension "https://example.com/file.md#section"
  [[ "${output}" == "md" ]]
}

@test "get_path_extension: ignores both query params and anchors" {
  run get_path_extension "https://example.com/file.txt?v=1#top"
  [[ "${output}" == "txt" ]]
}

@test "get_path_extension: returns empty for no extension" {
  run get_path_extension "https://example.com/page"
  [[ "${output}" == "" ]]
}

@test "get_path_extension: strips trailing slash before check" {
  run get_path_extension "https://example.com/page/"
  [[ "${output}" == "" ]]
}

@test "get_path_extension: lowercases extension" {
  run get_path_extension "https://example.com/file.PDF"
  [[ "${output}" == "pdf" ]]
}

# -- is_binary_url --

@test "is_binary_url: detects pdf" {
  is_binary_url "https://example.com/doc.pdf"
}

@test "is_binary_url: detects png" {
  is_binary_url "https://example.com/image.png"
}

@test "is_binary_url: detects jpg" {
  is_binary_url "https://example.com/photo.jpg"
}

@test "is_binary_url: detects jpeg" {
  is_binary_url "https://example.com/photo.jpeg"
}

@test "is_binary_url: detects mp4" {
  is_binary_url "https://example.com/video.mp4"
}

@test "is_binary_url: detects doc" {
  is_binary_url "https://example.com/file.doc"
}

@test "is_binary_url: detects docx" {
  is_binary_url "https://example.com/file.docx"
}

@test "is_binary_url: detects xlsx" {
  is_binary_url "https://example.com/data.xlsx"
}

@test "is_binary_url: rejects md" {
  ! is_binary_url "https://example.com/file.md"
}

@test "is_binary_url: rejects json" {
  ! is_binary_url "https://example.com/data.json"
}

@test "is_binary_url: rejects no extension" {
  ! is_binary_url "https://example.com/page"
}

# -- is_plaintext_url --

@test "is_plaintext_url: detects md" {
  is_plaintext_url "https://example.com/file.md"
}

@test "is_plaintext_url: detects json" {
  is_plaintext_url "https://example.com/data.json"
}

@test "is_plaintext_url: detects jsonl" {
  is_plaintext_url "https://example.com/data.jsonl"
}

@test "is_plaintext_url: detects yaml" {
  is_plaintext_url "https://example.com/config.yaml"
}

@test "is_plaintext_url: detects yml" {
  is_plaintext_url "https://example.com/config.yml"
}

@test "is_plaintext_url: detects py" {
  is_plaintext_url "https://example.com/script.py"
}

@test "is_plaintext_url: detects c" {
  is_plaintext_url "https://example.com/main.c"
}

@test "is_plaintext_url: detects h" {
  is_plaintext_url "https://example.com/main.h"
}

@test "is_plaintext_url: rejects pdf" {
  ! is_plaintext_url "https://example.com/file.pdf"
}

@test "is_plaintext_url: rejects png" {
  ! is_plaintext_url "https://example.com/image.png"
}

@test "is_plaintext_url: rejects no extension" {
  ! is_plaintext_url "https://example.com/page"
}

# -- transform_url --

@test "transform_url: GitHub blob URL" {
  run transform_url "https://github.com/owner/repo/blob/main/README.md"
  [[ "${output}" == "https://raw.githubusercontent.com/owner/repo/refs/heads/main/README.md" ]]
}

@test "transform_url: GitHub blob URL with nested path" {
  run transform_url "https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/headless.md"
  [[ "${output}" == "https://raw.githubusercontent.com/google-gemini/gemini-cli/refs/heads/main/docs/cli/headless.md" ]]
}

@test "transform_url: Claude Code docs" {
  run transform_url "https://code.claude.com/docs/en/skills"
  [[ "${output}" == "https://code.claude.com/docs/en/skills.md" ]]
}

@test "transform_url: Claude Code docs strips anchor" {
  run transform_url "https://code.claude.com/docs/en/skills#pass-arguments-to-skills"
  [[ "${output}" == "https://code.claude.com/docs/en/skills.md" ]]
}

@test "transform_url: Claude Code docs strips query params" {
  run transform_url "https://code.claude.com/docs/en/skills?v=1"
  [[ "${output}" == "https://code.claude.com/docs/en/skills.md" ]]
}

@test "transform_url: Anthropic API docs" {
  run transform_url "https://platform.claude.com/docs/en/api/overview"
  [[ "${output}" == "https://platform.claude.com/docs/en/api/overview.md" ]]
}

@test "transform_url: Anthropic API docs with nested path" {
  run transform_url "https://platform.claude.com/docs/en/api/messages/create"
  [[ "${output}" == "https://platform.claude.com/docs/en/api/messages/create.md" ]]
}

@test "transform_url: Gemini CLI docs" {
  run transform_url "https://geminicli.com/docs/cli/headless"
  [[ "${output}" == "https://raw.githubusercontent.com/google-gemini/gemini-cli/refs/heads/main/docs/cli/headless.md" ]]
}

@test "transform_url: Gemini CLI docs strips trailing slash" {
  run transform_url "https://geminicli.com/docs/cli/headless/"
  [[ "${output}" == "https://raw.githubusercontent.com/google-gemini/gemini-cli/refs/heads/main/docs/cli/headless.md" ]]
}

@test "transform_url: Firebase docs" {
  run transform_url "https://firebase.google.com/docs/ai-logic"
  [[ "${output}" == "https://firebase.google.com/docs/ai-logic.md.txt" ]]
}

@test "transform_url: Firebase docs with nested path" {
  run transform_url "https://firebase.google.com/docs/cloud-messaging/android/client"
  [[ "${output}" == "https://firebase.google.com/docs/cloud-messaging/android/client.md.txt" ]]
}

@test "transform_url: Google dev docs" {
  run transform_url "https://ai.google.dev/gemini-api/docs"
  [[ "${output}" == "https://ai.google.dev/gemini-api/docs.md.txt" ]]
}

@test "transform_url: OpenAI docs" {
  run transform_url "https://platform.openai.com/docs/guides/prompt-engineering"
  [[ "${output}" == "https://platform.openai.com/docs/guides/prompt-engineering.md" ]]
}

@test "transform_url: unknown URL returns empty" {
  run transform_url "https://example.com/some-page"
  [[ "${output}" == "" ]]
}

@test "transform_url: non-matching domain returns empty" {
  run transform_url "https://docs.python.org/3/library/os.html"
  [[ "${output}" == "" ]]
}

# -- Edge cases --

@test "edge case: GitHub URL with query params" {
  run transform_url "https://github.com/owner/repo/blob/main/file.md?raw=true"
  [[ "${output}" == "https://raw.githubusercontent.com/owner/repo/refs/heads/main/file.md" ]]
}

@test "edge case: URL with both anchor and query" {
  run transform_url "https://code.claude.com/docs/en/skills?v=2#section"
  [[ "${output}" == "https://code.claude.com/docs/en/skills.md" ]]
}

@test "edge case: binary URL with query params still detected" {
  is_binary_url "https://example.com/photo.png?size=large"
}

@test "edge case: plaintext URL with anchor still detected" {
  is_plaintext_url "https://example.com/readme.md#installation"
}
