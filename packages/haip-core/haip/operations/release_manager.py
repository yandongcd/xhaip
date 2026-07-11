"""Release & Baseline Manager — backup, release listing, rollback.

Port of ``agents/harness/release.py`` from v0.2.0, adapted for xhaip v1.0.

Backup targets:
  - Agent definitions (YAML)
  - Modules (Python handlers)
  - Knowledge base (YAML guidelines/rules)
  - Configuration (config/*.yaml)

Usage::

    from haip.operations.release_manager import ReleaseManager

    rm = ReleaseManager()
    rm.backup("v1.2")
    rm.list()
    rm.rollback("v1.2")
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _find_project_root() -> Path:
    """Walk up from this file to find the xhaip project root.

    The xhaip monorepo root contains both ``packages/`` and ``pyproject.toml``.
    We walk up until we find a parent that has a ``packages`` subdirectory,
    which distinguishes the monorepo root from individual package dirs.
    """
    d = Path(__file__).resolve().parent
    for _ in range(10):
        if (d / "packages").is_dir():
            return d
        if d.parent == d:
            break
        d = d.parent
    return Path.cwd()


def _git(*args: str) -> str:
    """Run a git command and return stripped stdout, or empty string on failure."""
    try:
        r = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(_find_project_root()),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except FileNotFoundError:
        return ""


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _date_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class ReleaseManager:
    """Manage project backups, listing, and rollback."""

    def __init__(self, releases_dir: str | Path | None = None):
        if releases_dir is None:
            releases_dir = _find_project_root() / "releases"
        self.root = Path(releases_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.project_root = _find_project_root()
        self._tracked_cache: set[str] | None = None

    # ── Backups ─────────────────────────────────────────────────────

    def _get_tracked_files(self) -> set[str]:
        if self._tracked_cache is None:
            out = _git("ls-files")
            self._tracked_cache = set(out.splitlines()) if out else set()
        return self._tracked_cache

    def _walk_target_dirs(self) -> dict[str, dict[str, str]]:
        """Walk agent definitions, modules, knowledge, config directories."""
        roots = [
            self.project_root / "agents" / "definitions",
            self.project_root / "agents" / "modules",
            self.project_root / "agents" / "knowledge",
            self.project_root / "config",
        ]
        # Also include haip-hospital package if present
        hospital = self.project_root / "packages" / "haip-hospital"
        if hospital.exists():
            roots.append(hospital / "agents" / "definitions")
            roots.append(hospital / "agents" / "modules")
            roots.append(hospital / "agents" / "knowledge")

        files: dict[str, dict[str, str]] = {}
        for root_dir in roots:
            if not root_dir.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(str(root_dir)):
                dirnames[:] = [d for d in dirnames if d not in {"__pycache__", ".git"}]
                for fn in filenames:
                    abspath = Path(dirpath) / fn
                    try:
                        rel = str(abspath.relative_to(self.project_root))
                        files[rel] = {
                            "hash": _hash_file(abspath),
                            "size": str(abspath.stat().st_size),
                        }
                    except (OSError, ValueError):
                        pass
        return files

    def _should_skip_copy(self, rel: str, size_bytes: int) -> bool:
        if size_bytes > 10 * 1024 * 1024:
            return True
        skip_exts = {".pdf", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png", ".zip"}
        return Path(rel).suffix.lower() in skip_exts

    def create_backup(self, label: str = "") -> dict[str, Any]:
        """Create a full backup snapshot of agent definitions, modules, knowledge, and config.

        Returns backup metadata dict with ``id``, ``timestamp``, ``files``.
        """
        date = _date_stamp()
        backup_id = f"{date}-{label}" if label else date
        dst = self.root / backup_id

        if dst.exists():
            backup_id = f"{backup_id}-{int(time.time())}"
            dst = self.root / backup_id

        dst.mkdir(parents=True, exist_ok=True)

        tracked = self._get_tracked_files()
        git_info: dict[str, Any] = {
            "backup_id": backup_id,
            "date": date,
            "timestamp": _now_iso(),
            "files": {},
        }

        commit_line = _git("log", "-1", "--format=%H|%s|%an|%ai")
        if commit_line:
            parts = commit_line.split("|", 3)
            git_info["commit"] = parts[0] if len(parts) > 0 else ""
            git_info["message"] = parts[1] if len(parts) > 1 else ""
            git_info["author"] = parts[2] if len(parts) > 2 else ""
            git_info["author_date"] = parts[3] if len(parts) > 3 else ""

        branch = _git("branch", "--show-current")
        if branch:
            git_info["branch"] = branch

        for rel, meta in self._walk_target_dirs().items():
            abspath = self.project_root / rel
            sz = int(meta.get("size", 0))
            if rel in tracked:
                meta["source"] = "git"
                git_info["files"][rel] = meta
            elif self._should_skip_copy(rel, sz):
                meta["source"] = "hash-only"
                git_info["files"][rel] = meta
            else:
                meta["source"] = "copy"
                meta["path"] = rel
                git_info["files"][rel] = meta
                copy_dst = dst / rel
                copy_dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(str(abspath), str(copy_dst))
                except (OSError, shutil.Error):
                    pass

        manifest_path = dst / "backup.json"
        manifest_path.write_text(
            json.dumps(git_info, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return git_info

    # ── Listing ─────────────────────────────────────────────────────

    def list_backups(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent backups with summary info."""
        if not self.root.exists():
            return []

        entries = sorted(
            (p for p in self.root.iterdir() if p.is_dir() and (p / "backup.json").exists()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        results = []
        for p in entries[:limit]:
            try:
                mf = json.loads((p / "backup.json").read_text(encoding="utf-8"))
                total = len(mf.get("files", {}))
                copied = sum(1 for v in mf["files"].values() if v.get("source") == "copy")
                results.append({
                    "backup_id": mf.get("backup_id", p.name),
                    "date": mf.get("date", ""),
                    "commit": (mf.get("commit", "") or "")[:12],
                    "message": (mf.get("message", "") or "")[:60],
                    "author": mf.get("author", ""),
                    "branch": mf.get("branch", ""),
                    "total_files": total,
                    "git_files": total - copied,
                    "copied_files": copied,
                })
            except (json.JSONDecodeError, OSError):
                pass
        return results

    # ── Rollback ────────────────────────────────────────────────────

    def rollback(self, backup_id: str) -> dict[str, Any]:
        """Restore project files from a backup.

        Returns a dict with ``success``, ``restored``, ``skipped``, ``errors``.
        """
        src = self.root / backup_id
        manifest_path = src / "backup.json"

        if not manifest_path.exists():
            return {
                "success": False,
                "error": f"Backup {backup_id} not found",
                "restored": [],
                "skipped": [],
                "errors": [f"not found: {backup_id}"],
            }

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest.get("files", {})
        restored: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []

        for rel, meta in files.items():
            abspath = self.project_root / rel
            abspath.parent.mkdir(parents=True, exist_ok=True)
            source = meta.get("source", "git")

            try:
                if source == "git":
                    r = _git("checkout", "--", rel)
                    if r:
                        restored.append(f"{rel} (git)")
                    else:
                        errors.append(f"{rel}: git checkout failed")
                elif source == "copy":
                    copy_src = src / rel
                    if copy_src.exists():
                        shutil.copy2(str(copy_src), str(abspath))
                        restored.append(f"{rel} (copy)")
                    else:
                        skipped.append(f"{rel}: no snapshot file")
                else:
                    skipped.append(f"{rel}: hash-only (no content)")
            except Exception as e:
                errors.append(f"{rel}: {e}")

        return {
            "success": len(errors) == 0,
            "restored": restored,
            "skipped": skipped,
            "errors": errors,
        }

    # ── Info ────────────────────────────────────────────────────────

    def info(self, backup_id: str) -> dict[str, Any] | None:
        """Return full manifest for a backup."""
        mf = self.root / backup_id / "backup.json"
        if mf.exists():
            return json.loads(mf.read_text(encoding="utf-8"))
        return None
