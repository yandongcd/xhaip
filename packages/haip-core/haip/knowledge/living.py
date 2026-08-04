"""存活知识库 (B4) — 指南/规则版本监控 + 变更影响分析 + agent 自动重验证.

检测: 指南 YAML version 字段变化 → 受影响的规则 → 使用该规则的 agent → 自动重验证.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_KNOWLEDGE_BASE = Path(__file__).resolve().parents[4] / "packages" / "haip-hospital" / "knowledge"
_GUIDELINES_DIR = _KNOWLEDGE_BASE / "guidelines"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@dataclass
class VersionChange:
    """指南版本变更记录."""
    guideline_id: str
    guideline_name: str
    old_version: str
    new_version: str
    affected_rules: list[str] = field(default_factory=list)
    affected_agents: list[str] = field(default_factory=list)
    action: str = "review"  # review / revalidate / unchanged


def _current_snapshot() -> dict[str, dict[str, str]]:
    """当前指南 YAML 的快照 {fname: {version, hash}}."""
    snap: dict[str, dict[str, str]] = {}
    if not _GUIDELINES_DIR.is_dir():
        return snap
    import yaml
    for f in sorted(_GUIDELINES_DIR.glob("*.yaml")):
        if f.name.startswith("_"):
            continue
        try:
            with open(f, encoding="utf-8") as fh:
                raw = fh.read()
                data = yaml.safe_load(raw)
            ver = str(data.get("version", "") or data.get("last_updated", ""))
            snap[f.name] = {"version": ver, "hash": _sha256(raw)}
        except Exception:
            continue
    return snap


def _load_snapshot(snapshot_file: str = "") -> dict[str, dict[str, str]]:
    """从持久化文件加载上次快照."""
    path = Path(snapshot_file) if snapshot_file else (_KNOWLEDGE_BASE / ".guideline_snapshot.json")
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_snapshot(snapshot: dict[str, dict[str, str]], snapshot_file: str = "") -> None:
    path = Path(snapshot_file) if snapshot_file else (_KNOWLEDGE_BASE / ".guideline_snapshot.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def _find_affected_rules(guideline_id: str) -> list[str]:
    """通过 KG 查找受指南变更影响的规则."""
    try:
        from haip.kg import get_kg_store
        store = get_kg_store()
        rels = []
        with store._lock:
            conn = store._get_conn()
            rows = conn.execute(
                "SELECT target_id FROM kg_relations WHERE relation_type='guides' AND source_id = ?",
                [guideline_id],
            ).fetchall()
            rels = [r["target_id"] for r in rows]
        return rels[:20]
    except Exception:
        return []


def check_guideline_changes(snapshot_file: str = "") -> list[VersionChange]:
    """检查指南版本变更.

    比较当前 YAML 状态与上次快照, 识别:
    - 新增/删除 (hash 变化)
    - 版本升级 (version 字段变化)
    - 受影响的规则 + agent

    返回变更清单供人工审核或自动重验证.
    """
    current = _current_snapshot()
    previous = _load_snapshot(snapshot_file)

    changes: list[VersionChange] = []

    for fname, cur in current.items():
        prev = previous.get(fname, {})
        if not prev:
            changes.append(VersionChange(
                guideline_id=fname,
                guideline_name=fname.replace(".yaml", "").replace("guideline-", ""),
                old_version="-", new_version=cur["version"],
                action="new_guideline",
            ))
            continue
        if cur["hash"] != prev.get("hash", ""):
            gname = fname.replace(".yaml", "").replace("guideline-", "")
            affected = _find_affected_rules(fname)
            changes.append(VersionChange(
                guideline_id=fname,
                guideline_name=gname,
                old_version=prev.get("version", "?"),
                new_version=cur["version"],
                affected_rules=affected,
                action="revalidate" if affected else "review",
            ))

    return changes


@dataclass
class AgentRevalidationResult:
    """Agent 重新验证结果."""
    agent_name: str
    tools_revalidated: int = 0
    tools_failed: int = 0
    errors: list[str] = field(default_factory=list)


def revalidate_agents_for_guideline(guideline_id: str) -> list[AgentRevalidationResult]:
    """指南变更后, 重新验证受影响的 agent 工具.

    当前实现: 做了一次快速导入验证 (handler 可导入), 不做全量 LLM 推理.
    """
    affected_rules = _find_affected_rules(guideline_id)
    if not affected_rules:
        return []

    results: list[AgentRevalidationResult] = []
    try:
        from haip.a2a import call
        from haip.agent import list_all
        for agent_name, plugin in list_all().items():
            failed = 0
            passed = 0
            for rule_id in affected_rules[:3]:  # 最多验证 3 条规则
                # 快速验证: 找匹配的工具名并调用
                for tool in plugin.tools:
                    if rule_id in tool.description or rule_id in tool.name:
                        try:
                            call(agent_name, tool.name, {})
                            passed += 1
                        except Exception:
                            failed += 1
            if passed or failed:
                results.append(AgentRevalidationResult(
                    agent_name=agent_name,
                    tools_revalidated=passed,
                    tools_failed=failed,
                ))
    except Exception:
        pass

    return results


def update_snapshot(snapshot_file: str = "") -> dict[str, float]:
    """更新快照到磁盘. 返回 {guidelines_updated, agents_revalidated}."""
    current = _current_snapshot()
    _save_snapshot(current, snapshot_file)

    # 检查变更
    changes = check_guideline_changes(snapshot_file)
    agents_revalidated = 0
    for c in changes:
        if c.action == "revalidate":
            results = revalidate_agents_for_guideline(c.guideline_id)
            agents_revalidated += len(results)

    return {
        "guidelines_scanned": len(current),
        "guidelines_changed": len([c for c in changes if c.action != "unchanged"]),
        "agents_revalidated": agents_revalidated,
    }
