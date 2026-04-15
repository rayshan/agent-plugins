#!/usr/bin/env python3
"""Diagnose Claude Code LSP plugin configuration.

Checks installed LSP plugins, verifies language server binaries,
and detects configuration issues in the plugin cache.

Dependencies: none (stdlib only)
Usage: python3 check_lsp_config.py [--json]
"""

import json
import shutil
import sys
from pathlib import Path


def load_json(path: Path) -> dict | list | None:
    """Load a JSON file, returning None on any failure."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return None


def find_lsp_plugins(claude_home: Path | None = None) -> list[dict]:
    """Find all installed LSP plugins and diagnose their configuration.

    Args:
        claude_home: Override for ``~/.claude`` (useful for testing).

    Returns:
        List of diagnostic dicts, one per LSP plugin.
    """
    claude_dir = claude_home or (Path.home() / ".claude")

    installed = load_json(claude_dir / "plugins" / "installed_plugins.json")
    if not isinstance(installed, dict):
        return []

    known_marketplaces = load_json(claude_dir / "plugins" / "known_marketplaces.json")
    if not isinstance(known_marketplaces, dict):
        known_marketplaces = {}

    settings = load_json(claude_dir / "settings.json")
    enabled_plugins: dict = {}
    if isinstance(settings, dict):
        enabled_plugins = settings.get("enabledPlugins", {})

    results: list[dict] = []

    for plugin_id, entries in installed.get("plugins", {}).items():
        plugin_name = plugin_id.split("@")[0]
        if not plugin_name.endswith("-lsp"):
            continue

        marketplace_name = plugin_id.split("@")[1] if "@" in plugin_id else "unknown"
        entry = entries[0] if entries else {}
        install_path = Path(entry.get("installPath", ""))
        version = entry.get("version", "unknown")
        enabled = enabled_plugins.get(plugin_id, False)

        # --- Cached plugin.json ---
        cached_plugin = load_json(install_path / ".claude-plugin" / "plugin.json")
        if cached_plugin is None:
            cache_status = "no_plugin_json"
        elif isinstance(cached_plugin, dict) and "lspServers" in cached_plugin:
            cache_status = "has_config"
        else:
            cache_status = "missing_config"

        # --- Marketplace catalog ---
        lsp_servers: dict = {}
        mp_info = known_marketplaces.get(marketplace_name, {})
        mp_path = mp_info.get("installLocation", "")
        if mp_path:
            catalog = load_json(Path(mp_path) / ".claude-plugin" / "marketplace.json")
            if isinstance(catalog, dict):
                for p in catalog.get("plugins", []):
                    if (
                        isinstance(p, dict)
                        and p.get("name") == plugin_name
                        and "lspServers" in p
                    ):
                        lsp_servers = p["lspServers"]
                        break

        # --- Server binaries ---
        servers: list[dict] = []
        for server_name, config in lsp_servers.items():
            command = config.get("command", "")
            extensions = config.get("extensionToLanguage", {})
            binary_path = shutil.which(command)
            servers.append(
                {
                    "name": server_name,
                    "command": command,
                    "args": config.get("args", []),
                    "extensions": sorted(extensions.keys()),
                    "languages": sorted(set(extensions.values())),
                    "binary_found": binary_path is not None,
                    "binary_path": binary_path or "",
                }
            )

        all_extensions: list[str] = []
        for s in servers:
            all_extensions.extend(s["extensions"])

        ready = (
            enabled and bool(lsp_servers) and all(s["binary_found"] for s in servers)
        )

        results.append(
            {
                "plugin_id": plugin_id,
                "plugin_name": plugin_name,
                "marketplace": marketplace_name,
                "version": version,
                "enabled": enabled,
                "install_path": str(install_path),
                "cache_status": cache_status,
                "has_lsp_config_in_catalog": bool(lsp_servers),
                "servers": servers,
                "all_extensions": sorted(set(all_extensions)),
                "ready": ready,
            }
        )

    return results


def format_report(plugins: list[dict]) -> str:
    """Format a human-readable diagnostic report."""
    lines: list[str] = []

    if not plugins:
        lines.append("No LSP plugins found in Claude Code.")
        lines.append("Install from marketplace: look for plugins ending in '-lsp'.")
        return "\n".join(lines)

    lines.append(f"Found {len(plugins)} LSP plugin(s):\n")

    for p in plugins:
        if not p["enabled"]:
            status = "❌ Disabled in settings"
        elif not p["has_lsp_config_in_catalog"]:
            status = "⚠️  No lspServers in marketplace catalog"
        elif not all(s["binary_found"] for s in p["servers"]):
            missing = [s["command"] for s in p["servers"] if not s["binary_found"]]
            status = f"⚠️  Missing binary: {', '.join(missing)}"
        elif p["ready"]:
            status = "✅ Ready"
        else:
            status = "❓ Unknown issue"

        lines.append(
            f"  {p['plugin_name']} v{p['version']} ({p['marketplace']}) — {status}"
        )

        if p["cache_status"] == "no_plugin_json":
            lines.append(
                "    ℹ️  No plugin.json in cache "
                "(normal after reinstall, config read from catalog)"
            )
        elif p["cache_status"] == "missing_config":
            lines.append("    ⚠️  Cached plugin.json exists but lacks lspServers")

        for s in p["servers"]:
            if s["binary_found"]:
                binary_info = f"✅ {s['binary_path']}"
            else:
                binary_info = "❌ NOT IN PATH"
            lines.append(f"    Binary: {s['command']} — {binary_info}")
            lines.append(f"    Extensions: {', '.join(s['extensions'])}")

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    plugins = find_lsp_plugins()

    if "--json" in sys.argv:
        print(json.dumps(plugins, indent=2))
    else:
        print(format_report(plugins))


if __name__ == "__main__":
    main()
