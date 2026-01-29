---
name: macos-app-bootstrap
description: Bootstrap a simple macOS desktop app using Swift Package Manager and command line tools. Use when user wants to create a new macOS app, start a Swift project, or scaffold a SwiftUI application.
argument-hint: [app-name]
disable-model-invocation: true
---

Bootstrap a macOS desktop app using Swift Package Manager and command line tools.

## Step 1: Gather Configuration

Use AskUserQuestion to collect these values (show defaults):

| Setting | Default | Notes |
|---------|---------|-------|
| App name | `My App` | Display name |
| Bundle file name | `My App.app` | The `.app` file name |
| Bundle ID | `com.rayshan.myapp` | Use all lowercase |
| Swift version | `6+` | Swift tools version |
| macOS version | `Sequoia 15` | Deployment target |

Derive these from user input:
- **Module name**: App name with spaces/special chars removed (e.g., `My App` → `MyApp`)
- **macOS version number**: Extract from version name (e.g., `Sequoia 15` → `15.0`)
- **Swift tools version**: Map version to tools version (e.g., `6+` → `6.0`)

## Step 2: Create Project Structure

Create this directory structure in the current working directory:

```
<project-root>/
├── Package.swift
├── README.md
├── CLAUDE.md
├── scripts/
│   └── create-bundle.sh
├── Sources/
│   └── <ModuleName>/
│       ├── <ModuleName>App.swift
│       └── ContentView.swift
└── Tests/
    └── <ModuleName>Tests/
        └── <ModuleName>Tests.swift
```

### Template Files

Use templates from this skill's [templates/](templates/) directory, replacing placeholders:

| Placeholder | Value |
|-------------|-------|
| `{{APP_NAME}}` | User's app name |
| `{{MODULE_NAME}}` | Derived module name |
| `{{BUNDLE_FILE_NAME}}` | User's bundle file name |
| `{{BUNDLE_ID}}` | User's bundle ID |
| `{{SWIFT_TOOLS_VERSION}}` | e.g., `6.0` |
| `{{MACOS_VERSION}}` | e.g., `15` (just major version for platform spec) |

| Template | Output Path |
|----------|-------------|
| [Package.swift.template](templates/Package.swift.template) | `Package.swift` |
| [App.swift.template](templates/App.swift.template) | `Sources/<ModuleName>/<ModuleName>App.swift` |
| [ContentView.swift.template](templates/ContentView.swift.template) | `Sources/<ModuleName>/ContentView.swift` |
| [Tests.swift.template](templates/Tests.swift.template) | `Tests/<ModuleName>Tests/<ModuleName>Tests.swift` |
| [README.md.template](templates/README.md.template) | `README.md` |

### Bundle Script

Copy [scripts/create-bundle.sh](scripts/create-bundle.sh) to `scripts/create-bundle.sh` in the project. This script creates the `.app` bundle from the built executable.

### CLAUDE.md

Create `CLAUDE.md` with:

```markdown
# Import rules

- Global software development rules: @~/.claude/AGENTS-global.md
- Global Swift development rules: @~/.claude/AGENTS-global-macos-swift.md

# Project rules

TK
```

## Step 3: Verify Setup

After creating the files:

1. Run `swift build` to verify the project compiles
2. Run `swift test` to verify tests pass

## Notes

- **Large libraries**: Before adding any external dependencies, warn about potential app size bloat and ask for confirmation. Explain pros, cons, and size impact.
- **Xcode compatibility**: The project can be opened and developed in Xcode at any time via `open Package.swift`.
- **Desktop only**: This bootstraps a macOS desktop app only, not iOS or multi-platform.
