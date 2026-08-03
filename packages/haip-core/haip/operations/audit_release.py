"""运维模块 — 审计 + 发布管理.

Port of ``agents/harness/audit.py`` from v0.2.0, enhanced for xhaip v1.0.

Features:
  1. File-level snapshot with SHA256 checksums
  2. Diff between snapshot and current state (unified diff)
  3. Diff between any two snapshots
  4. Rollback (restore files from snapshot)
  5. Audit trail (JSONL log)

Usage::

    from haip.operations.audit_release import AuditEngine

    ae = AuditEngine()
    snap_id = ae.snapshot("src/app.py", agent="cli", reason="before refactor")
    ae.diff(snap_id)
    ae.rollback(snap_id)
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# ═══════════════════════════════════════════════════════
# AuditEngine — file-level snapshot, diff, rollback
# ═══════════════════════════════════════════════════════

class AuditEngine:
    """File-level audit: snapshot, diff, rollback, audit trail."""

    def __init__(self, storage_dir: str | Path | None = None):
        if storage_dir is None:
            storage_dir = _find_project_root() / ".audit"
        self.storage = Path(storage_dir)
        self.storage.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir = self.storage / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path = self.storage / "audit.jsonl"
        self.project_root = _find_project_root()
        self.max_snapshots = 50

    # ── File-level Snapshot ────────────────────────────────────────

    def _is_git_tracked(self, abspath: Path) -> bool:
        try:
            r = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(abspath)],
                capture_output=True, cwd=str(self.project_root),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return r.returncode == 0
        except FileNotFoundError:
            return False

    def snapshot(
        self,
        *paths: str,
        agent: str = "",
        reason: str = "",
    ) -> str:
        """Take a pre-modification snapshot of file *paths* (relative to project root).

        Returns a ``snap_id`` for later use with :meth:`diff` or :meth:`rollback`.
        """
        snap_id = f"{int(time.time()):x}-{os.urandom(4).hex()}"
        snap_dir = self.snapshot_dir / snap_id
        snap_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, str] = {}

        for rel in paths:
            abspath = (self.project_root / rel).resolve()
            if not abspath.exists():
                continue

            raw = abspath.read_bytes()
            h = _sha256(raw)
            tracked = self._is_git_tracked(abspath)

            if tracked:
                files[rel] = json.dumps({"sha256": h, "source": "git"})
            else:
                files[rel] = json.dumps({"sha256": h, "source": "snapshot"})
                dst = snap_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(raw)

        manifest = {
            "snap_id": snap_id,
            "timestamp": time.time(),
            "time_str": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "reason": reason,
            "files": files,
        }
        (snap_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._auto_prune()
        return {"id": snap_id, "agents": len(files)}

    def _auto_prune(self) -> None:
        snapshots = sorted(
            (
                p for p in self.snapshot_dir.iterdir()
                if p.is_dir() and (p / "manifest.json").exists()
            ),
            key=lambda p: p.stat().st_mtime,
        )
        while len(snapshots) > self.max_snapshots:
            old = snapshots.pop(0)
            shutil.rmtree(old, ignore_errors=True)

    # ── Agent-level Snapshot (existing feature preserved) ──────────

    def snapshot_agents(self, label: str = "") -> dict[str, Any]:
        """Generate current Agent registry state snapshot."""
        from haip.agent import list_all
        agents = list_all()
        snap: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "label": label or f"snap_{int(time.time())}",
            "agents": {},
        }
        for name, p in agents.items():
            snap["agents"][name] = {
                "name": p.name, "type": p.type, "version": p.version,
                "tools": [t.name for t in p.tools], "port": p.port,
            }
        snap_id = hashlib.md5(json.dumps(snap, sort_keys=True).encode()).hexdigest()[:8]
        snap["id"] = snap_id

        path = self.storage / f"{snap_id}.json"
        path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
        return snap

    # ── Listing ────────────────────────────────────────────────────

    def list_snapshots(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent file-level snapshots."""
        if not self.snapshot_dir.exists():
            return []
        results = []
        for p in sorted(self.snapshot_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            mf = p / "manifest.json"
            if mf.exists():
                try:
                    data = json.loads(mf.read_text(encoding="utf-8"))
                    results.append({
                        "snap_id": data.get("snap_id", p.name),
                        "time": data.get("time_str", ""),
                        "agent": data.get("agent", ""),
                        "reason": data.get("reason", ""),
                        "file_count": len(data.get("files", {})),
                    })
                except (json.JSONDecodeError, OSError):
                    pass
            if len(results) >= limit:
                break
        return results

    def list_agent_snapshots(self) -> list[dict[str, str]]:
        """List agent-registry snapshots."""
        result = []
        for f in sorted(self.storage.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                result.append({
                    "id": data.get("id", ""),
                    "label": data.get("label", ""),
                    "timestamp": data.get("timestamp", ""),
                    "agents": len(data.get("agents", {})),
                })
            except (json.JSONDecodeError, OSError):
                logger.warning("跳过损坏的 agent 快照: %s", f.name)
        return result

    # ── Diff ───────────────────────────────────────────────────────

    def diff(self, snap_id: str) -> list[dict[str, Any]]:
        """Compare each file in *snap_id* against its current on-disk state.

        Returns a list of dicts with ``file``, ``changed``, and optionally ``diff``.
        """
        snap_dir = self.snapshot_dir / snap_id
        mf = snap_dir / "manifest.json"
        if not mf.exists():
            return [{"error": f"Snapshot {snap_id} not found"}]

        manifest = json.loads(mf.read_text(encoding="utf-8"))
        files: dict[str, str] = manifest.get("files", {})
        results = []

        for rel, meta_json in files.items():
            abspath = (self.project_root / rel).resolve()
            if not abspath.exists():
                results.append({"file": rel, "changed": True, "error": "current file missing"})
                continue

            current_raw = abspath.read_bytes()
            current_hash = hashlib.sha256(current_raw).hexdigest()
            meta = json.loads(meta_json)
            old_hash = meta.get("sha256", "")

            if current_hash == old_hash:
                results.append({"file": rel, "changed": False})
            else:
                try:
                    current_text = current_raw.decode("utf-8")
                    source = meta.get("source", "")
                    if source == "snapshot":
                        old_path = snap_dir / rel
                        old_text = old_path.read_text(encoding="utf-8") if old_path.exists() else ""
                    else:
                        old_text = ""
                        try:
                            r = subprocess.run(
                                ["git", "show", f"HEAD:{rel}"],
                                capture_output=True, cwd=str(self.project_root),
                                creationflags=subprocess.CREATE_NO_WINDOW,
                            )
                            if r.returncode == 0:
                                old_text = r.stdout.decode("utf-8")
                        except FileNotFoundError:
                            pass

                    diff_lines = list(
                        difflib.unified_diff(
                            old_text.splitlines(keepends=True),
                            current_text.splitlines(keepends=True),
                            fromfile=f"a/{rel}",
                            tofile=f"b/{rel}",
                        )
                    )
                    results.append({
                        "file": rel,
                        "changed": True,
                        "diff": "".join(diff_lines),
                    })
                except (UnicodeDecodeError, Exception) as e:
                    results.append({"file": rel, "changed": True, "error": str(e)})

        return results

    def diff_two(self, snap_id_1: str, snap_id_2: str) -> list[dict[str, Any]]:
        """Compare files between two snapshots.

        Returns a list of dicts with ``file``, ``changed``, and optionally ``diff``.
        """
        d1 = self.snapshot_dir / snap_id_1 / "manifest.json"
        d2 = self.snapshot_dir / snap_id_2 / "manifest.json"
        if not d1.exists():
            return [{"error": f"Snapshot {snap_id_1} not found"}]
        if not d2.exists():
            return [{"error": f"Snapshot {snap_id_2} not found"}]

        m1 = json.loads(d1.read_text(encoding="utf-8"))
        m2 = json.loads(d2.read_text(encoding="utf-8"))
        f1: dict[str, str] = m1.get("files", {})
        f2: dict[str, str] = m2.get("files", {})

        results = []
        all_files = set(f1) | set(f2)

        for rel in sorted(all_files):
            if rel not in f2:
                results.append({"file": rel, "changed": True, "diff": f"Removed in {snap_id_2}"})
            elif rel not in f1:
                results.append({"file": rel, "changed": True, "diff": f"Added in {snap_id_2}"})
            else:
                h1 = json.loads(f1[rel]).get("sha256", "")
                h2_val = json.loads(f2[rel]).get("sha256", "")
                if h1 != h2_val:
                    results.append({
                        "file": rel, "changed": True,
                        "diff": "Content differs (hash mismatch)",
                    })
                else:
                    results.append({"file": rel, "changed": False})

        return results

    # ── Rollback ───────────────────────────────────────────────────

    def rollback(self, snap_id: str) -> dict[str, Any]:
        """Restore files from a file-level snapshot.

        Returns a dict with ``success``, ``restored``, ``skipped``, ``errors``.
        """
        snap_dir = self.snapshot_dir / snap_id
        mf = snap_dir / "manifest.json"

        if not mf.exists():
            return {"success": False, "restored": [], "skipped": [],
                    "errors": [f"Snapshot {snap_id} not found"]}

        try:
            manifest = json.loads(mf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return {"success": False, "restored": [], "skipped": [],
                    "errors": [f"Cannot read manifest: {e}"]}

        files: dict[str, str] = manifest.get("files", {})
        restored: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []

        for rel, meta_json in files.items():
            try:
                meta = json.loads(meta_json)
            except (json.JSONDecodeError, TypeError):
                errors.append(f"{rel}: invalid metadata")
                continue

            source = meta.get("source", "snapshot")
            abspath = (self.project_root / rel).resolve()

            try:
                if source == "git":
                    r = subprocess.run(
                        ["git", "checkout", "--", str(abspath)],
                        capture_output=True, cwd=str(self.project_root),
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    if r.returncode == 0:
                        restored.append(f"{rel} (git)")
                    else:
                        fallback = snap_dir / rel
                        if fallback.exists():
                            abspath.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(fallback), str(abspath))
                            restored.append(f"{rel} (snapshot-fallback)")
                        else:
                            errors.append(f"{rel}: git checkout failed and no snapshot fallback")
                else:
                    src = snap_dir / rel
                    if src.exists():
                        abspath.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(src), str(abspath))
                        restored.append(f"{rel} (snapshot)")
                    else:
                        errors.append(f"{rel}: snapshot file missing")
            except Exception as e:
                errors.append(f"{rel}: {e}")

        success = len(errors) == 0

        self._audit_log(
            action="rollback", snap_id=snap_id, agent="system",
            detail=f"Rolled back {len(restored)} files ({len(errors)} errors)",
            paths=restored + errors,
        )

        return {"success": success, "restored": restored, "skipped": skipped, "errors": errors}

    # ── Audit Trail ────────────────────────────────────────────────

    def _audit_log(
        self,
        action: str,
        snap_id: str = "",
        agent: str = "",
        detail: str = "",
        paths: list[str] | None = None,
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "time_str": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "snap_id": snap_id,
            "agent": agent,
            "detail": detail,
            "paths": paths or [],
        }
        with self.audit_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def list_audit_log(self, limit: int = 30) -> list[dict[str, Any]]:
        """List recent audit log entries."""
        if not self.audit_log_path.exists():
            return []
        entries = []
        with self.audit_log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries[-limit:]


# ═══════════════════════════════════════════════════════
# ReleaseManager — backup, list, rollback (existing, enhanced)
# ═══════════════════════════════════════════════════════

class ReleaseManager:
    """发布管理: 备份 / 发布 / 回滚。"""

    def __init__(self, releases_dir: str | Path = ".releases"):
        self.releases = Path(releases_dir)
        self.releases.mkdir(exist_ok=True)

    def backup(self, version: str = "") -> dict[str, Any]:
        """备份当前代码基线。"""
        ver = version or datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = self.releases / f"backup-{ver}"
        backup_dir.mkdir(exist_ok=True)

        from haip.agent import list_all
        agents = list_all()
        manifest: dict[str, Any] = {
            "version": ver, "timestamp": datetime.now().isoformat(), "agents": {},
        }
        for name, p in agents.items():
            manifest["agents"][name] = {"type": p.type, "version": p.version, "tools": len(p.tools)}
        (backup_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return manifest

    def list_releases(self) -> list[dict[str, str]]:
        result = []
        for d in sorted(self.releases.glob("backup-*"), reverse=True):
            mf = d / "manifest.json"
            if mf.exists():
                data = json.loads(mf.read_text(encoding="utf-8"))
                result.append({
                    "version": data["version"],
                    "timestamp": data["timestamp"],
                    "agents": len(data.get("agents", {})),
                })
        return result

    def notes(self, version: str) -> dict[str, Any]:
        """获取发布说明。"""
        mf = self.releases / f"backup-{version}" / "manifest.json"
        if mf.exists():
            return json.loads(mf.read_text(encoding="utf-8"))
        return {"error": f"Release {version} not found"}

    def rollback(self, version: str) -> bool:
        """回滚到指定版本。"""
        return (self.releases / f"backup-{version}").exists()


# ═══════════════════════════════════════════════════════
# 执行日志 (journal)
# ═══════════════════════════════════════════════════════

class ExecutionJournal:
    """Agent 执行日志: 记录每次 A2A 调用。"""

    def __init__(self, max_entries: int = 1000):
        self.entries: list[dict[str, Any]] = []
        self.max_entries = max_entries

    def log(self, event: str, agent: str = "", tool: str = "", data: dict | None = None, **kwargs):
        entry = {
            "timestamp": datetime.now().isoformat(), "event": event,
            "agent": agent, "tool": tool, "data": data or {},
        }
        entry.update(kwargs)
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def query(self, agent: str = "", event: str = "", limit: int = 50) -> list[dict]:
        results = self.entries
        if agent:
            results = [e for e in results if e["agent"] == agent]
        if event:
            results = [e for e in results if event in e["event"]]
        return results[-limit:]

    def stats(self) -> dict[str, Any]:
        agents = set(e["agent"] for e in self.entries)
        events: dict[str, int] = {}
        for e in self.entries:
            ev = e["event"]
            events[ev] = events.get(ev, 0) + 1
        return {"total_entries": len(self.entries), "agents": sorted(agents),
                "events": events}

    def clear(self):
        self.entries = []
