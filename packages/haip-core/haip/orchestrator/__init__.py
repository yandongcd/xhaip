"""Orchestrator — 多 Agent 编排引擎 (支持并行 DAG 执行)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from haip.a2a import call as a2a_call
from haip.llm import LLMProvider


class OrchestrationMode(str, Enum):
    AUTO = "auto"          # LLM 动态规划 DAG
    PIPELINE = "pipeline"  # 预定义步骤顺序执行
    DIRECT = "direct"      # 单 Agent 直接调用


@dataclass
class TaskNode:
    id: str
    agent: str
    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    status: str = "pending"  # pending / running / completed / error / skipped


@dataclass
class TaskDAG:
    nodes: list[TaskNode] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def toposort_layers(self) -> list[list[TaskNode]]:
        """拓扑排序分层: 无依赖节点放在同一层, 可并行执行。"""
        node_map = {n.id: n for n in self.nodes}
        in_degree: dict[str, int] = {n.id: len(n.depends_on) for n in self.nodes}
        layers: list[list[TaskNode]] = []

        while in_degree:
            layer = [n for nid, n in node_map.items()
                     if nid in in_degree and in_degree[nid] == 0]
            if not layer:
                # 检测到循环依赖
                remaining = list(in_degree.keys())
                for nid in remaining:
                    node_map[nid].status = "error"
                    node_map[nid].result = {"status": "error", "error": "circular dependency"}
                break
            layers.append(layer)
            for n in layer:
                del in_degree[n.id]
                for other in self.nodes:
                    if n.id in other.depends_on and other.id in in_degree:
                        in_degree[other.id] -= 1
        return layers


@dataclass
class OrchestrationResult:
    status: str = "completed"
    answer: str = ""
    nodes: list[TaskNode] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_elapsed_ms: float = 0.0


# ── Transport ──

class AgentTransport(ABC):
    """Agent 调用传输层抽象。"""

    @abstractmethod
    def call(self, agent: str, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        ...


class InProcessTransport(AgentTransport):
    """进程内 A2A 调用 — 直接 importlib 加载。"""

    def call(self, agent: str, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        return a2a_call(agent, tool, params)


class MockTransport(AgentTransport):
    """测试用 Mock Transport。"""

    def __init__(self, responses: dict[str, dict[str, Any]] | None = None):
        self.responses = responses or {}
        self.call_log: list[dict[str, Any]] = []

    def call(self, agent: str, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        self.call_log.append({"agent": agent, "tool": tool, "params": params})
        key = f"{agent}/{tool}"
        if key in self.responses:
            return dict(self.responses[key])
        return {"status": "ok", "result": f"mock:{agent}/{tool}", "agent": agent}


# ── Orchestrator ──

class A2AOrchestrator:
    """多 Agent 编排器。支持 AUTO/PIPELINE/DIRECT 三种模式 + 并行 DAG 执行。"""

    def __init__(
        self,
        transport: AgentTransport | None = None,
        llm: LLMProvider | None = None,
        mode: OrchestrationMode = OrchestrationMode.AUTO,
    ):
        self.transport = transport or InProcessTransport()
        self.llm = llm
        self.mode = mode

    def execute(
        self,
        task: str = "",
        dag: TaskDAG | None = None,
        pipeline_steps: list[TaskNode] | None = None,
    ) -> OrchestrationResult:
        """执行编排任务。

        AUTO 模式: 使用 LLM 规划 DAG (需要 llm 不为 None)
        PIPELINE 模式: 使用预定义步骤构建 DAG
        DIRECT 模式: 单 Agent 直连
        如提供 dag 参数，则直接执行该 DAG。
        """
        import time
        t0 = time.perf_counter()

        if dag is None:
            if self.mode == OrchestrationMode.PIPELINE and pipeline_steps:
                dag = TaskDAG(nodes=pipeline_steps)
            elif self.mode == OrchestrationMode.DIRECT and pipeline_steps:
                dag = TaskDAG(nodes=pipeline_steps[:1])
            elif self.llm and task:
                dag = self.plan(task)
            else:
                return OrchestrationResult(status="error", errors=["no DAG or LLM available"])

        result = self._execute_dag(dag)
        result.total_elapsed_ms = (time.perf_counter() - t0) * 1000
        return result

    def plan(self, task: str, available_agents: list[dict] | None = None) -> TaskDAG:
        """LLM 动态规划 DAG。"""
        if not self.llm:
            return TaskDAG(metadata={"plan_error": "no LLM provider"})

        agents_desc = ""
        if available_agents:
            for a in available_agents:
                agents_desc += f"- {a['name']}: {a.get('description', '')}\n"
        else:
            from haip.agent import list_all
            for name, p in list_all().items():
                agents_desc += f"- {name}({p.type}): {p.cn_name}\n"

        resp = self.llm.chat(
            messages=[{
                "role": "system",
                "content": (
                    "你是多Agent编排器。根据任务描述和可用Agent列表，生成JSON格式的TaskDAG。\n"
                    "每个节点格式: {id, agent, tool, params, depends_on: [node_id]}\n"
                    "无依赖的节点可以并行执行。只输出JSON数组，不要解释。"
                ),
            }, {
                "role": "user",
                "content": f"任务: {task}\n\n可用Agent:\n{agents_desc}",
            }],
            temperature=0.1,
            max_tokens=2048,
        )

        import json
        try:
            content = resp.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            nodes_data = json.loads(content)
            if isinstance(nodes_data, list):
                nodes = [TaskNode(**n) for n in nodes_data]
                return TaskDAG(nodes=nodes)
        except (json.JSONDecodeError, TypeError):
            pass
        return TaskDAG(metadata={"plan_error": "LLM response not valid JSON"})

    def _execute_dag(self, dag: TaskDAG) -> OrchestrationResult:
        """按拓扑排序分层并行执行 DAG。"""
        result = OrchestrationResult(nodes=dag.nodes)
        completed: dict[str, dict[str, Any]] = {}

        layers = dag.toposort_layers()
        for layer_idx, layer in enumerate(layers):
            # 并行执行同层无依赖节点
            pending = [n for n in layer if n.status == "pending"]
            if not pending:
                continue

            def _run_node(node: TaskNode):
                merged_params = dict(node.params)
                for dep_id in node.depends_on:
                    if dep_id in completed:
                        merged_params[f"_dep_{dep_id}"] = completed[dep_id]
                node.status = "running"
                resp = self.transport.call(node.agent, node.tool, merged_params)
                node.result = resp
                return node, resp

            with ThreadPoolExecutor(max_workers=min(len(pending), 8)) as executor:
                futures = {executor.submit(_run_node, n): n for n in pending}
                for future in as_completed(futures):
                    node, resp = future.result()
                    if resp.get("status") == "error":
                        node.status = "error"
                        result.errors.append(f"{node.agent}/{node.tool}: {resp.get('error', '')}")
                        for n in dag.nodes:
                            if node.id in n.depends_on and n.status == "pending":
                                n.status = "skipped"
                    else:
                        node.status = "completed"
                        completed[node.id] = resp

        # 聚合答案
        answers = []
        for n in dag.nodes:
            if n.result and n.result.get("status") == "ok":
                data = n.result
                for key in ("recommendations", "conclusion", "output", "result"):
                    if key in data:
                        val = data[key]
                        if isinstance(val, list):
                            answers.extend(val)
                        elif isinstance(val, str) and val:
                            answers.append(val)
        result.answer = "\n".join(answers) if answers else "编排完成"
        return result
