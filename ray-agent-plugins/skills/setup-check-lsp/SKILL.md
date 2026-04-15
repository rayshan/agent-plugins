---
name: setup-check-lsp
description: >-
  This skill should be used when the user asks to "check LSP", "test LSP
  plugins", "diagnose LSP", "fix LSP", "LSP not working", "language server
  not available", "code intelligence not working", "verify LSP setup",
  "goToDefinition not working", "hover not working", or mentions issues
  with any LSP operations in Claude Code. Also use when the user installs
  a new LSP plugin and wants to verify it works, or after reinstalling
  plugins. Runs a comprehensive diagnostic of all installed LSP plugins,
  checks language server binaries, detects configuration issues, and
  live-tests each working plugin with the LSP tool.
allowed-tools: Bash, LSP, Glob, Read
---

# Check LSP Plugins

Diagnose and test Claude Code's LSP (Language Server Protocol) plugins.

## Background

LSP plugins give Claude Code code intelligence — go-to-definition,
find-references, hover type info, call hierarchy, and more. They work by
connecting to language server binaries installed on the user's machine.

The diagnostic covers three layers:

1. **Configuration** — Is the plugin installed, enabled, and does the
   marketplace catalog contain the `lspServers` config that tells Claude
   Code how to invoke the language server?
2. **Binary** — Is the language server command available in PATH?
3. **Runtime** — Does the LSP tool actually return results when invoked?

### Common failure modes

- **Missing catalog config**: The marketplace catalog
  (`marketplace.json`) must contain an `lspServers` entry for the plugin.
  Without it, Claude Code does not know which command to run or which
  file extensions to handle.
- **Missing binary**: The language server is not installed or not in
  PATH. Each LSP plugin's README lists install instructions.
- **Cold start**: The first LSP call after a server starts may fail
  with "server is starting". Retry after a few seconds.
- **Wrong project root**: Language servers like jdtls (Java) and
  sourcekit-lsp (Swift) need the working directory to be the project
  root (where `build.gradle` or `Package.swift` lives) for full
  cross-file intelligence. When invoked from a different directory,
  hover and documentSymbol may work but goToDefinition and
  findReferences will be degraded.

## Step 1: Run the diagnostic script

Locate and run the bundled diagnostic script. It reads Claude Code's
plugin configuration files and checks each language server binary.

```bash
python3 "$(find ~/.claude/plugins/cache ~/.claude/skills \
  -path "*/setup-check-lsp/scripts/check_lsp_config.py" -type f 2>/dev/null \
  | head -1)" --json
```

If the script is not found (e.g., the skill was loaded from a different
location), perform the checks manually:

1. Read `~/.claude/plugins/installed_plugins.json` — find entries whose
   name ends with `-lsp`.
2. Read `~/.claude/settings.json` — check `enabledPlugins` for each.
3. For each plugin's marketplace, read the marketplace catalog at
   `~/.claude/plugins/marketplaces/<marketplace>/.claude-plugin/marketplace.json`
   and look for the `lspServers` field on the matching plugin entry.
4. For each server in `lspServers`, check if the `command` is in PATH
   with `which <command>`.

## Step 2: Report configuration status

Present findings in a table:

| Plugin | Enabled | Catalog Config | Binary | Status |
|--------|---------|----------------|--------|--------|
| name   | Yes/No  | Yes/No         | path or MISSING | Ready / Issue description |

For each issue, explain the fix:

- **Not enabled**: Enable in Claude Code settings or run
  `claude plugins enable <plugin-id>`.
- **No catalog config**: The marketplace may not support this plugin
  yet, or the marketplace cache is stale. Try
  `claude plugins update <plugin-id>`.
- **Missing binary**: Provide the install command. Common ones:
  - `pyright-lsp`: `pip install pyright` or `npm install -g pyright`
  - `typescript-lsp`: `npm install -g typescript-language-server typescript`
  - `swift-lsp`: Included with Xcode (`xcode-select --install`)
  - `jdtls-lsp`: `brew install jdtls`
  - `gopls-lsp`: `go install golang.org/x/tools/gopls@latest`
  - `rust-analyzer-lsp`: `rustup component add rust-analyzer`

## Step 3: Live-test working plugins

For each plugin marked "ready" in step 2:

### 3a. Find a test file

Use Glob to search for files matching the plugin's extensions. Search
the current working directory first. If no files are found, check any
directories added with `--add-dir`. If still none, skip this plugin and
mark it as "Skipped (no matching files)".

Prefer source files in `src/`, `lib/`, or `Sources/` over generated
files in `build/`, `dist/`, or `node_modules/`.

### 3b. Test documentSymbol

Run `documentSymbol` on the found file. This operation typically works
even during server cold-start because it only requires parsing, not full
project indexing.

```text
LSP(operation: "documentSymbol", filePath: "<path>", line: 1, character: 1)
```

If it fails with "server is starting", wait 5 seconds and retry once.

### 3c. Test hover

Pick a symbol from the documentSymbol results (a function or class
definition) and run `hover` on it to verify the server provides type
information.

```text
LSP(operation: "hover", filePath: "<path>", line: <N>, character: <N>)
```

Hover returning type signatures (e.g., `func merge(configuration:
MergeConfiguration) throws -> URL`) confirms the server has full
language intelligence for the file.

### 3d. Record results

Note whether each operation returned meaningful results, returned empty,
or errored.

## Step 4: Present test results

Add a second table with live-test results:

| Plugin | documentSymbol | hover | Test File | Notes |
|--------|---------------|-------|-----------|-------|
| name   | Pass/Fail/Skip | Pass/Fail/Skip | path | e.g., "server cold start, passed on retry" |

## Step 5: Summary and recommendations

End with a brief summary:

- Total plugins: N installed, M ready, K tested
- Any action items (reinstall, install binary, restart session)

If all plugins pass, confirm that LSP is fully operational.

If issues remain after fixes, remind the user:

- LSP tools register at session startup — restart Claude Code after
  making changes.
- Language servers that need a build system (Java, Swift, C++) work
  best when Claude Code is launched from the project root.
