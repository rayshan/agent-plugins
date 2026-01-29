#!/bin/bash
#
# Create a macOS .app bundle from a Swift Package Manager executable.
#
# Usage: ./create-bundle.sh
#
# This script reads configuration from environment variables or uses defaults.
# Set these before running:
#   MODULE_NAME      - The executable name (required)
#   APP_NAME         - Display name (defaults to MODULE_NAME)
#   BUNDLE_FILE_NAME - The .app file name (defaults to "$APP_NAME.app")
#   BUNDLE_ID        - Bundle identifier (defaults to "com.example.$MODULE_NAME")
#   MACOS_VERSION    - Minimum macOS version (defaults to "15.0")

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly TEMPLATE_DIR="${SCRIPT_DIR}/../templates"

# Configuration
readonly MODULE_NAME="${MODULE_NAME:?MODULE_NAME is required}"
readonly APP_NAME="${APP_NAME:-${MODULE_NAME}}"
readonly BUNDLE_FILE_NAME="${BUNDLE_FILE_NAME:-${APP_NAME}.app}"
readonly BUNDLE_ID="${BUNDLE_ID:-com.example.${MODULE_NAME,,}}"
readonly MACOS_VERSION="${MACOS_VERSION:-15.0}"

# Render a template file by replacing {{PLACEHOLDER}} with variable values.
#
# Globals:
#   MODULE_NAME, APP_NAME, BUNDLE_ID, MACOS_VERSION
# Arguments:
#   $1 - Path to template file
# Outputs:
#   Rendered template to stdout
# Returns:
#   0 on success, non-zero if template file not found
render_template() {
    local template_file="$1"

    if [[ ! -f "${template_file}" ]]; then
        echo "Error: Template file not found: ${template_file}" >&2
        return 1
    fi

    while IFS= read -r line || [[ -n "${line}" ]]; do
        line="${line//\{\{MODULE_NAME\}\}/${MODULE_NAME}}"
        line="${line//\{\{APP_NAME\}\}/${APP_NAME}}"
        line="${line//\{\{BUNDLE_ID\}\}/${BUNDLE_ID}}"
        line="${line//\{\{MACOS_VERSION\}\}/${MACOS_VERSION}}"
        printf '%s\n' "${line}"
    done < "${template_file}"
}

# Build the Swift package and create a macOS .app bundle.
#
# Globals:
#   MODULE_NAME      - Executable/module name
#   APP_NAME         - Display name for the app
#   BUNDLE_FILE_NAME - Output .app file name
#   BUNDLE_ID        - Bundle identifier
#   MACOS_VERSION    - Minimum macOS version
#   TEMPLATE_DIR     - Path to templates directory
# Arguments:
#   None
# Outputs:
#   Writes status messages to stdout
#   Creates .app bundle in current directory
# Returns:
#   0 on success, non-zero on failure
main() {
    echo "Building release..."
    swift build --configuration release

    echo "Creating app bundle: ${BUNDLE_FILE_NAME}"
    mkdir -p "${BUNDLE_FILE_NAME}/Contents/MacOS"
    mkdir -p "${BUNDLE_FILE_NAME}/Contents/Resources"

    echo "Copying executable..."
    cp ".build/release/${MODULE_NAME}" "${BUNDLE_FILE_NAME}/Contents/MacOS/"

    echo "Creating Info.plist..."
    render_template "${TEMPLATE_DIR}/Info.plist.template" \
        > "${BUNDLE_FILE_NAME}/Contents/Info.plist"

    echo "Done! Created: ${BUNDLE_FILE_NAME}"
    echo ""
    echo "To install, run:"
    echo "  cp -r \"${BUNDLE_FILE_NAME}\" /Applications/"
}

main "$@"
