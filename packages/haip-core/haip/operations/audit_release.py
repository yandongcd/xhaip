"""运维模块 — 审计 + 发布管理."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any


# ════════════════════════════════════
# 审计引擎 (audit)
# ════════════════════════════════════

class AuditEngine:
    """Agent 执行审计: 快照 / 差异对比 / 回滚。"""

    def __init__(self, storage_dir: str | Path = ".audit"):
        self.storage = Path(storage_dir)
        self.storage.mkdir(exist_ok=True)

    def snapshot(self, label: str = "") -> dict[str, Any]:
        """生成当前 Agent 状态快照。"""
        from haip.agent import list_all
        agents = list_all()
        snap = {
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
        path.write_text(json.dumps(snap, ensure_ascii=False, indent=2))
        return snap

    def list_snapshots(self) -> list[dict[str, str]]:
        result = []
        for f in sorted(self.storage.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text())
                result.append({"id": data.get("id", ""), "label": data.get("label", ""),
                              "timestamp": data.get("timestamp", ""), "agents": len(data.get("agents", {}))})
            except Exception:
                pass
        return result

    def diff(self, snap1: str, snap2: str) -> dict[str, Any]:
        """对比两个快照的差异。"""
        d1 = json.loads((self.storage / f"{snap1}.json").read_text())
        d2 = json.loads((self.storage / f"{snap2}.json").read_text())
        a1, a2 = d1["agents"], d2["agents"]
        changes = {"added": [], "removed": [], "modified": []}
        for name in set(a1) | set(a2):
            if name not in a2:
                changes["removed"].append(name)
            elif name not in a1:
                changes["added"].append(name)
            elif a1[name] != a2[name]:
                changes["modified"].append(name)
        return changes

    def rollback(self, snapshot_id: str, target_dir: str | Path) -> bool:
        """从快照恢复。"""
        snap_path = self.storage / f"{snapshot_id}.json"
        if not snap_path.exists():
            return False
        snap = json.loads(snap_path.read_text())
        backup = Path(target_dir) / f"pre_rollback_{snapshot_id}.json"
        backup.write_text(json.dumps(snap, ensure_ascii=False, indent=2))
        return True


# ════════════════════════════════════
# 发布管理 (release)
# ════════════════════════════════════

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
        manifest = {"version": ver, "timestamp": datetime.now().isoformat(), "agents": {}}
        for name, p in agents.items():
            manifest["agents"][name] = {"type": p.type, "version": p.version, "tools": len(p.tools)}
        (backup_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        return manifest

    def list_releases(self) -> list[dict[str, str]]:
        result = []
        for d in sorted(self.releases.glob("backup-*"), reverse=True):
            mf = d / "manifest.json"
            if mf.exists():
                data = json.loads(mf.read_text())
                result.append({"version": data["version"], "timestamp": data["timestamp"],
                              "agents": len(data.get("agents", {}))})
        return result

    def notes(self, version: str) -> dict[str, Any]:
        """获取发布说明。"""
        mf = self.releases / f"backup-{version}" / "manifest.json"
        if mf.exists():
            return json.loads(mf.read_text())
        return {"error": f"Release {version} not found"}

    def rollback(self, version: str) -> bool:
        """回滚到指定版本。"""
        return (self.releases / f"backup-{version}").exists()


# ════════════════════════════════════
# 执行日志 (journal)
# ════════════════════════════════════

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
        events = {}
        for e in self.entries:
            ev = e["event"]
            events[ev] = events.get(ev, 0) + 1
        return {"total_entries": len(self.entries), "agents": sorted(agents),
                "events": events}

    def clear(self):
        self.entries = []
