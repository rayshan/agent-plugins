"""Tests for link-claude-project."""

import json
from pathlib import Path
from unittest.mock import patch

# Import from the script
import importlib.util

spec = importlib.util.spec_from_file_location(
    "reconnect",
    Path(__file__).parent / "link-claude-project.py",
)
reconnect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconnect)
State = reconnect.State


class TestEncodePath:
    def test_simple_path(self):
        assert reconnect.encode_path("/Users/me/project") == "-Users-me-project"

    def test_spaces(self):
        assert (
            reconnect.encode_path("/Users/me/My Documents") == "-Users-me-My-Documents"
        )

    def test_tildes(self):
        assert (
            reconnect.encode_path("/Users/me/com~apple~CloudDocs")
            == "-Users-me-com-apple-CloudDocs"
        )

    def test_equals(self):
        assert (
            reconnect.encode_path("/Users/me/=Projects=/foo")
            == "-Users-me--Projects--foo"
        )

    def test_underscores(self):
        assert (
            reconnect.encode_path("/Users/me/_private-repo")
            == "-Users-me--private-repo"
        )

    def test_icloud_path(self):
        path = "/Users/ray.shan/Library/Mobile Documents/com~apple~CloudDocs/Carta/AI/Prompts - agent behavior"
        expected = "-Users-ray-shan-Library-Mobile-Documents-com-apple-CloudDocs-Carta-AI-Prompts---agent-behavior"
        assert reconnect.encode_path(path) == expected

    def test_adjacent_special_chars(self):
        # "Prompts - agent" has space-dash-space -> three dashes
        assert reconnect.encode_path("/a - b") == "-a---b"


class TestDetectState:
    """Cover every branch of detect_state by laying out a fake projects dir."""

    def _setup(self, tmp_path, *, old_disk, new_disk, old_enc, new_enc):
        old_disk_dir = tmp_path / "old-disk"
        new_disk_dir = tmp_path / "new-disk"
        if old_disk:
            old_disk_dir.mkdir()
        if new_disk:
            new_disk_dir.mkdir()

        projects = tmp_path / "projects"
        projects.mkdir()
        old_path_str = str(old_disk_dir)
        new_path_str = str(new_disk_dir)
        if old_enc:
            (projects / reconnect.encode_path(old_path_str)).mkdir()
        if new_enc:
            (projects / reconnect.encode_path(new_path_str)).mkdir()
        return projects, old_path_str, new_path_str

    def test_identical(self, tmp_path):
        with patch.object(reconnect, "PROJECTS_DIR", tmp_path / "projects"):
            assert reconnect.detect_state("/a", "/a") is State.IDENTICAL

    def test_already_linked(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=False, new_disk=True, old_enc=False, new_enc=True
        )
        with patch.object(reconnect, "PROJECTS_DIR", projects):
            assert reconnect.detect_state(old, new) is State.ALREADY_LINKED

    def test_old_storage_missing(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=True, new_disk=False, old_enc=False, new_enc=False
        )
        with patch.object(reconnect, "PROJECTS_DIR", projects):
            assert reconnect.detect_state(old, new) is State.OLD_STORAGE_MISSING

    def test_target_storage_occupied(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=True, new_disk=True, old_enc=True, new_enc=True
        )
        with patch.object(reconnect, "PROJECTS_DIR", projects):
            assert reconnect.detect_state(old, new) is State.TARGET_STORAGE_OCCUPIED

    def test_ambiguous(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=True, new_disk=True, old_enc=True, new_enc=False
        )
        with patch.object(reconnect, "PROJECTS_DIR", projects):
            assert reconnect.detect_state(old, new) is State.AMBIGUOUS

    def test_both_disk_missing(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=False, new_disk=False, old_enc=True, new_enc=False
        )
        with patch.object(reconnect, "PROJECTS_DIR", projects):
            assert reconnect.detect_state(old, new) is State.BOTH_DISK_MISSING

    def test_needs_disk_rename(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=True, new_disk=False, old_enc=True, new_enc=False
        )
        with patch.object(reconnect, "PROJECTS_DIR", projects):
            assert reconnect.detect_state(old, new) is State.NEEDS_DISK_RENAME

    def test_relink_only(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=False, new_disk=True, old_enc=True, new_enc=False
        )
        with patch.object(reconnect, "PROJECTS_DIR", projects):
            assert reconnect.detect_state(old, new) is State.RELINK_ONLY


