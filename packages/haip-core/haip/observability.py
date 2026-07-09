"""可观测性 — A2A Trace + 性能 Metrics 收集."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Span:
    """一次 A2A 调用的 trace span。"""
    trace_id: str = ""
    span_id: str = ""
    parent_id: str = ""
    agent: str = ""
    tool: str = ""
    status: str = "pending"
    start_ms: float = 0.0
    duration_ms: float = 0.0
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class TraceContext:
    """分布式 trace 上下文管理。"""

    def __init__(self):
        self.spans: list[Span] = []
        self._trace_counter = 0

    def start_trace(self, workflow_id: str = "") -> str:
        self._trace_counter += 1
        tid = workflow_id or f"trace_{self._trace_counter}_{int(time.time() * 1000)}"
        return tid

    def add_span(self, span: Span):
        self.spans.append(span)

    def get_trace(self, trace_id: str) -> list[Span]:
        return [s for s in self.spans if s.trace_id == trace_id]

    def clear(self):
        self.spans.clear()


class MetricsCollector:
    """性能指标收集器。"""

    def __init__(self):
        self.call_counts: dict[str, int] = defaultdict(int)
        self.call_durations: dict[str, list[float]] = defaultdict(list)
        self.error_counts: dict[str, int] = defaultdict(int)
        self.start_time = time.time()

    def record(self, agent: str, tool: str, duration_ms: float, status: str = "ok"):
        key = f"{agent}/{tool}"
        self.call_counts[key] += 1
        self.call_durations[key].append(duration_ms)
        if status == "error":
            self.error_counts[key] += 1

    def summary(self) -> dict[str, Any]:
        """生成性能汇总报告。"""
        agents: dict[str, Any] = {}
        for key, count in self.call_counts.items():
            agent, tool = key.split("/", 1)
            if agent not in agents:
                agents[agent] = {"total_calls": 0, "tools": {}}
            durations = self.call_durations[key]
            agents[agent]["total_calls"] += count
            agents[agent]["tools"][tool] = {
                "count": count,
                "errors": self.error_counts.get(key, 0),
                "avg_ms": round(sum(durations) / len(durations), 2) if durations else 0,
                "p95_ms": round(sorted(durations)[int(len(durations) * 0.95)], 2) if durations else 0,
            }

        return {
            "uptime_seconds": round(time.time() - self.start_time, 1),
            "total_calls": sum(self.call_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "agents": agents,
        }

    def reset(self):
        self.call_counts.clear()
        self.call_durations.clear()
        self.error_counts.clear()


# 全局单例
trace_ctx = TraceContext()
metrics = MetricsCollector()
