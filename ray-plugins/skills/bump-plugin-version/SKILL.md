---
name: bump-plugin-version
description: Bump a plugin's version in its plugin.json manifest
argument-hint: [plugin-name] [major|minor|patch|x.y.z]
disable-model-invocation: true
allowed-tools: Read, Edit, Glob, AskUserQuestion
---

Bump the version of a Claude Code plugin.

## Step 1: Identify Plugin

If `$1` (plugin name) was provided, use it. Otherwise, use AskUserQuestion to ask which plugin to bump. List available plugins by searching for `.claude-plugin/plugin.json` files in the workspace.

## Step 2: Determine Version Change

If `$2` (version change) was provided, use it. Otherwise, use AskUserQuestion with these options:

1. Patch (x.y.Z) - Bug fixes, minor changes
2. Minor (x.Y.0) - New features, backward compatible
3. Major (X.0.0) - Breaking changes
4. Exact version - Specify a version number

If user selects "Exact version", ask for the specific version string.

## Step 3: Read Current Version

Read the plugin's `.claude-plugin/plugin.json` file and extract the current version.

## Step 4: Calculate New Version

- **patch**: Increment the third number (1.2.3 → 1.2.4)
- **minor**: Increment the second number, reset patch to 0 (1.2.3 → 1.3.0)
- **major**: Increment the first number, reset minor and patch to 0 (1.2.3 → 2.0.0)
- **exact**: Use the provided version string (validate SemVer format: X.Y.Z)

## Step 5: Apply Update

Use Edit to update the `version` field in the plugin's `.claude-plugin/plugin.json`.

## Step 6: Confirm

Display: `Updated {plugin-name} version: {old-version} → {new-version}`
