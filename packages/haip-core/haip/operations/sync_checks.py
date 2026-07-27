"""运维模块 — Skill同步 + 系统检查 + 基准测试 + 输出格式."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

# ════════════════════════════════════
# Skill 同步 (sync_skills)
# ════════════════════════════════════

class SkillSync:
    """Skill 源 → 运行时同步管理。"""

    def __init__(self, source_dir: str | Path, target_dir: str | Path):
        self.source = Path(source_dir)
        self.target = Path(target_dir)
        self.target.mkdir(exist_ok=True)

    def dry_run(self) -> dict[str, Any]:
        """预览变更 (不执行)。"""
        changes: dict[str, list] = {"new": [], "modified": [], "deleted": [], "unchanged": []}
        if not self.source.exists():
            return changes

        for src_file in self.source.rglob("SKILL.md"):
            rel = src_file.relative_to(self.source)
            tgt = self.target / rel
            if not tgt.exists():
                changes["new"].append(str(rel))
            elif src_file.read_text() != tgt.read_text():
                changes["modified"].append(str(rel))
            else:
                changes["unchanged"].append(str(rel))

        for tgt_file in self.target.rglob("SKILL.md"):
            rel = tgt_file.relative_to(self.target)
            if not (self.source / rel).exists():
                changes["deleted"].append(str(rel))
        return changes

    def apply(self) -> int:
        """执行同步, 返回更新数量。"""
        changes = self.dry_run()
        count = 0
        for rel in changes["new"] + changes["modified"]:
            src = self.source / rel
            tgt = self.target / rel
            tgt.parent.mkdir(parents=True, exist_ok=True)
            tgt.write_text(src.read_text())
            count += 1
        for rel in changes["deleted"]:
            (self.target / rel).unlink(missing_ok=True)
            count += 1
        return count

    def validate(self) -> dict[str, Any]:
        """验证源与目标一致性。"""
        changes = self.dry_run()
        return {"consistent": not any([changes["new"], changes["modified"], changes["deleted"]]),
                "changes": sum(len(v) for v in changes.values()) - len(changes["unchanged"])}


# ════════════════════════════════════
# 系统检查 (checks)
# ════════════════════════════════════

def system_checks() -> dict[str, Any]:
    """运行时系统健康检查。"""
    checks: dict[str, Any] = {}

    # Python 版本
    import sys
    checks["python"] = {"version": sys.version, "ok": sys.version_info >= (3, 10)}

    # 核心依赖
    deps = ["pydantic", "pyyaml", "httpx", "typer", "fastapi"]
    for dep in deps:
        try:
            import importlib
            importlib.import_module(dep)
            checks[dep] = "ok"
        except ImportError:
            checks[dep] = "missing"

    # Agent 数量
    from haip.agent import list_all
    checks["agents_registered"] = len(list_all())

    # 目录存在性
    for d in ["assets", "knowledge", "config"]:
        checks[f"dir_{d}"] = Path(d).exists()

    return checks


# ════════════════════════════════════
# 基准测试 (benchmark)
# ════════════════════════════════════

def benchmark_a2a(iterations: int = 10) -> dict[str, Any]:
    """A2A 调用基准测试。"""
    from haip.a2a import call, clear_history
    from haip.agent import DomainPlugin, ToolDef, _registry, register

    _registry.clear()
    clear_history()

    def dummy(**kwargs):
        return {"status": "ok"}

    register(DomainPlugin(name="bench", type="specialist", tools=[
        ToolDef(name="noop", description="", handler="builtins.print")]))

    times: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        call("bench", "noop", {})
        times.append((time.perf_counter() - t0) * 1000)

    times.sort()
    return {
        "iterations": iterations,
        "avg_ms": round(sum(times) / len(times), 3),
        "min_ms": round(times[0], 3),
        "max_ms": round(times[-1], 3),
        "p95_ms": round(times[int(len(times) * 0.95)], 3),
    }


# ════════════════════════════════════
# 输出格式化 (output)
# ════════════════════════════════════

def format_output(data: dict[str, Any], fmt: str = "text") -> str:
    """格式化 Agent 输出: text / json / table。"""
    import json

    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    if fmt == "table":
        lines = []
        for key, value in data.items():
            lines.append(f"  {key:25s} | {str(value)[:60]}")
        return "\n".join(lines)

    # text format
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for v in value:
                lines.append(f"  - {v}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)
