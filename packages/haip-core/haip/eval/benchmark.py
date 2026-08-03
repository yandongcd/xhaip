"""基准评测适配器 — 连接外部评测环境 (CP-Env, MedAgentBench 等).

设计: 适配器协议 EvalAdapter → 特定评测后端 (CPEnvAdapter/MedAgentBenchAdapter).
未接入外部环境时 fallback 到内置评测 (haip/eval 场景).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkResult:
    """外部基准评测结果 (对齐 CP-Env 输出结构)."""
    benchmark: str                       # CP-Env / MedAgentBench / ...
    model: str                           # 被测 agent 名
    pass_rate: float = 0.0
    total_tasks: int = 0
    passed: int = 0
    dimensions: dict[str, float] = field(default_factory=dict)  # 维度分
    per_task: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class EvalAdapter(ABC):
    """外部评测适配器协议."""

    @abstractmethod
    def setup(self) -> bool:
        """初始化评测环境 (下载数据/检查依赖)."""

    @abstractmethod
    def run(self, agent_name: str, task_ids: list[str] | None = None) -> BenchmarkResult:
        """运行评测, 返回结果."""


class BuiltinAdapter(EvalAdapter):
    """内置评测适配器 (haip/eval 场景 → 对齐 BenchmarkResult 格式)."""

    def setup(self) -> bool:
        from haip.eval import list_tasks
        return bool(list_tasks())

    def run(self, agent_name: str = "orthopedic-surgery", task_ids: list[str] | None = None) -> BenchmarkResult:
        from haip.eval import build_scenarios, run_all
        from haip.eval.scorer import score_scenario_rules

        task = "orthopedics_hip_fracture"
        scenarios = build_scenarios(task, limit=10)
        if not scenarios:
            return BenchmarkResult(benchmark="builtin-eval", model=agent_name, errors=["无匹配场景"])

        traces = run_all(scenarios, agent_name=agent_name)
        scores = []
        passed = 0
        for trace, sc in zip(traces, scenarios):
            s = score_scenario_rules(sc, trace["results"])
            scores.append(s)
            if s.overall >= 60:
                passed += 1

        n = len(scores)
        return BenchmarkResult(
            benchmark="builtin-eval",
            model=agent_name,
            pass_rate=round(passed / n * 100, 1) if n else 0.0,
            total_tasks=n,
            passed=passed,
            dimensions={
                "efficacy": round(sum(s.efficacy for s in scores) / n, 1) if n else 0.0,
                "process": round(sum(s.process for s in scores) / n, 1) if n else 0.0,
                "ethics": round(sum(s.ethics for s in scores) / n, 1) if n else 0.0,
            },
            per_task=[{"id": s.scenario_id, "overall": s.overall} for s in scores],
        )


class CPEnvAdapter(EvalAdapter):
    """CP-Env 评测适配器 (对接港大 2025-12 开源环境).

    未接入外部仓库时返回 placeholder.
    """

    def __init__(self):
        self._available = False

    def setup(self) -> bool:
        try:
            import sys
            sys.path.insert(0, "extern/CP_ENV")
            from gym_env import CPEnvGym  # noqa: F401
            self._available = True
        except ImportError:
            pass
        return self._available

    def run(self, agent_name: str = "orthopedic-surgery", task_ids: list[str] | None = None) -> BenchmarkResult:
        if not self._available:
            return BenchmarkResult(
                benchmark="CP-Env",
                model=agent_name,
                errors=["CP-Env 环境未安装 (克隆 github.com/SPIRAL-MED/CP_ENV 到 extern/CP_ENV 后重试)"],
            )
        # TODO: 对接 CP-Env gym 接口: reset(patient) → step(tool_call) → observation
        return BenchmarkResult(benchmark="CP-Env", model=agent_name, errors=["adapter 待实现"])


class MedAgentBenchAdapter(EvalAdapter):
    """MedAgentBench 评测适配器 (Stanford 2025-01, FHIR 环境)."""

    def __init__(self):
        self._available = False

    def setup(self) -> bool:
        try:
            import sys
            sys.path.insert(0, "extern/MedAgentBench")
            from medagentbench_env import MedAgentEnv  # noqa: F401
            self._available = True
        except ImportError:
            pass
        return self._available

    def run(self, agent_name: str = "orthopedic-surgery", task_ids: list[str] | None = None) -> BenchmarkResult:
        if not self._available:
            return BenchmarkResult(
                benchmark="MedAgentBench",
                model=agent_name,
                errors=["MedAgentBench 环境未安装 (克隆 github.com/stanfordmlgroup/MedAgentBench 到 extern/MedAgentBench 后重试)"],
            )
        # TODO: FHIR converter (haip/fhir/converter.py) + MedAgentEnv
        return BenchmarkResult(benchmark="MedAgentBench", model=agent_name, errors=["adapter 待实现"])


def get_builtin_score(agent_name: str = "orthopedic-surgery") -> BenchmarkResult:
    """快速获取内置评测基准分数."""
    a = BuiltinAdapter()
    a.setup()
    return a.run(agent_name)


def list_benchmarks() -> list[str]:
    return ["builtin-eval", "CP-Env", "MedAgentBench"]
