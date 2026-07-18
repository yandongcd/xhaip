"""数据库备份脚本 — 纯 stdlib.

收集 xhaip.db + data/*.db + data/patients.json → releases/backups/<UTC 时间戳>/
输出 manifest.json (文件名/大小/sha256).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_and_manifest(src: Path, dest_dir: Path, manifest: list[dict]) -> None:
    if not src.is_file():
        return
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    st = src.stat()
    manifest.append({
        "filename": src.name,
        "size_bytes": st.st_size,
        "sha256": _sha256(dest),
    })


def collect_files(root: Path) -> list[Path]:
    """收集需备份的文件列表."""
    files: list[Path] = []

    db_path = root / "xhaip.db"
    if db_path.is_file():
        files.append(db_path)

    data_dir = root / "data"
    if data_dir.is_dir():
        for db_file in sorted(data_dir.glob("*.db")):
            files.append(db_file)

    patients_json = root / "packages" / "haip-hospital" / "data" / "patients.json"
    if patients_json.is_file():
        files.append(patients_json)

    return files


def list_backups(backup_root: Path) -> list[str]:
    """列出所有备份目录."""
    if not backup_root.is_dir():
        return []
    dirs = sorted(
        [d.name for d in backup_root.iterdir() if d.is_dir()],
        reverse=True,
    )
    return dirs


def prune_backups(backup_root: Path, retain: int) -> list[str]:
    """修剪过期备份, 返回被删除的目录名列表."""
    if not backup_root.is_dir():
        return []
    dirs = sorted(
        [d for d in backup_root.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    removed = []
    while len(dirs) > retain:
        d = dirs.pop(0)
        shutil.rmtree(d)
        removed.append(d.name)
    return removed


def run_backup(root: Path, dry_run: bool = False) -> Path | None:
    """执行备份, 返回备份目录路径 (dry-run 时返回 None)."""
    files = collect_files(root)
    if not files:
        print("没有发现可备份的文件.", file=sys.stderr)
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = root / "releases" / "backups" / timestamp

    if dry_run:
        print(f"[DRY-RUN] 将备份到: {backup_dir}")
        for f in files:
            print(f"  {f.relative_to(root)} ({f.stat().st_size} bytes)")
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for f in files:
        _copy_and_manifest(f, backup_dir, manifest)

    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({
            "timestamp": timestamp,
            "source_root": str(root.resolve()),
            "files": manifest,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"备份完成: {backup_dir} (共 {len(manifest)} 文件)")
    return backup_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="xhaip 数据库备份工具")
    parser.add_argument("--root", type=Path, default=None,
                        help="仓库根路径 (默认: 脚本所在仓库根)")
    parser.add_argument("--retain", type=int, default=7,
                        help="保留最近 N 份备份 (默认 7)")
    parser.add_argument("--list", action="store_true",
                        help="列出已有备份")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览而不实际执行")
    args = parser.parse_args()

    root = args.root if args.root else Path(__file__).resolve().parent.parent
    backup_root = root / "releases" / "backups"

    if args.list:
        backups = list_backups(backup_root)
        if backups:
            for b in backups:
                print(b)
        else:
            print("暂无备份.")
        return

    if args.dry_run:
        run_backup(root, dry_run=True)
        return

    result = run_backup(root)
    if result is None:
        sys.exit(1)

    removed = prune_backups(backup_root, args.retain)
    if removed:
        for r in removed:
            print(f"已修剪旧备份: {r}")


if __name__ == "__main__":
    main()
