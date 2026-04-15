"""Tests for check_lsp_config.py."""

import json
from pathlib import Path

from check_lsp_config import find_lsp_plugins, format_report, load_json


# --- load_json ---


def test_load_json_valid(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text('{"key": "value"}')
    assert load_json(path) == {"key": "value"}


def test_load_json_missing(tmp_path: Path) -> None:
    assert load_json(tmp_path / "nonexistent.json") is None


def test_load_json_invalid(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("not json")
    assert load_json(path) is None


# --- Helpers ---


def _setup_claude_dir(
    tmp_path: Path,
    *,
    installed_plugins: dict | None = None,
    settings: dict | None = None,
    known_marketplaces: dict | None = None,
    catalog_plugins: list[dict] | None = None,
    marketplace_name: str = "test-mp",
    cache_plugin_json: dict | None = None,
    plugin_name: str = "test-lsp",
    plugin_version: str = "1.0.0",
    skip_cache: bool = False,
) -> Path:
    """Create a mock ~/.claude directory with the given configuration."""
    claude = tmp_path / ".claude"
    claude.mkdir(exist_ok=True)
    plugins_dir = claude / "plugins"
    plugins_dir.mkdir(exist_ok=True)

    plugin_id = f"{plugin_name}@{marketplace_name}"

    # Cache path
    cache_path = tmp_path / "cache" / marketplace_name / plugin_name / plugin_version
    if not skip_cache:
        cache_path.mkdir(parents=True, exist_ok=True)
        plugin_json_dir = cache_path / ".claude-plugin"
        plugin_json_dir.mkdir(exist_ok=True)
        if cache_plugin_json is not None:
            (plugin_json_dir / "plugin.json").write_text(json.dumps(cache_plugin_json))

    # installed_plugins.json
    if installed_plugins is None:
        installed_plugins = {
            "version": 2,
            "plugins": {
                plugin_id: [
                    {
                        "installPath": str(cache_path),
                        "version": plugin_version,
                    }
                ]
            },
        }
    (plugins_dir / "installed_plugins.json").write_text(json.dumps(installed_plugins))

    # settings.json
    if settings is None:
        settings = {"enabledPlugins": {plugin_id: True}}
    (claude / "settings.json").write_text(json.dumps(settings))

    # Marketplace catalog
    mp_path = tmp_path / "marketplaces" / marketplace_name
    mp_path.mkdir(parents=True, exist_ok=True)
    (mp_path / ".claude-plugin").mkdir(exist_ok=True)
    if catalog_plugins is not None:
        catalog = {"plugins": catalog_plugins}
    else:
        catalog = {"plugins": []}
    (mp_path / ".claude-plugin" / "marketplace.json").write_text(json.dumps(catalog))

    # known_marketplaces.json
    if known_marketplaces is None:
        known_marketplaces = {marketplace_name: {"installLocation": str(mp_path)}}
    (plugins_dir / "known_marketplaces.json").write_text(json.dumps(known_marketplaces))

    return claude


# --- find_lsp_plugins ---


def test_no_installed_file(tmp_path: Path) -> None:
    """Empty claude dir returns empty list."""
    claude = tmp_path / ".claude"
    claude.mkdir()
    assert find_lsp_plugins(claude) == []


def test_no_lsp_plugins(tmp_path: Path) -> None:
    """Non-LSP plugins are ignored."""
    claude = _setup_claude_dir(
        tmp_path,
        installed_plugins={
            "version": 2,
            "plugins": {
                "some-plugin@mp": [{"installPath": "/tmp/x", "version": "1.0"}]
            },
        },
    )
    assert find_lsp_plugins(claude) == []


def test_plugin_detected_ready(tmp_path: Path) -> None:
    """Plugin with catalog config and binary in PATH reports as ready."""
    claude = _setup_claude_dir(
        tmp_path,
        cache_plugin_json={"name": "test-lsp"},
        catalog_plugins=[
            {
                "name": "test-lsp",
                "lspServers": {
                    "test-server": {
                        "command": "python3",
                        "args": ["--stdio"],
                        "extensionToLanguage": {".py": "python"},
                    }
                },
            }
        ],
    )
    result = find_lsp_plugins(claude)
    assert len(result) == 1

    p = result[0]
    assert p["plugin_name"] == "test-lsp"
    assert p["enabled"] is True
    assert p["has_lsp_config_in_catalog"] is True
    assert p["ready"] is True
    assert len(p["servers"]) == 1
    assert p["servers"][0]["command"] == "python3"
    assert p["servers"][0]["binary_found"] is True
    assert p["all_extensions"] == [".py"]


def test_cache_no_plugin_json(tmp_path: Path) -> None:
    """Plugin with no plugin.json in cache (normal after reinstall)."""
    claude = _setup_claude_dir(
        tmp_path,
        skip_cache=True,
        catalog_plugins=[
            {
                "name": "test-lsp",
                "lspServers": {
                    "s": {
                        "command": "python3",
                        "extensionToLanguage": {".py": "python"},
                    }
                },
            }
        ],
    )
    result = find_lsp_plugins(claude)
    assert len(result) == 1
    assert result[0]["cache_status"] == "no_plugin_json"
    assert result[0]["ready"] is True


def test_cache_missing_lsp_config(tmp_path: Path) -> None:
    """Plugin.json exists in cache but lacks lspServers field."""
    claude = _setup_claude_dir(
        tmp_path,
        cache_plugin_json={"name": "test-lsp", "version": "1.0.0"},
        catalog_plugins=[
            {
                "name": "test-lsp",
                "lspServers": {
                    "s": {
                        "command": "python3",
                        "extensionToLanguage": {".py": "python"},
                    }
                },
            }
        ],
    )
    result = find_lsp_plugins(claude)
    assert len(result) == 1
    assert result[0]["cache_status"] == "missing_config"


def test_cache_has_lsp_config(tmp_path: Path) -> None:
    """Plugin.json in cache includes lspServers."""
    claude = _setup_claude_dir(
        tmp_path,
        cache_plugin_json={
            "name": "test-lsp",
            "lspServers": {
                "s": {
                    "command": "python3",
                    "extensionToLanguage": {".py": "python"},
                }
            },
        },
        catalog_plugins=[
            {
                "name": "test-lsp",
                "lspServers": {
                    "s": {
                        "command": "python3",
                        "extensionToLanguage": {".py": "python"},
                    }
                },
            }
        ],
    )
    result = find_lsp_plugins(claude)
    assert len(result) == 1
    assert result[0]["cache_status"] == "has_config"


def test_missing_binary(tmp_path: Path) -> None:
    """Plugin with nonexistent binary reports not ready."""
    claude = _setup_claude_dir(
        tmp_path,
        cache_plugin_json={"name": "test-lsp"},
        catalog_plugins=[
            {
                "name": "test-lsp",
                "lspServers": {
                    "s": {
                        "command": "nonexistent-binary-xyz-12345",
                        "extensionToLanguage": {".xyz": "xyzlang"},
                    }
                },
            }
        ],
    )
    result = find_lsp_plugins(claude)
    assert len(result) == 1

    p = result[0]
    assert p["servers"][0]["binary_found"] is False
    assert p["ready"] is False


def test_plugin_disabled(tmp_path: Path) -> None:
    """Disabled plugin reports not ready."""
    claude = _setup_claude_dir(
        tmp_path,
        settings={"enabledPlugins": {"test-lsp@test-mp": False}},
        cache_plugin_json={"name": "test-lsp"},
        catalog_plugins=[
            {
                "name": "test-lsp",
                "lspServers": {
                    "s": {
                        "command": "python3",
                        "extensionToLanguage": {".py": "python"},
                    }
                },
            }
        ],
    )
    result = find_lsp_plugins(claude)
    assert len(result) == 1
    assert result[0]["enabled"] is False
    assert result[0]["ready"] is False


def test_no_catalog_config(tmp_path: Path) -> None:
    """Plugin installed but marketplace catalog has no lspServers."""
    claude = _setup_claude_dir(
        tmp_path,
        cache_plugin_json={"name": "test-lsp"},
        catalog_plugins=[{"name": "test-lsp"}],
    )
    result = find_lsp_plugins(claude)
    assert len(result) == 1
    assert result[0]["has_lsp_config_in_catalog"] is False
    assert result[0]["servers"] == []
    assert result[0]["ready"] is False


def test_multiple_extensions(tmp_path: Path) -> None:
    """Server with multiple extensions reports all of them."""
    claude = _setup_claude_dir(
        tmp_path,
        cache_plugin_json={"name": "test-lsp"},
        catalog_plugins=[
            {
                "name": "test-lsp",
                "lspServers": {
                    "ts": {
                        "command": "python3",
                        "extensionToLanguage": {
                            ".ts": "typescript",
                            ".tsx": "typescriptreact",
                            ".js": "javascript",
                        },
                    }
                },
            }
        ],
    )
    result = find_lsp_plugins(claude)
    assert len(result) == 1
    assert set(result[0]["all_extensions"]) == {".ts", ".tsx", ".js"}
    assert "javascript" in result[0]["servers"][0]["languages"]
    assert "typescript" in result[0]["servers"][0]["languages"]


# --- format_report ---


def test_format_report_empty() -> None:
    report = format_report([])
    assert "No LSP plugins found" in report


def test_format_report_ready() -> None:
    plugins = [
        {
            "plugin_name": "pyright-lsp",
            "version": "1.0.0",
            "marketplace": "official",
            "enabled": True,
            "has_lsp_config_in_catalog": True,
            "cache_status": "has_config",
            "servers": [
                {
                    "command": "pyright-langserver",
                    "binary_found": True,
                    "binary_path": "/usr/bin/pyright-langserver",
                    "extensions": [".py"],
                }
            ],
            "ready": True,
        }
    ]
    report = format_report(plugins)
    assert "✅ Ready" in report
    assert "pyright-lsp" in report


def test_format_report_missing_binary() -> None:
    plugins = [
        {
            "plugin_name": "swift-lsp",
            "version": "1.0.0",
            "marketplace": "official",
            "enabled": True,
            "has_lsp_config_in_catalog": True,
            "cache_status": "no_plugin_json",
            "servers": [
                {
                    "command": "sourcekit-lsp",
                    "binary_found": False,
                    "binary_path": "",
                    "extensions": [".swift"],
                }
            ],
            "ready": False,
        }
    ]
    report = format_report(plugins)
    assert "Missing binary" in report
    assert "NOT IN PATH" in report


def test_format_report_disabled() -> None:
    plugins = [
        {
            "plugin_name": "test-lsp",
            "version": "1.0.0",
            "marketplace": "mp",
            "enabled": False,
            "has_lsp_config_in_catalog": True,
            "cache_status": "has_config",
            "servers": [
                {
                    "command": "test",
                    "binary_found": True,
                    "binary_path": "/usr/bin/test",
                    "extensions": [".x"],
                }
            ],
            "ready": False,
        }
    ]
    report = format_report(plugins)
    assert "Disabled" in report