class TestRenameDiskDir:
    def test_renames_directory(self, tmp_path):
        old = tmp_path / "old"
        new = tmp_path / "new"
        old.mkdir()
        (old / "file.txt").write_text("hi")

        result = reconnect.rename_disk_dir(str(old), str(new), dry_run=False)

        assert result is True
        assert not old.exists()
        assert (new / "file.txt").read_text() == "hi"

    def test_dry_run_does_not_rename(self, tmp_path):
        old = tmp_path / "old"
        new = tmp_path / "new"
        old.mkdir()

        result = reconnect.rename_disk_dir(str(old), str(new), dry_run=True)

        assert result is True
        assert old.exists()
        assert not new.exists()

    def test_old_missing(self, tmp_path):
        old = tmp_path / "missing"
        new = tmp_path / "new"
        assert reconnect.rename_disk_dir(str(old), str(new), dry_run=False) is False

    def test_new_already_exists(self, tmp_path):
        old = tmp_path / "old"
        new = tmp_path / "new"
        old.mkdir()
        new.mkdir()
        assert reconnect.rename_disk_dir(str(old), str(new), dry_run=False) is False
        assert old.exists()
        assert new.exists()

    def test_parent_of_new_missing(self, tmp_path):
        old = tmp_path / "old"
        new = tmp_path / "missing-parent" / "new"
        old.mkdir()
        assert reconnect.rename_disk_dir(str(old), str(new), dry_run=False) is False
        assert old.exists()


