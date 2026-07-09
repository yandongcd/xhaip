"""知识库运行时 — 启动自动同步 + 运行时查询 + 热更新.

整合 knowledge/guidelines + knowledge/rules + knowledge/guideline_sources
三个目录的 YAML 资产, 启动时自动同步到 SQLite, 提供毫秒级查询接口。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from haip.knowledge import KnowledgeStore
from haip.guard.citation import Citation, CitationEngine


class KnowledgeRuntime:
    """知识库运行时: YAML → SQLite 同步 + 查询 + 热更新。

    用法:
        kb = KnowledgeRuntime(project_root)
        kb.sync()                    # 启动时同步
        kb.find_rules("cardiac_delay")  # 毫秒级查询
        kb.search_guidelines("NICE")    # 搜索指南
        kb.stats()                      # 统计信息
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
        return self.sync()

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
