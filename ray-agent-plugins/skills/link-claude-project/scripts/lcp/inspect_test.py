"""Tests for lcp.inspect."""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

from lcp import core, inspect


class TestExtractUserText:
    def test_string_content(self):
        assert inspect._extract_user_text("hello") == "hello"

    def test_list_with_text_block(self):
        assert (
            inspect._extract_user_text([{"type": "text", "text": "hi there"}])
            == "hi there"
        )

    def test_list_skips_tool_results(self):
        content = [
            {"type": "tool_result", "content": "x"},
            {"type": "text", "text": "actual prompt"},
        ]
        assert inspect._extract_user_text(content) == "actual prompt"

    def test_empty_text_falls_back(self):
        content = [{"type": "text", "text": ""}, {"type": "text", "text": "later"}]
        assert inspect._extract_user_text(content) == "later"

    def test_unknown_shape_returns_empty(self):
        assert inspect._extract_user_text(None) == ""
        assert inspect._extract_user_text(42) == ""


class TestTruncate:
    def test_short_unchanged(self):
        assert inspect._truncate("hello", 80) == "hello"

    def test_long_truncated(self):
        out = inspect._truncate("x" * 100, 20)
        assert len(out) == 20
        assert out.endswith("…")

    def test_newlines_replaced(self):
        assert inspect._truncate("a\nb\nc", 80) == "a b c"


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


class TestFirstUserMessage:
    def test_finds_first_user_message(self, tmp_path):
        f = tmp_path / "s.jsonl"
        _write_jsonl(
            f,
            [
                {"type": "last-prompt", "leafUuid": "x"},
                {"type": "permission-mode"},
                {"type": "user", "message": {"role": "user", "content": "hello world"}},
                {"type": "user", "message": {"role": "user", "content": "second"}},
            ],
        )
        assert inspect.first_user_message(f) == "hello world"

    def test_skips_assistant(self, tmp_path):
        f = tmp_path / "s.jsonl"
        _write_jsonl(
            f,
            [
                {"type": "user", "message": {"role": "assistant", "content": "no"}},
                {"type": "user", "message": {"role": "user", "content": "yes"}},
            ],
        )
        assert inspect.first_user_message(f) == "yes"

    def test_skips_malformed_lines(self, tmp_path):
        f = tmp_path / "s.jsonl"
        f.write_text(
            "not-json\n"
            + json.dumps({"type": "user", "message": {"role": "user", "content": "ok"}})
            + "\n",
            encoding="utf-8",
        )
        assert inspect.first_user_message(f) == "ok"

    def test_truncates(self, tmp_path):
        f = tmp_path / "s.jsonl"
        _write_jsonl(
            f,
            [{"type": "user", "message": {"role": "user", "content": "x" * 200}}],
        )
        assert len(inspect.first_user_message(f, max_chars=20)) == 20

    def test_missing_file_returns_empty(self, tmp_path):
        assert inspect.first_user_message(tmp_path / "nope.jsonl") == ""

    def test_no_user_message_returns_empty(self, tmp_path):
        f = tmp_path / "s.jsonl"
        _write_jsonl(f, [{"type": "last-prompt", "leafUuid": "x"}])
        assert inspect.first_user_message(f) == ""


class TestGatherSessionInfo:
    def test_returns_sessions_newest_first(self, tmp_path):
        projects = tmp_path / "projects"
        storage = projects / "encoded"
        storage.mkdir(parents=True)
        a = storage / "aaa.jsonl"
        b = storage / "bbb.jsonl"
        a.write_text(
            json.dumps({"type": "user", "message": {"role": "user", "content": "A"}}),
            encoding="utf-8",
        )
        b.write_text(
            json.dumps({"type": "user", "message": {"role": "user", "content": "B"}}),
            encoding="utf-8",
        )
        os.utime(a, (time.time() - 100, time.time() - 100))
        os.utime(b, None)

        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "encode_path", lambda _: "encoded"),
        ):
            infos = inspect.gather_session_info("/whatever")

        assert [i.uuid for i in infos] == ["bbb", "aaa"]
        assert infos[0].first_user_msg == "B"

    def test_picks_up_subdir_flags(self, tmp_path):
        projects = tmp_path / "projects"
        storage = projects / "encoded"
        storage.mkdir(parents=True)
        (storage / "aaa.jsonl").write_text("{}", encoding="utf-8")
        (storage / "aaa" / "tool-results").mkdir(parents=True)
        (storage / "aaa" / "subagents").mkdir(parents=True)

        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "encode_path", lambda _: "encoded"),
        ):
            infos = inspect.gather_session_info("/whatever")

        assert len(infos) == 1
        assert infos[0].has_tool_results is True
        assert infos[0].has_subagents is True

    def test_missing_storage_returns_empty(self, tmp_path):
        with (
            patch.object(core, "PROJECTS_DIR", tmp_path / "projects"),
            patch.object(core, "encode_path", lambda _: "missing"),
        ):
            assert inspect.gather_session_info("/x") == []


class TestSelectLastN:
    def test_returns_n_newest(self, tmp_path):
        projects = tmp_path / "projects"
        storage = projects / "encoded"
        storage.mkdir(parents=True)
        for i, name in enumerate(["a", "b", "c"]):
            f = storage / f"{name}.jsonl"
            f.write_text("{}")
            os.utime(f, (time.time() - (10 - i) * 10, time.time() - (10 - i) * 10))

        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "encode_path", lambda _: "encoded"),
        ):
            assert inspect.select_last_n_sessions("/x", 2) == ["c", "b"]


class TestFormatSize:
    def test_bytes(self):
        assert inspect.format_size(0) == "0B"
        assert inspect.format_size(512) == "512B"
        assert inspect.format_size(1023) == "1023B"

    def test_kilobytes(self):
        assert inspect.format_size(1024) == "1.0KB"
        assert inspect.format_size(2048) == "2.0KB"

    def test_megabytes(self):
        assert inspect.format_size(2 * 1024 * 1024) == "2.0MB"

    def test_gigabytes(self):
        assert inspect.format_size(3 * 1024**3) == "3.0GB"