class TestRenameStorageDir:
    def test_renames_directory(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        old_dir = projects / "old-encoded"
        old_dir.mkdir()
        (old_dir / "session.jsonl").write_text("{}")

        with patch.object(reconnect, "PROJECTS_DIR", projects):
            result = reconnect.rename_storage_dir(
                "old-encoded", "new-encoded", dry_run=False
            )

        assert result is True
        assert not old_dir.exists()
        assert (projects / "new-encoded" / "session.jsonl").exists()

    def test_dry_run_does_not_rename(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        old_dir = projects / "old-encoded"
        old_dir.mkdir()

        with patch.object(reconnect, "PROJECTS_DIR", projects):
            result = reconnect.rename_storage_dir(
                "old-encoded", "new-encoded", dry_run=True
            )

        assert result is True
        assert old_dir.exists()
        assert not (projects / "new-encoded").exists()

    def test_old_dir_missing(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()

        with patch.object(reconnect, "PROJECTS_DIR", projects):
            result = reconnect.rename_storage_dir(
                "nonexistent", "new-encoded", dry_run=False
            )

        assert result is False

    def test_new_dir_already_exists(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        (projects / "old-encoded").mkdir()
        (projects / "new-encoded").mkdir()

        with patch.object(reconnect, "PROJECTS_DIR", projects):
            result = reconnect.rename_storage_dir(
                "old-encoded", "new-encoded", dry_run=False
            )

        assert result is False
        # Both dirs still exist, nothing was destroyed
        assert (projects / "old-encoded").exists()
        assert (projects / "new-encoded").exists()


class TestUpdateHistory:
    def _write_history(self, path: Path, entries: list[dict]) -> None:
        path.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n",
            encoding="utf-8",
        )

    def test_updates_matching_entries(self, tmp_path):
        history = tmp_path / "history.jsonl"
        entries = [
            {"display": "msg1", "project": "/old/path", "sessionId": "aaa"},
            {"display": "msg2", "project": "/other/path", "sessionId": "bbb"},
            {"display": "msg3", "project": "/old/path", "sessionId": "aaa"},
        ]
        self._write_history(history, entries)

        with patch.object(reconnect, "HISTORY_FILE", history):
            changed = reconnect.update_history("/old/path", "/new/path", dry_run=False)

        assert changed == 2
        lines = history.read_text(encoding="utf-8").strip().splitlines()
        assert json.loads(lines[0])["project"] == "/new/path"
        assert json.loads(lines[1])["project"] == "/other/path"
        assert json.loads(lines[2])["project"] == "/new/path"

    def test_creates_backup(self, tmp_path):
        history = tmp_path / "history.jsonl"
        entries = [{"display": "msg", "project": "/old/path", "sessionId": "a"}]
        self._write_history(history, entries)

        with patch.object(reconnect, "HISTORY_FILE", history):
            reconnect.update_history("/old/path", "/new/path", dry_run=False)

        backup = history.with_suffix(".jsonl.bak")
        assert backup.exists()
        # Backup has original content
        original = json.loads(backup.read_text(encoding="utf-8").strip())
        assert original["project"] == "/old/path"

    def test_dry_run_does_not_modify(self, tmp_path):
        history = tmp_path / "history.jsonl"
        entries = [{"display": "msg", "project": "/old/path", "sessionId": "a"}]
        self._write_history(history, entries)
        original_content = history.read_text(encoding="utf-8")

        with patch.object(reconnect, "HISTORY_FILE", history):
            changed = reconnect.update_history("/old/path", "/new/path", dry_run=True)

        assert changed == 1
        assert history.read_text(encoding="utf-8") == original_content
        assert not history.with_suffix(".jsonl.bak").exists()

    def test_no_matching_entries(self, tmp_path):
        history = tmp_path / "history.jsonl"
        entries = [{"display": "msg", "project": "/other/path", "sessionId": "a"}]
        self._write_history(history, entries)

        with patch.object(reconnect, "HISTORY_FILE", history):
            changed = reconnect.update_history("/old/path", "/new/path", dry_run=False)

        assert changed == 0

    def test_ignores_substring_match_in_other_fields(self, tmp_path):
        """Display text or other fields that contain the old path must NOT be rewritten."""
        history = tmp_path / "history.jsonl"
        entries = [
            {
                "display": "Use /link to rename /old/path to /new/path",
                "project": "/unrelated/dir",
                "sessionId": "a",
            },
        ]
        self._write_history(history, entries)

        with patch.object(reconnect, "HISTORY_FILE", history):
            changed = reconnect.update_history("/old/path", "/new/path", dry_run=False)

        assert changed == 0
        line = json.loads(history.read_text(encoding="utf-8").strip())
        assert line["display"] == "Use /link to rename /old/path to /new/path"
        assert line["project"] == "/unrelated/dir"

    def test_preserves_non_json_lines(self, tmp_path):
        history = tmp_path / "history.jsonl"
        history.write_text(
            '{"display":"msg","project":"/old/path","sessionId":"a"}\nnot-json-line\n',
            encoding="utf-8",
        )

        with patch.object(reconnect, "HISTORY_FILE", history):
            changed = reconnect.update_history("/old/path", "/new/path", dry_run=False)

        assert changed == 1
        lines = history.read_text(encoding="utf-8").strip().splitlines()
        assert lines[1] == "not-json-line"

    def test_preserves_unicode(self, tmp_path):
        history = tmp_path / "history.jsonl"
        entries = [{"display": "café résumé", "project": "/old/path", "sessionId": "a"}]
        self._write_history(history, entries)

        with patch.object(reconnect, "HISTORY_FILE", history):
            reconnect.update_history("/old/path", "/new/path", dry_run=False)

        line = json.loads(history.read_text(encoding="utf-8").strip().splitlines()[0])
        assert line["display"] == "café résumé"
