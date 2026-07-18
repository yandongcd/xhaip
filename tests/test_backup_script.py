"""备份脚本测试 — manifest / retain 修剪 / dry-run 不落盘."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import backup_db


class TestBackupScript:

    def test_backup_creates_manifest(self, tmp_path):
        """备份产生 manifest.json (文件/大小/sha256)."""
        root = tmp_path / "repo"
        root.mkdir()
        dummy_db = root / "xhaip.db"
        dummy_db.write_bytes(b"sqlite placeholder")

        data_dir = root / "data"
        data_dir.mkdir()
        (data_dir / "test.db").write_bytes(b"some data")

        pts_dir = root / "packages" / "haip-hospital" / "data"
        pts_dir.mkdir(parents=True)
        (pts_dir / "patients.json").write_text('{"patients":[]}', encoding="utf-8")

        backup_dir = backup_db.run_backup(root)
        assert backup_dir is not None
        assert backup_dir.is_dir()

        manifest_path = backup_dir / "manifest.json"
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        filenames = {f["filename"] for f in manifest["files"]}
        assert "xhaip.db" in filenames
        assert "test.db" in filenames
        assert "patients.json" in filenames
        assert manifest["timestamp"] == backup_dir.name

        for entry in manifest["files"]:
            assert isinstance(entry["size_bytes"], int)
            assert len(entry["sha256"]) == 64

    def test_retain_prunes_old_backups(self, tmp_path):
        """retain 修剪超出数量的旧备份."""
        root = tmp_path / "repo"
        root.mkdir()
        dummy_db = root / "xhaip.db"
        dummy_db.write_bytes(b"db")

        backup_root = root / "releases" / "backups"
        # 创建 5 份假备份
        for ts in ["20260101T000001Z", "20260102T000001Z", "20260103T000001Z",
                    "20260104T000001Z", "20260105T000001Z"]:
            d = backup_root / ts
            d.mkdir(parents=True)
            (d / "placeholder.txt").write_text(ts, encoding="utf-8")

        # 执行备份
        backup_db.run_backup(root)

        # 保留 3 份
        removed = backup_db.prune_backups(backup_root, retain=3)
        remaining = sorted([d.name for d in backup_root.iterdir() if d.is_dir()])

        assert len(removed) >= 1
        assert len(remaining) == 3

    def test_dry_run_does_not_create_files(self, tmp_path):
        """dry-run 不创建任何文件/目录."""
        root = tmp_path / "repo"
        root.mkdir()
        (root / "xhaip.db").write_bytes(b"db")

        before = set(
            str(p.relative_to(tmp_path))
            for p in tmp_path.rglob("*")
            if p.is_file() or p.is_dir()
        )
        backup_db.run_backup(root, dry_run=True)
        after = set(
            str(p.relative_to(tmp_path))
            for p in tmp_path.rglob("*")
            if p.is_file() or p.is_dir()
        )
        assert before == after

    def test_list_backups_shows_directories(self, tmp_path):
        """--list 列出已有备份."""
        root = tmp_path / "repo"
        root.mkdir()
        backup_root = root / "releases" / "backups"
        for ts in ["20260101T000001Z", "20260102T000001Z"]:
            (backup_root / ts).mkdir(parents=True)

        backups = backup_db.list_backups(backup_root)
        assert len(backups) == 2
        assert backups[0] > backups[1]  # 最新在前

    def test_no_files_returns_none(self, tmp_path):
        """无文件时返回 None."""
        root = tmp_path / "repo"
        root.mkdir()
        result = backup_db.run_backup(root)
        assert result is None
