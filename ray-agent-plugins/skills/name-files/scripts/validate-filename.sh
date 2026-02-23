#!/usr/bin/env bash
# validate-filename.sh — Validate filenames for cross-platform compatibility.
#
# Usage: validate-filename.sh <filename> [<filename> ...]
# Exit codes: 0 = all pass, 1 = one or more failures, 2 = usage error.
#
# Rules checked:
#   1. Safe characters: stem contains only [a-z0-9_-]
#   2. No reserved names: stem is not a Windows device name
#   3. Clean ends: no leading/trailing space or period
#   4. Lowercase: all letters are lowercase
#   5. Length limit: stem <= 200 characters
#   6. Unicode warning: non-ASCII characters trigger a warning

set -uo pipefail

readonly MAX_STEM_LENGTH=200
readonly RESERVED_NAMES=(
  CON PRN AUX NUL
  COM1 COM2 COM3 COM4 COM5 COM6 COM7 COM8 COM9
  LPT1 LPT2 LPT3 LPT4 LPT5 LPT6 LPT7 LPT8 LPT9
)

# Validate a single filename.
# Args: $1 = filename (basename or path; directory components are stripped)
# Returns: 0 if valid, 1 if invalid.
validate_filename() {
  local input="$1"
  local full stem ext upper_stem
  local errors=0 warnings=0

  full="$(basename -- "$input")"
  if [[ -z "$full" ]]; then
    printf "  FAIL  Empty filename\n"
    return 1
  fi

  # Split into stem and extension at the last dot.
  # Dotfiles without a second dot (e.g., .gitignore) do not match and are
  # treated as stem-only, which correctly triggers rule 1 and rule 3 failures.
  if [[ "$full" =~ ^(.+)\.([^.]+)$ ]]; then
    stem="${BASH_REMATCH[1]}"
    ext="${BASH_REMATCH[2]}"
  else
    stem="$full"
    ext=""
  fi

  # Rule 1: Safe characters (stem must be alphanumeric, hyphen, or underscore)
  if [[ ! "$stem" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    printf "  FAIL  Safe characters — stem contains invalid characters: '%s'\n" "$stem"
    printf "        Allowed: a-z, 0-9, hyphen (-), underscore (_)\n"
    errors=$((errors + 1))
  fi

  # Rule 2: No reserved names (case-insensitive)
  upper_stem="$(printf '%s' "$stem" | tr '[:lower:]' '[:upper:]')"
  for reserved in "${RESERVED_NAMES[@]}"; do
    if [[ "$upper_stem" == "$reserved" ]]; then
      printf "  FAIL  Reserved name — '%s' is reserved on Windows\n" "$stem"
      errors=$((errors + 1))
      break
    fi
  done

  # Rule 3: Clean ends (no leading/trailing space or period)
  case "$full" in
    [[:space:].]*)
      printf "  FAIL  Clean ends — filename starts with a space or period\n"
      errors=$((errors + 1))
      ;;
  esac
  case "$full" in
    *[[:space:].])
      printf "  FAIL  Clean ends — filename ends with a space or period\n"
      errors=$((errors + 1))
      ;;
  esac

  # Rule 4: Lowercase
  if [[ "$stem" =~ [A-Z] ]]; then
    printf "  FAIL  Lowercase — stem contains uppercase: '%s'\n" "$stem"
    errors=$((errors + 1))
  fi
  if [[ -n "$ext" ]] && [[ "$ext" =~ [A-Z] ]]; then
    printf "  FAIL  Lowercase — extension contains uppercase: '%s'\n" "$ext"
    errors=$((errors + 1))
  fi

  # Rule 5: Stem length (max 200 characters)
  if [[ "${#stem}" -gt "$MAX_STEM_LENGTH" ]]; then
    printf "  FAIL  Length — stem is %d characters (max %d)\n" "${#stem}" "$MAX_STEM_LENGTH"
    errors=$((errors + 1))
  fi

  # Rule 6: Unicode / non-ASCII warning
  if printf '%s' "$full" | LC_ALL=C grep -q '[^ -~]'; then
    printf "  WARN  Unicode — filename contains non-ASCII characters: '%s'\n" "$full"
    printf "        Consider transliterating to ASCII equivalents.\n"
    warnings=$((warnings + 1))
  fi

  # Summary
  if [[ "$errors" -eq 0 ]] && [[ "$warnings" -eq 0 ]]; then
    printf "  PASS  '%s'\n" "$full"
  elif [[ "$errors" -eq 0 ]]; then
    printf "  PASS  '%s' — %d warning(s)\n" "$full" "$warnings"
  else
    printf "  FAIL  '%s' — %d error(s), %d warning(s)\n" "$full" "$errors" "$warnings"
  fi

  if [[ "$errors" -gt 0 ]]; then
    return 1
  fi
  return 0
}

main() {
  if [[ $# -eq 0 ]]; then
    printf "Usage: validate-filename.sh <filename> [<filename> ...]\n"
    printf "Validates filenames for cross-platform compatibility.\n"
    return 2
  fi

  local failures=0
  for filename in "$@"; do
    validate_filename "$filename" || failures=$((failures + 1))
  done

  if [[ "$failures" -gt 0 ]]; then
    return 1
  fi
  return 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
