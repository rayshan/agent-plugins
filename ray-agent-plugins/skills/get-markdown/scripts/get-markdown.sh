#!/bin/bash
# Fetches the markdown version of a URL.
#
# Transforms known URL patterns (GitHub, Claude Code docs, Anthropic API
# docs, Gemini CLI docs, Firebase docs, Google dev docs, OpenAI docs) to
# their raw markdown equivalents. Falls back to the Tabstack API for
# unknown URLs. Outputs markdown content to stdout, errors to stderr.

set -euo pipefail

readonly BINARY_EXTENSIONS="pdf|docx?|xlsx?|pptx?|odt|ods|odp|epub|zip|tar|gz|mp3|mp4|mov|avi|mkv|wav|flac|aac|ogg|webm|png|jpe?g|gif|svg|webp|bmp|tiff|ico"
readonly PLAINTEXT_EXTENSIONS="md|txt|csv|tsv|log|jsonl?|xml|ya?ml|toml|ini|cfg|conf|rtf|rst|adoc|tex|sh|py|js|ts|go|rs|rb|java|kt|[ch]|cpp|css|html|sql"

# Extracts the file extension from a URL path, ignoring query params
# and anchors.
#
# Arguments:
#   $1 - URL
# Outputs:
#   Extension (lowercase, without dot) to stdout, or nothing if none
get_path_extension() {
  local url="${1}"
  local path="${url%%[?#]*}"
  path="${path%/}"

  if [[ "${path}" =~ \.([a-zA-Z0-9]+)$ ]]; then
    printf '%s' "${BASH_REMATCH[1]}" | tr '[:upper:]' '[:lower:]'
  fi
}

# Checks if a URL points to a binary file based on extension.
#
# Arguments:
#   $1 - URL
# Returns:
#   0 if binary, 1 otherwise
is_binary_url() {
  local ext
  ext=$(get_path_extension "${1}")
  [[ -n "${ext}" && "${ext}" =~ ^(${BINARY_EXTENSIONS})$ ]]
}

# Checks if a URL points to a plain text file based on extension.
#
# Arguments:
#   $1 - URL
# Returns:
#   0 if plain text, 1 otherwise
is_plaintext_url() {
  local ext
  ext=$(get_path_extension "${1}")
  [[ -n "${ext}" && "${ext}" =~ ^(${PLAINTEXT_EXTENSIONS})$ ]]
}

