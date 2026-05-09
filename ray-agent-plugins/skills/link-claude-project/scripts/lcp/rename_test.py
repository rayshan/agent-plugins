"""Tests for lcp.rename."""

from unittest.mock import patch

from lcp import core, rename
from lcp.rename import RenameState


class TestDetectRenameState:
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
            (projects / core.encode_path(old_path_str)).mkdir()
        if new_enc:
            (projects / core.encode_path(new_path_str)).mkdir()
        return projects, old_path_str, new_path_str

    def test_identical(self, tmp_path):
        with patch.object(core, "PROJECTS_DIR", tmp_path / "projects"):
            assert rename.detect_rename_state("/a", "/a") is RenameState.IDENTICAL

    def test_already_linked(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=False, new_disk=True, old_enc=False, new_enc=True
        )
        with patch.object(core, "PROJECTS_DIR", projects):
            assert rename.detect_rename_state(old, new) is RenameState.ALREADY_LINKED

    def test_old_storage_missing(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=True, new_disk=False, old_enc=False, new_enc=False
        )
        with patch.object(core, "PROJECTS_DIR", projects):
            assert (
                rename.detect_rename_state(old, new) is RenameState.OLD_STORAGE_MISSING
            )

    def test_target_storage_occupied(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=True, new_disk=True, old_enc=True, new_enc=True
        )
        with patch.object(core, "PROJECTS_DIR", projects):
            assert (
                rename.detect_rename_state(old, new)
                is RenameState.TARGET_STORAGE_OCCUPIED
            )

    def test_ambiguous(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=True, new_disk=True, old_enc=True, new_enc=False
        )
        with patch.object(core, "PROJECTS_DIR", projects):
            assert rename.detect_rename_state(old, new) is RenameState.AMBIGUOUS

    def test_both_disk_missing(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=False, new_disk=False, old_enc=True, new_enc=False
        )
        with patch.object(core, "PROJECTS_DIR", projects):
            assert rename.detect_rename_state(old, new) is RenameState.BOTH_DISK_MISSING

    def test_needs_disk_rename(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=True, new_disk=False, old_enc=True, new_enc=False
        )
        with patch.object(core, "PROJECTS_DIR", projects):
            assert rename.detect_rename_state(old, new) is RenameState.NEEDS_DISK_RENAME

    def test_relink_only(self, tmp_path):
        projects, old, new = self._setup(
            tmp_path, old_disk=False, new_disk=True, old_enc=True, new_enc=False
        )
        with patch.object(core, "PROJECTS_DIR", projects):
            assert rename.detect_rename_state(old, new) is RenameState.RELINK_ONLY


class TestRenameDiskDir:
    def test_renames_directory(self, tmp_path):
        old = tmp_path / "old"
        new = tmp_path / "new"
        old.mkdir()
        (old / "file.txt").write_text("hi")
        assert rename.rename_disk_dir(str(old), str(new), dry_run=False) is True
        assert not old.exists()
        assert (new / "file.txt").read_text() == "hi"

    def test_dry_run_does_not_rename(self, tmp_path):
        old = tmp_path / "old"
        new = tmp_path / "new"
        old.mkdir()
        assert rename.rename_disk_dir(str(old), str(new), dry_run=True) is True
        assert old.exists()
        assert not new.exists()

    def test_old_missing(self, tmp_path):
        assert (
            rename.rename_disk_dir(
                str(tmp_path / "missing"), str(tmp_path / "new"), dry_run=False
            )
            is False
        )

    def test_new_already_exists(self, tmp_path):
        old = tmp_path / "old"
        new = tmp_path / "new"
        old.mkdir()
        new.mkdir()
        assert rename.rename_disk_dir(str(old), str(new), dry_run=False) is False
        assert old.exists()
        assert new.exists()

    def test_parent_of_new_missing(self, tmp_path):
        old = tmp_path / "old"
        new = tmp_path / "missing-parent" / "new"
        old.mkdir()
        assert rename.rename_disk_dir(str(old), str(new), dry_run=False) is False
        assert old.exists()


class TestRenameStorageDir:
    def test_renames_directory(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        (projects / "old-encoded").mkdir()
        (projects / "old-encoded" / "session.jsonl").write_text("{}")

        with patch.object(core, "PROJECTS_DIR", projects):
            assert (
                rename.rename_storage_dir("old-encoded", "new-encoded", dry_run=False)
                is True
            )
        assert not (projects / "old-encoded").exists()
        assert (projects / "new-encoded" / "session.jsonl").exists()

    def test_dry_run_does_not_rename(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        (projects / "old-encoded").mkdir()
        with patch.object(core, "PROJECTS_DIR", projects):
            assert (
                rename.rename_storage_dir("old-encoded", "new-encoded", dry_run=True)
                is True
            )
        assert (projects / "old-encoded").exists()
        assert not (projects / "new-encoded").exists()

    def test_old_dir_missing(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        with patch.object(core, "PROJECTS_DIR", projects):
            assert (
                rename.rename_storage_dir("nonexistent", "new", dry_run=False) is False
            )

    def test_new_dir_already_exists(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        (projects / "old-encoded").mkdir()
        (projects / "new-encoded").mkdir()
        with patch.object(core, "PROJECTS_DIR", projects):
            assert (
                rename.rename_storage_dir("old-encoded", "new-encoded", dry_run=False)
                is False
            )
        assert (projects / "old-encoded").exists()
        assert (projects / "new-encoded").exists()
