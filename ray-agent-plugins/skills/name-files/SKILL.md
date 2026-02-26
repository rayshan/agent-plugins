---
name: name-files
description: This skill should be used when the user explicitly asks to "name a file", "rename a file", "suggest a filename", "make filename compatible", "fix filename", "clean up filename", or needs help creating cross-platform compatible filenames. Applies strict naming rules for maximum compatibility across Windows, macOS, and Linux.
---

# Name Files

Generate filenames with maximum compatibility across modern platforms (Windows, macOS, Linux), cloud storage services, and common tools.

## Rules

| # | Rule | Requirement | Rationale |
|---|------|-------------|-----------|
| 1 | Safe characters | Stem: only `a-z`, `0-9`, `-`, `_` | Windows forbids `<>:"/\|?*`; spaces break shell scripts and URLs; other special characters cause issues in cloud storage and archive tools |
| 2 | No reserved names | Stem must not be `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9` (case-insensitive) | Windows reserves these as device names; NTFS enforces this at the filesystem level |
| 3 | Clean ends | No leading or trailing space or period | Windows silently strips trailing periods/spaces; leading periods create hidden files on Unix |
| 4 | Lowercase | All lowercase letters | Avoids case-sensitivity conflicts between Linux (case-sensitive) and Windows/macOS (case-insensitive) |
| 5 | Length limit | Stem max 200 characters (excluding extension) | Accommodates Windows MAX_PATH (260) and Excel path limits (~218) after typical path prefixes |
| 6 | Unicode warning | Warn on non-ASCII characters (CJK, accented, emoji) | Encoding mismatches across systems can corrupt filenames; suggest ASCII transliterations |

**Terminology:** *stem* = the filename before the last dot (extension separator). Example: in `my-report.pdf`, the stem is `my-report`.

## Workflow

1. Determine what the file represents and propose a filename following the rules above.
2. Validate by running the validation script:

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/skills/name-files/scripts/validate-filename.sh" "<proposed-filename>"
   ```

3. If validation reports errors, fix and re-validate.
4. Present the final filename to the user.

## Validation Script

`scripts/validate-filename.sh` — Checks all rules above. Accepts one or more filenames. Exit code 0 = all pass, 1 = failure, 2 = usage error.
