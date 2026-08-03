"""运维模块 — 架构管理 + 指南管理 + 验证引擎."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ════════════════════════════════════
# 架构管理 (architecture)
# ════════════════════════════════════

class ArchitectureManager:
    """架构审计: 自动发现 Agent + 资产 + 导出报告。"""

    def __init__(self, project_root: str | Path = "."):
        self.root = Path(project_root)

    def audit(self) -> dict[str, Any]:
        """扫描项目发现所有 Agent 和资产。"""
        report: dict[str, Any] = {"agents": {}, "assets": {}, "quality": {}}

        # 发现 Agent
        yaml_dir = self.root / "packages" / "haip-hospital" / "agents" / "definitions"
        if yaml_dir.exists():
            import yaml
            for f in sorted(yaml_dir.glob("*.yaml")):
                if f.name.startswith("_"):
                    continue
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                report["agents"][data["name"]] = {
                    "type": data.get("type"), "tools": len(data.get("tools", [])),
                    "port": data.get("port", 0), "file": str(f.relative_to(self.root)),
                }

        # 发现资产
        knowledge = self.root / "packages" / "haip-hospital" / "knowledge"
        if knowledge.exists():
            for cat in os.listdir(knowledge):
                cat_path = knowledge / cat
                if cat_path.is_dir():
                    count = sum(1 for _ in cat_path.rglob("*") if _.is_file())
                    report["assets"][cat] = count

        # 质量检查
        from haip.agent import list_all
        agents = list_all()
        report["quality"]["registered_agents"] = len(agents)
        report["quality"]["yaml_agents"] = len(report["agents"])
        report["quality"]["consistent"] = len(agents) == len(report["agents"])

        return report

    def show(self) -> str:
        """生成架构报告文本。"""
        report = self.audit()
        lines = ["=" * 50, "  xhaip Architecture Report", "=" * 50,
                 f"\n  Registered Agents: {report['quality']['registered_agents']}",
                 f"  YAML-defined Agents: {report['quality']['yaml_agents']}",
                 f"  Consistent: {report['quality']['consistent']}",
                 "\n  Assets:"]
        for cat, count in report["assets"].items():
            lines.append(f"    {cat}: {count} files")
        return "\n".join(lines)

    def export(self) -> dict[str, Any]:
        """导出完整架构 JSON。"""
        return self.audit()


# ════════════════════════════════════
# 指南管理 (guidelines)
# ════════════════════════════════════

class GuidelinesManager:
    """指南索引: 加载 + 搜索 + 验证。"""

    def __init__(self, guides_dir: str | Path = ""):
        self.index: dict[str, dict] = {}
        if guides_dir:
            self.load(Path(guides_dir))

    def load(self, directory: Path):
        if not directory.exists():
            return
        for f in directory.glob("*.yaml"):
            try:
                import yaml
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "id" in data:
                    self.index[data["id"]] = {
                        "name": data.get("name", ""), "publisher": data.get("publisher", ""),
                        "trust_level": data.get("trust_level", "T2"), "file": str(f),
                    }
            except (OSError, yaml.YAMLError) as exc:
                logger.warning("跳过无法解析的指南 YAML %s: %s", f, exc)

    def search(self, keyword: str) -> list[dict]:
        kw = keyword.lower()
        return [v for v in self.index.values()
                if kw in v["name"].lower() or kw in v.get("publisher", "").lower()]

    def count_by_level(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for v in self.index.values():
            tl = v["trust_level"]
            counts[tl] = counts.get(tl, 0) + 1
        return counts


# ════════════════════════════════════
# 验证引擎 (validate)
# ════════════════════════════════════

def validate_agents(host: str = "127.0.0.1") -> dict[str, Any]:
    """验证 Agent 端口 + 模块 + YAML 一致性。"""
    issues: list[str] = []
    ports: dict[int, str] = {}
    agent_status: dict[str, Any] = {}

    from haip.agent import list_all
    agents = list_all()

    for name, p in agents.items():
        status = "ok"
        if p.port:
            if p.port in ports:
                issues.append(f"端口冲突: {name}({p.port}) vs {ports[p.port]}({p.port})")
                status = "port_conflict"
            ports[p.port] = name
        agent_status[name] = {"port": p.port, "type": p.type, "tools": len(p.tools), "status": status}

    return {"valid": len(issues) == 0, "issues": issues, "agents": agent_status, "total": len(agents)}


def validate_modules() -> dict[str, Any]:
    """验证 handler 模块是否可导入。"""
    issues: list[str] = []
    ok_count = 0

    from haip.agent import list_all
    for name, p in list_all().items():
        for t in p.tools:
            try:
                import importlib
                mod_name, func_name = t.handler.rsplit(".", 1)
                importlib.import_module(mod_name)
                ok_count += 1
            except Exception as e:
                issues.append(f"{name}/{t.name}: {e}")

    return {"valid": len(issues) == 0, "issues": issues, "ok_count": ok_count,
            "total": sum(len(p.tools) for p in list_all().values())}
