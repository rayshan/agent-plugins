"""Tests for lcp.core."""

import json
from pathlib import Path
from unittest.mock import patch

from lcp import core


class TestEncodePath:
    def test_simple_path(self):
        assert core.encode_path("/Users/me/project") == "-Users-me-project"

    def test_spaces(self):
        assert core.encode_path("/Users/me/My Documents") == "-Users-me-My-Documents"

    def test_tildes(self):
        assert (
            core.encode_path("/Users/me/com~apple~CloudDocs")
            == "-Users-me-com-apple-CloudDocs"
        )

    def test_equals(self):
        assert (
            core.encode_path("/Users/me/=Projects=/foo") == "-Users-me--Projects--foo"
        )

    def test_underscores(self):
        assert core.encode_path("/Users/me/_private-repo") == "-Users-me--private-repo"

    def test_icloud_path(self):
        path = "/Users/ray.shan/Library/Mobile Documents/com~apple~CloudDocs/Carta/AI/Prompts - agent behavior"
        expected = "-Users-ray-shan-Library-Mobile-Documents-com-apple-CloudDocs-Carta-AI-Prompts---agent-behavior"
        assert core.encode_path(path) == expected

    def test_adjacent_special_chars(self):
        assert core.encode_path("/a - b") == "-a---b"


class TestActiveSessionIds:
    def test_collects_session_ids(self, tmp_path):
        sessions = tmp_path / "sessions"
        sessions.mkdir()
        (sessions / "1234.json").write_text(
            json.dumps({"pid": 1234, "sessionId": "uuid-a"}), encoding="utf-8"
        )
        (sessions / "5678.json").write_text(
            json.dumps({"pid": 5678, "sessionId": "uuid-b"}), encoding="utf-8"
        )
        with patch.object(core, "SESSIONS_DIR", sessions):
            assert core.active_session_ids() == {"uuid-a", "uuid-b"}

    def test_skips_malformed(self, tmp_path):
        sessions = tmp_path / "sessions"
        sessions.mkdir()
        (sessions / "1.json").write_text("not-json", encoding="utf-8")
        (sessions / "2.json").write_text(
            json.dumps({"sessionId": "ok"}), encoding="utf-8"
        )
        with patch.object(core, "SESSIONS_DIR", sessions):
            assert core.active_session_ids() == {"ok"}

    def test_missing_dir(self, tmp_path):
        with patch.object(core, "SESSIONS_DIR", tmp_path / "missing"):
            assert core.active_session_ids() == set()


def _write_history(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


class TestUpdateHistory:
    def test_updates_matching_entries(self, tmp_path):
        history = tmp_path / "history.jsonl"
        _write_history(
            history,
            [
                {"display": "m1", "project": "/old/path", "sessionId": "aaa"},
                {"display": "m2", "project": "/other/path", "sessionId": "bbb"},
                {"display": "m3", "project": "/old/path", "sessionId": "aaa"},
            ],
        )
        with patch.object(core, "HISTORY_FILE", history):
            changed = core.update_history("/old/path", "/new/path", dry_run=False)
        assert changed == 2
        lines = history.read_text(encoding="utf-8").strip().splitlines()
        assert json.loads(lines[0])["project"] == "/new/path"
        assert json.loads(lines[1])["project"] == "/other/path"
        assert json.loads(lines[2])["project"] == "/new/path"

    def test_session_ids_filter(self, tmp_path):
        history = tmp_path / "history.jsonl"
        _write_history(
            history,
            [
                {"display": "m1", "project": "/old/path", "sessionId": "keep"},
                {"display": "m2", "project": "/old/path", "sessionId": "skip"},
                {"display": "m3", "project": "/old/path", "sessionId": "keep"},
            ],
        )
        with patch.object(core, "HISTORY_FILE", history):
            changed = core.update_history(
                "/old/path", "/new/path", dry_run=False, session_ids={"keep"}
            )
        assert changed == 2
        lines = history.read_text(encoding="utf-8").strip().splitlines()
        assert json.loads(lines[0])["project"] == "/new/path"
        assert json.loads(lines[1])["project"] == "/old/path"
        assert json.loads(lines[2])["project"] == "/new/path"

    def test_session_ids_filter_empty_set(self, tmp_path):
        history = tmp_path / "history.jsonl"
        _write_history(
            history, [{"display": "m1", "project": "/old/path", "sessionId": "aaa"}]
        )
        with patch.object(core, "HISTORY_FILE", history):
            assert (
                core.update_history(
                    "/old/path", "/new/path", dry_run=False, session_ids=set()
                )
                == 0
            )

    def test_creates_backup(self, tmp_path):
        history = tmp_path / "history.jsonl"
        _write_history(
            history, [{"display": "msg", "project": "/old/path", "sessionId": "a"}]
        )
        with patch.object(core, "HISTORY_FILE", history):
            core.update_history("/old/path", "/new/path", dry_run=False)
        backup = history.with_suffix(".jsonl.bak")
        assert backup.exists()
        assert (
            json.loads(backup.read_text(encoding="utf-8").strip())["project"]
            == "/old/path"
        )

    def test_dry_run_does_not_modify(self, tmp_path):
        history = tmp_path / "history.jsonl"
        _write_history(
            history, [{"display": "msg", "project": "/old/path", "sessionId": "a"}]
        )
        original = history.read_text(encoding="utf-8")
        with patch.object(core, "HISTORY_FILE", history):
            assert core.update_history("/old/path", "/new/path", dry_run=True) == 1
        assert history.read_text(encoding="utf-8") == original
        assert not history.with_suffix(".jsonl.bak").exists()

    def test_no_matching_entries(self, tmp_path):
        history = tmp_path / "history.jsonl"
        _write_history(
            history, [{"display": "msg", "project": "/other/path", "sessionId": "a"}]
        )
        with patch.object(core, "HISTORY_FILE", history):
            assert core.update_history("/old/path", "/new/path", dry_run=False) == 0

    def test_ignores_substring_match_in_other_fields(self, tmp_path):
        history = tmp_path / "history.jsonl"
        _write_history(
            history,
            [
                {
                    "display": "Use /link to rename /old/path to /new/path",
                    "project": "/unrelated/dir",
                    "sessionId": "a",
                }
            ],
        )
        with patch.object(core, "HISTORY_FILE", history):
            assert core.update_history("/old/path", "/new/path", dry_run=False) == 0
        line = json.loads(history.read_text(encoding="utf-8").strip())
        assert line["project"] == "/unrelated/dir"

    def test_preserves_non_json_lines(self, tmp_path):
        history = tmp_path / "history.jsonl"
        history.write_text(
            '{"display":"msg","project":"/old/path","sessionId":"a"}\nnot-json-line\n',
            encoding="utf-8",
        )
        with patch.object(core, "HISTORY_FILE", history):
            core.update_history("/old/path", "/new/path", dry_run=False)
        lines = history.read_text(encoding="utf-8").strip().splitlines()
        assert lines[1] == "not-json-line"

    def test_preserves_unicode(self, tmp_path):
        history = tmp_path / "history.jsonl"
        _write_history(
            history,
            [{"display": "café résumé", "project": "/old/path", "sessionId": "a"}],
        )
        with patch.object(core, "HISTORY_FILE", history):
            core.update_history("/old/path", "/new/path", dry_run=False)
        line = json.loads(history.read_text(encoding="utf-8").strip().splitlines()[0])
        assert line["display"] == "café résumé"
