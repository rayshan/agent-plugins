"""Tests for lcp.cli (argparse wiring smoke tests)."""

import pytest  # pyright: ignore[reportMissingImports]

from lcp import cli


class TestArgparseWiring:
    def test_rename_subcommand(self):
        args = cli.build_parser().parse_args(
            ["rename", "/old", "/new", "--rename-disk", "--dry-run"]
        )
        assert args.cmd == "rename"
        assert args.old_path == "/old"
        assert args.new_path == "/new"
        assert args.rename_disk is True
        assert args.dry_run is True

    def test_move_with_sessions(self):
        args = cli.build_parser().parse_args(
            ["move", "/src", "/dst", "--sessions", "a,b,c"]
        )
        assert args.cmd == "move"
        assert args.sessions == "a,b,c"
        assert args.last is None

    def test_move_with_last(self):
        args = cli.build_parser().parse_args(["move", "/src", "/dst", "--last", "3"])
        assert args.last == 3
        assert args.sessions is None

    def test_move_requires_selection(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["move", "/src", "/dst"])

    def test_move_sessions_and_last_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(
                ["move", "/src", "/dst", "--sessions", "a", "--last", "1"]
            )

    def test_list_subcommand(self):
        args = cli.build_parser().parse_args(["list", "/some/project"])
        assert args.cmd == "list"
        assert args.project_path == "/some/project"