# Transforms a URL to its markdown equivalent using known patterns.
# Outputs nothing if no pattern matches.
#
# Arguments:
#   $1 - URL
# Outputs:
#   Transformed URL to stdout, or nothing if no pattern matches
transform_url() {
  local url="${1}"

  # Strip query params, anchors, and trailing slash for matching
  local clean="${url%%[?#]*}"
  clean="${clean%/}"

  # GitHub: github.com/{owner}/{repo}/blob/{branch}/{path}
  if [[ "${clean}" =~ ^https?://github\.com/([^/]+)/([^/]+)/blob/(.+)$ ]]; then
    printf 'https://raw.githubusercontent.com/%s/%s/refs/heads/%s' \
      "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
    return 0
  fi

  # Claude Code docs: code.claude.com/docs/en/{page}
  if [[ "${clean}" =~ ^https?://code\.claude\.com/docs/en/(.+)$ ]]; then
    printf 'https://code.claude.com/docs/en/%s.md' "${BASH_REMATCH[1]}"
    return 0
  fi

  # Anthropic API docs: platform.claude.com/docs/en/{path}
  if [[ "${clean}" =~ ^https?://platform\.claude\.com/docs/en/(.+)$ ]]; then
    printf 'https://platform.claude.com/docs/en/%s.md' "${BASH_REMATCH[1]}"
    return 0
  fi

  # Gemini CLI docs: geminicli.com/docs/{path} -> GitHub raw
  if [[ "${clean}" =~ ^https?://geminicli\.com/docs/(.+)$ ]]; then
    printf 'https://raw.githubusercontent.com/google-gemini/gemini-cli/refs/heads/main/docs/%s.md' \
      "${BASH_REMATCH[1]}"
    return 0
  fi

  # Firebase docs: firebase.google.com/docs/{path}
  if [[ "${clean}" =~ ^https?://firebase\.google\.com/docs/(.+)$ ]]; then
    printf 'https://firebase.google.com/docs/%s.md.txt' "${BASH_REMATCH[1]}"
    return 0
  fi

  # Google dev docs: ai.google.dev/{path}
  if [[ "${clean}" =~ ^https?://ai\.google\.dev/(.+)$ ]]; then
    printf 'https://ai.google.dev/%s.md.txt' "${BASH_REMATCH[1]}"
    return 0
  fi

  # OpenAI docs: platform.openai.com/docs/{path}
  if [[ "${clean}" =~ ^https?://platform\.openai\.com/docs/(.+)$ ]]; then
    printf 'https://platform.openai.com/docs/%s.md' "${BASH_REMATCH[1]}"
    return 0
  fi

  # No pattern matched
  return 0
}

# Fetches URL content and validates the response is not HTML/empty/404.
#
# Arguments:
#   $1 - URL to fetch
# Outputs:
#   Content to stdout
# Returns:
#   0 on success, 1 on error (with message to stderr)
fetch_url() {
  local url="${1}"
  local tmpfile
  tmpfile=$(mktemp)

  local http_code
  http_code=$(curl --silent --location \
    --output "${tmpfile}" --write-out "%{http_code}" "${url}") || {
    rm -f "${tmpfile}"
    echo "ERROR: Failed to fetch URL: ${url}" >&2
    return 1
  }

  if [[ "${http_code}" == "404" ]]; then
    rm -f "${tmpfile}"
    echo "ERROR: URL returned 404. The page may not exist or the URL pattern may have changed." >&2
    return 1
  fi

  if [[ ! -s "${tmpfile}" ]]; then
    rm -f "${tmpfile}"
    echo "ERROR: URL returned empty content." >&2
    return 1
  fi

  local sample
  sample=$(head -c 500 "${tmpfile}" | tr '[:upper:]' '[:lower:]')
  if [[ "${sample}" == *'<!doctype'* || "${sample}" == *'<html'* ]]; then
    rm -f "${tmpfile}"
    echo "WARNING: URL returned HTML instead of markdown." >&2
    return 1
  fi

  cat "${tmpfile}"
  rm -f "${tmpfile}"
}

# Fetches markdown from a URL using the Tabstack API.
#
# Arguments:
#   $1 - URL to extract markdown from
# Outputs:
#   Markdown content to stdout
# Returns:
#   0 on success, 1 on error (with message to stderr)
fetch_tabstack() {
  local url="${1}"

  local api_key
  api_key=$(op read 'op://Carta personal/Tabstack for MCP/credential')

  local payload
  payload=$(jq --null-input --arg url "${url}" '{"url": $url, "metadata": true}')

  local response
  response=$(curl --silent --request POST "https://api.tabstack.ai/v1/extract/markdown" \
    --header "Authorization: Bearer ${api_key}" \
    --header "Content-Type: application/json" \
    --data "${payload}") || {
    echo "ERROR: Failed to connect to Tabstack API." >&2
    return 1
  }

  # Check for API errors
  if printf '%s' "${response}" | jq --exit-status '.error' > /dev/null 2>&1; then
    local error_msg
    error_msg=$(printf '%s' "${response}" | jq --raw-output '.error')
    echo "ERROR: Tabstack API: ${error_msg}" >&2
    return 1
  fi

  local content
  content=$(printf '%s' "${response}" | jq --raw-output '.content // ""')

  if [[ -z "${content}" ]]; then
    echo "ERROR: Tabstack returned empty content." >&2
    return 1
  fi

  printf '%s\n' "${content}"
}

main() {
  if [[ $# -lt 1 ]]; then
    echo "Usage: get-markdown.sh <url>" >&2
    exit 1
  fi

  local url="${1}"

  # Binary files cannot be converted to markdown
  if is_binary_url "${url}"; then
    echo "ERROR: URL points to a binary file that cannot be converted to markdown." >&2
    exit 1
  fi

  # Try known URL patterns first (handles e.g. GitHub blob URLs that
  # would otherwise match plaintext extension check but return HTML)
  local markdown_url
  markdown_url=$(transform_url "${url}")

  if [[ -n "${markdown_url}" ]]; then
    if fetch_url "${markdown_url}"; then
      exit 0
    fi
    # Transformed URL failed (e.g. returned HTML); fall through to Tabstack
    echo "Falling back to Tabstack extraction..." >&2
  fi

  # Plain text files can be fetched directly
  if is_plaintext_url "${url}"; then
    fetch_url "${url}"
    exit $?
  fi

  # Tabstack fallback for unknown patterns or failed transformations
  fetch_tabstack "${url}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
