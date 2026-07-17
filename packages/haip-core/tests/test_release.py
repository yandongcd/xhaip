"""Tests for haip.operations.release_manager."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))


@patch("haip.operations.release_manager._find_project_root")
@patch("haip.operations.release_manager._git")
class TestCreateBackup:
    """Tests for ReleaseManager.create_backup()."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        yield
        self.tmpdir.cleanup()

    def test_create_backup_with_label(self, mock_git, mock_find_root):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)
        mock_find_root.return_value = root
        mock_git.return_value = ""
        (root / "agents" / "definitions").mkdir(parents=True)
        (root / "agents" / "definitions" / "test_agent.yaml").write_text("name: test\n", encoding="utf-8")
        (root / "config").mkdir(parents=True)
        (root / "config" / "test.yaml").write_text("key: value\n", encoding="utf-8")

        rm = ReleaseManager(releases_dir=str(root / "releases"))
        result = rm.create_backup(label="v1.0")

        assert "backup_id" in result
        assert "v1.0" in result["backup_id"]
        assert "timestamp" in result
        assert "files" in result
        assert len(result["files"]) > 0
        assert (root / "releases" / result["backup_id"] / "backup.json").exists()

    def test_create_backup_without_label(self, mock_git, mock_find_root):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)
        mock_find_root.return_value = root
        mock_git.return_value = ""

        rm = ReleaseManager(releases_dir=str(root / "releases"))
        result = rm.create_backup()

        assert "backup_id" in result
        assert "timestamp" in result
        assert isinstance(result["files"], dict)

    def test_create_backup_duplicate_label_generates_unique_id(self, mock_git, mock_find_root):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)
        mock_find_root.return_value = root
        mock_git.return_value = ""

        rm = ReleaseManager(releases_dir=str(root / "releases"))
        r1 = rm.create_backup(label="dup")
        r2 = rm.create_backup(label="dup")

        assert r1["backup_id"] != r2["backup_id"]
        assert "dup" in r1["backup_id"]
        assert "dup" in r2["backup_id"]

    def test_backup_includes_git_info(self, mock_git, mock_find_root):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)
        mock_find_root.return_value = root

        def git_side_effect(*args):
            if len(args) >= 2 and args[0] == "log":
                return "abc123|test commit|dev|2026-01-01"
            if args[0] == "branch":
                return "main"
            return ""

        mock_git.side_effect = git_side_effect

        rm = ReleaseManager(releases_dir=str(root / "releases"))
        result = rm.create_backup(label="git-test")

        assert result.get("commit") == "abc123"
        assert result.get("message") == "test commit"
        assert result.get("author") == "dev"
        assert result.get("branch") == "main"


class TestListBackups:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        yield
        self.tmpdir.cleanup()

    def test_empty_when_no_backups(self):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)
        rm = ReleaseManager(releases_dir=str(root / "releases"))
        result = rm.list_backups()
        assert result == []

    def test_lists_backups_after_creation(self):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)

        with patch("haip.operations.release_manager._find_project_root", return_value=root):
            with patch("haip.operations.release_manager._git", return_value=""):
                rm = ReleaseManager(releases_dir=str(root / "releases"))
                rm.create_backup(label="b1")
                rm.create_backup(label="b2")

        rm2 = ReleaseManager(releases_dir=str(root / "releases"))
        backups = rm2.list_backups()
        assert len(backups) == 2
        for b in backups:
            assert "backup_id" in b
            assert "date" in b
            assert "total_files" in b


@patch("haip.operations.release_manager._find_project_root")
@patch("haip.operations.release_manager._git")
class TestRollback:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        yield
        self.tmpdir.cleanup()

    def test_rollback_nonexistent_backup(self, mock_git, mock_find_root):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)
        mock_find_root.return_value = root

        rm = ReleaseManager(releases_dir=str(root / "releases"))
        result = rm.rollback("nonexistent-backup")
        assert result["success"] is False
        assert "error" in result
        assert "nonexistent-backup" in result["error"]
        assert result["restored"] == []

    def test_rollback_restores_copied_files(self, mock_git, mock_find_root):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)
        mock_find_root.return_value = root
        mock_git.return_value = ""

        (root / "agents" / "definitions").mkdir(parents=True)
        test_file = root / "agents" / "definitions" / "agent_test.yaml"
        test_file.write_text("name: test-agent\nversion: '1.0'\n", encoding="utf-8")

        rm = ReleaseManager(releases_dir=str(root / "releases"))
        backup_info = rm.create_backup(label="rollback-test")

        test_file.write_text("name: test-agent\nversion: '2.0-changed'\n", encoding="utf-8")

        mock_git.reset_mock()
        result = rm.rollback(backup_info["backup_id"])

        assert "success" in result
        assert len(result.get("restored", [])) > 0, "回滚应恢复至少一个文件"


class TestInfo:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        yield
        self.tmpdir.cleanup()

    def test_info_nonexistent_backup_returns_none(self):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)
        rm = ReleaseManager(releases_dir=str(root / "releases"))
        result = rm.info("nonexistent")
        assert result is None

    def test_info_returns_manifest_for_existing_backup(self):
        from haip.operations.release_manager import ReleaseManager

        root = Path(self.tmpdir.name)

        with patch("haip.operations.release_manager._find_project_root", return_value=root):
            with patch("haip.operations.release_manager._git", return_value=""):
                rm = ReleaseManager(releases_dir=str(root / "releases"))
                backup_info = rm.create_backup(label="info-test")

        rm2 = ReleaseManager(releases_dir=str(root / "releases"))
        info = rm2.info(backup_info["backup_id"])
        assert info is not None
        assert info["backup_id"] == backup_info["backup_id"]
        assert "files" in info
        assert "timestamp" in info
