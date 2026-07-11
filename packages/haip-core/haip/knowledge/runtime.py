"""知识库运行时 — 启动自动同步 + 运行时查询 + 热更新.

整合 knowledge/guidelines + knowledge/rules + knowledge/guideline_sources
三个目录的 YAML 资产, 启动时自动同步到 SQLite, 提供毫秒级查询接口。
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from haip.knowledge import KnowledgeStore
from haip.guard.citation import Citation, CitationEngine


class KnowledgeRuntime:
    """知识库运行时: YAML → SQLite 同步 + 查询 + 热更新.

    用法:
        kb = KnowledgeRuntime(project_root)
        kb.sync()                    # 启动时同步
        kb.find_rules("cardiac_delay")  # 毫秒级查询
        kb.search_guidelines("NICE")    # 搜索指南
        kb.stats()                      # 统计信息
        kb.start_hot_reload()           # 启动文件监控 (30s 轮询)
        kb.force_resync()               # 手动强制重载
    """

    def __init__(self, project_root: str | Path = "."):
        self.root = Path(project_root)
        self.store = KnowledgeStore(":memory:")

        # 路径推断
        hospital = self.root / "packages" / "haip-hospital"
        if not hospital.exists():
            hospital = self.root  # fallback

        self.guidelines_dir = hospital / "knowledge" / "guidelines"
        self.rules_dir = hospital / "knowledge" / "rules"
        self.sources_dir = hospital / "knowledge" / "guideline_sources"

        # Citation 引擎 (用于 Guard 验证)
        self.citation_engine = CitationEngine()
        if self.guidelines_dir.exists():
            self.citation_engine.index_guidelines(self.guidelines_dir)

        self._synced = False

        # ── 热更新 ──
        self.hot_reload_enabled = False
        self._watcher_thread: threading.Thread | None = None
        self._watcher_stop = threading.Event()
        self._poll_interval = 30.0  # seconds
        self._file_mtimes: dict[str, float] = {}

    def sync(self) -> dict[str, int]:
        """从 YAML 目录同步到 SQLite。启动时调用一次。"""
        stats = self.store.sync_from_dir(
            guidelines_dir=self.guidelines_dir if self.guidelines_dir.exists() else None,
            rules_dir=self.rules_dir if self.rules_dir.exists() else None,
        )
        self._synced = True
        return stats

    def resync(self) -> dict[str, int]:
        """热重载: 清空数据后重新同步。"""
        self.store.close()
        self.store = KnowledgeStore(":memory:")
        self._file_mtimes = self._build_file_snapshot()
        return self.sync()

    def force_resync(self) -> dict[str, int]:
        """强制重载: agent 可调用此方法手动刷新知识库。

        Returns:
            与 sync() 同格式的统计 dict。
        """
        return self.resync()

    # ── 热更新文件监控 ──

    def start_hot_reload(self, poll_interval: float = 30.0) -> None:
        """启动后台文件监控线程，定期检查 YAML 变更并自动重载。

        Args:
            poll_interval: 轮询间隔 (秒)，默认 30s。
        """
        if self.hot_reload_enabled:
            return
        self.hot_reload_enabled = True
        self._poll_interval = poll_interval
        self._watcher_stop.clear()
        self._file_mtimes = self._build_file_snapshot()
        self._watcher_thread = threading.Thread(
            target=self._watch_loop, daemon=True, name="kb-hot-reload"
        )
        self._watcher_thread.start()

    def stop_hot_reload(self) -> None:
        """停止热更新监控线程。"""
        self.hot_reload_enabled = False
        self._watcher_stop.set()
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=5.0)
        self._watcher_thread = None

    def _build_file_snapshot(self) -> dict[str, float]:
        """扫描所有 YAML 文件，返回 {path: mtime} 快照。"""
        snapshot: dict[str, float] = {}
        for d in (self.guidelines_dir, self.rules_dir):
            if d.exists():
                for path in d.rglob("*.yaml"):
                    if path.name in ("registry.yaml", "conflict_policy.yaml"):
                        continue
                    try:
                        snapshot[str(path)] = os.path.getmtime(path)
                    except OSError:
                        pass
        return snapshot

    def _check_for_changes(self) -> list[str]:
        """检查文件快照是否变更，返回变更文件列表。"""
        changed: list[str] = []
        current = self._build_file_snapshot()

        # 检查新增/修改
        for path_str, mtime in current.items():
            prev = self._file_mtimes.get(path_str)
            if prev is None or mtime > prev:
                changed.append(path_str)

        # 检查删除
        for path_str in self._file_mtimes:
            if path_str not in current:
                changed.append(path_str)

        return changed

    def _watch_loop(self) -> None:
        """后台轮询线程：每 poll_interval 秒检查 YAML 文件变更。"""
        while not self._watcher_stop.is_set():
            self._watcher_stop.wait(timeout=self._poll_interval)
            if self._watcher_stop.is_set():
                break
            try:
                changed = self._check_for_changes()
                if changed:
                    self.resync()
            except Exception:
                pass

    # ── 查询接口 ──

    def find_rules(self, decision_point: str) -> list[dict[str, Any]]:
        if not self._synced:
            self.sync()
        return self.store.find_rules(decision_point)

    def search_guidelines(self, keyword: str) -> list[dict[str, Any]]:
        if not self._synced:
            self.sync()
        return self.store.search_guidelines(keyword)

    def get_guideline(self, gid: str) -> dict[str, Any] | None:
        if not self._synced:
            self.sync()
        return self.store.get_guideline(gid)

    def count_by_trust_level(self) -> dict[str, int]:
        if not self._synced:
            self.sync()
        return self.store.count_by_trust_level()

    def verify_citations(self, text: str, domain: str = "") -> list[Citation]:
        """提取引文并验证 (用于 Guard 运行时)。"""
        citations = self.citation_engine.extract(text)
        return self.citation_engine.verify(citations)

    def stats(self) -> dict[str, Any]:
        if not self._synced:
            self.sync()
        return {
            "guidelines": self.store.count_by_trust_level(),
            "total_rules": self.store.count_rules(),
            "synced": self._synced,
        }

    def close(self):
        self.stop_hot_reload()
        self.store.close()


# 全局单例
_kb_runtime: KnowledgeRuntime | None = None


def get_kb(project_root: str | Path = ".") -> KnowledgeRuntime:
    """获取全局单例 KnowledgeRuntime。"""
    global _kb_runtime
    if _kb_runtime is None:
        _kb_runtime = KnowledgeRuntime(project_root)
        _kb_runtime.sync()
    return _kb_runtime


def reset_kb():
    """重置全局 KnowledgeRuntime (测试用)。"""
    global _kb_runtime
    if _kb_runtime:
        _kb_runtime.close()
    _kb_runtime = None
