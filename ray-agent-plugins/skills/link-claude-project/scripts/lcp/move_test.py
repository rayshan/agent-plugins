"""Tests for lcp.move."""

import json
from pathlib import Path
from unittest.mock import patch

from lcp import core, move
from lcp.move import MoveState


class TestDetectMoveState:
    def _setup(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        sessions = tmp_path / "sessions"
        sessions.mkdir()
        src_disk = tmp_path / "src"
        dst_disk = tmp_path / "dst"
        src_disk.mkdir()
        dst_disk.mkdir()
        return projects, sessions, str(src_disk), str(dst_disk)

    def _make_storage(self, projects: Path, src_path: str, uuids: list[str]) -> Path:
        storage = projects / core.encode_path(src_path)
        storage.mkdir(parents=True, exist_ok=True)
        for u in uuids:
            (storage / f"{u}.jsonl").write_text("{}", encoding="utf-8")
        return storage

    def test_no_sessions(self, tmp_path):
        projects, sessions, src, dst = self._setup(tmp_path)
        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "SESSIONS_DIR", sessions),
        ):
            state, bad = move.detect_move_state(src, dst, [])
        assert state is MoveState.NO_SESSIONS_SELECTED
        assert bad == []

    def test_identical(self, tmp_path):
        projects, sessions, src, _ = self._setup(tmp_path)
        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "SESSIONS_DIR", sessions),
        ):
            state, _ = move.detect_move_state(src, src, ["uuid"])
        assert state is MoveState.SRC_DST_IDENTICAL

    def test_src_storage_missing(self, tmp_path):
        projects, sessions, src, dst = self._setup(tmp_path)
        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "SESSIONS_DIR", sessions),
        ):
            state, _ = move.detect_move_state(src, dst, ["uuid"])
        assert state is MoveState.SRC_STORAGE_MISSING

    def test_dst_disk_missing(self, tmp_path):
        projects, sessions, src, _ = self._setup(tmp_path)
        self._make_storage(projects, src, ["uuid"])
        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "SESSIONS_DIR", sessions),
        ):
            state, _ = move.detect_move_state(src, str(tmp_path / "missing"), ["uuid"])
        assert state is MoveState.DST_DISK_MISSING

    def test_session_not_found(self, tmp_path):
        projects, sessions, src, dst = self._setup(tmp_path)
        self._make_storage(projects, src, ["aaa"])
        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "SESSIONS_DIR", sessions),
        ):
            state, bad = move.detect_move_state(src, dst, ["aaa", "bbb"])
        assert state is MoveState.SESSION_NOT_FOUND
        assert bad == ["bbb"]

    def test_session_already_in_target(self, tmp_path):
        projects, sessions, src, dst = self._setup(tmp_path)
        self._make_storage(projects, src, ["aaa"])
        self._make_storage(projects, dst, ["aaa"])
        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "SESSIONS_DIR", sessions),
        ):
            state, bad = move.detect_move_state(src, dst, ["aaa"])
        assert state is MoveState.SESSION_ALREADY_IN_TARGET
        assert bad == ["aaa"]

    def test_active_session(self, tmp_path):
        projects, sessions, src, dst = self._setup(tmp_path)
        self._make_storage(projects, src, ["live-uuid"])
        (sessions / "1.json").write_text(
            json.dumps({"sessionId": "live-uuid"}), encoding="utf-8"
        )
        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "SESSIONS_DIR", sessions),
        ):
            state, bad = move.detect_move_state(src, dst, ["live-uuid"])
        assert state is MoveState.ACTIVE_SESSION
        assert bad == ["live-uuid"]

    def test_ok(self, tmp_path):
        projects, sessions, src, dst = self._setup(tmp_path)
        self._make_storage(projects, src, ["aaa"])
        with (
            patch.object(core, "PROJECTS_DIR", projects),
            patch.object(core, "SESSIONS_DIR", sessions),
        ):
            state, bad = move.detect_move_state(src, dst, ["aaa"])
        assert state is MoveState.OK
        assert bad == []


class TestMoveSessions:
    def _setup(self, tmp_path, src_uuids: list[str]) -> tuple[Path, str, str]:
        projects = tmp_path / "projects"
        projects.mkdir()
        src_dir = tmp_path / "src"
        dst_dir = tmp_path / "dst"
        src_dir.mkdir()
        dst_dir.mkdir()
        src_storage = projects / core.encode_path(str(src_dir))
        src_storage.mkdir()
        for u in src_uuids:
            (src_storage / f"{u}.jsonl").write_text(f"content-of-{u}", encoding="utf-8")
        return projects, str(src_dir), str(dst_dir)

    def test_moves_jsonl_only(self, tmp_path):
        projects, src, dst = self._setup(tmp_path, ["aaa"])
        with patch.object(core, "PROJECTS_DIR", projects):
            assert move.move_sessions(src, dst, ["aaa"], dry_run=False) is True
        src_storage = projects / core.encode_path(src)
        dst_storage = projects / core.encode_path(dst)
        assert not (src_storage / "aaa.jsonl").exists()
        assert (dst_storage / "aaa.jsonl").read_text() == "content-of-aaa"

    def test_creates_dst_storage_if_missing(self, tmp_path):
        projects, src, dst = self._setup(tmp_path, ["aaa"])
        dst_storage = projects / core.encode_path(dst)
        assert not dst_storage.exists()
        with patch.object(core, "PROJECTS_DIR", projects):
            move.move_sessions(src, dst, ["aaa"], dry_run=False)
        assert dst_storage.exists()

    def test_moves_per_session_subdir(self, tmp_path):
        projects, src, dst = self._setup(tmp_path, ["aaa"])
        src_storage = projects / core.encode_path(src)
        sub = src_storage / "aaa"
        (sub / "tool-results").mkdir(parents=True)
        (sub / "tool-results" / "x.txt").write_text("cached", encoding="utf-8")

        with patch.object(core, "PROJECTS_DIR", projects):
            move.move_sessions(src, dst, ["aaa"], dry_run=False)

        dst_storage = projects / core.encode_path(dst)
        assert (dst_storage / "aaa" / "tool-results" / "x.txt").read_text() == "cached"
        assert not sub.exists()

    def test_dry_run_does_not_modify(self, tmp_path):
        projects, src, dst = self._setup(tmp_path, ["aaa"])
        src_storage = projects / core.encode_path(src)
        with patch.object(core, "PROJECTS_DIR", projects):
            assert move.move_sessions(src, dst, ["aaa"], dry_run=True) is True
        assert (src_storage / "aaa.jsonl").exists()
        assert not (projects / core.encode_path(dst)).exists()

    def test_rollback_on_failure(self, tmp_path):
        """If a later move fails, prior moves in the batch are restored."""
        projects, src, dst = self._setup(tmp_path, ["aaa", "bbb"])
        src_storage = projects / core.encode_path(src)
        dst_storage = projects / core.encode_path(dst)
        dst_storage.mkdir()
        (dst_storage / "bbb.jsonl").write_text("collision", encoding="utf-8")

        with patch.object(core, "PROJECTS_DIR", projects):
            ok = move.move_sessions(src, dst, ["aaa", "bbb"], dry_run=False)

        assert ok is False
        assert (src_storage / "aaa.jsonl").read_text() == "content-of-aaa"
        assert not (dst_storage / "aaa.jsonl").exists()
        assert (dst_storage / "bbb.jsonl").read_text() == "collision"
        assert (src_storage / "bbb.jsonl").read_text() == "content-of-bbb"
