"""ClinicalWorkflow DSL — ADK 风格的声明式图编排引擎.

设计原则:
  1. 节点: Agent (LLM推理) / Function (确定性代码) / Join (汇聚)
  2. 边:   Sequential → Conditional (路由) → Fan-out/Fan-in
  3. 执行: topological sort → layer-parallel → async event streaming

用法示例:
    wf = ClinicalWorkflow("preop_checklist", edges=[
        ("START", assess_risk, router),
        (router, {"high": cardiology_consult, "low": anesthesia}),
        (cardiology_consult, anesthesia),
        (anesthesia, "END"),
    ])
    async for event in wf.run(ctx):
        print(event.content)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from haip.loop.context import InvocationContext
from haip.session.store import Event

# ── Node Types ──

class NodeType(str, Enum):
    AGENT = "agent"       # LLM Agent 节点
    FUNCTION = "function" # 纯函数节点
    JOIN = "join"         # 汇聚节点 (fan-in barrier)
    START = "start"       # 起始节点 (隐含)
    END = "end"           # 终止节点 (隐含)


@dataclass
class Node:
    """工作流节点."""
    id: str
    node_type: NodeType
    label: str = ""
    # Agent 类型: agent_name → 调用 a2a loop
    agent_name: str = ""
    # Function 类型: callable
    func: Callable | None = None
    # 节点级配置
    config: dict[str, Any] = field(default_factory=dict)


# ── Route Types ──

@dataclass
class Route:
    """路由规则: 从源节点到目标节点的条件映射."""
    source: str
    targets: dict[str, str]  # {route_value: target_node_id}
    default: str = ""        # 未匹配时的默认目标


# ── Workflow DSL ──

@dataclass
class ClinicalWorkflow:
    """声明式临床工作流图.

    支持三种边定义方式:
      1. Sequential: ("A", "B", "C") → A→B→C 顺序执行
      2. Conditional: (source, {"high": target_a, "low": target_b})
      3. Fan-out/Join: 多边指向同一 JoinNode → 自动并行→等待汇聚
    """

    name: str
    label: str = ""
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[tuple] = field(default_factory=list)

    # 自动推导的图结构
    _adjacency: dict[str, list[str]] = field(default_factory=dict)
    _routes: dict[str, Route] = field(default_factory=dict)
    _join_nodes: set[str] = field(default_factory=set)
    _node_registry: dict[str, Node] = field(default_factory=dict)  # label → Node

    def __post_init__(self):
        self.compile()

    def compile(self) -> None:
        """编译边定义 → 内部图结构."""
        self._adjacency.clear()
        self._routes.clear()
        self._join_nodes.clear()

        # 从预置 nodes 初始化 registry
        self._node_registry = {nid: n for nid, n in self.nodes.items()}
        # 隐式注册 START/END
        self._node_registry.setdefault("START", Node("START", NodeType.START, "开始"))
        self._node_registry.setdefault("END", Node("END", NodeType.END, "结束"))

        for edge_def in self.edges:
            if len(edge_def) == 2:
                src, tgt = edge_def
                if isinstance(tgt, dict):
                    # Conditional: (router, {route_key: target})
                    self._add_conditional(src, src, tgt)
                else:
                    self._add_sequential(src, tgt)
            elif len(edge_def) == 3:
                src, mid, third = edge_def
                if isinstance(third, dict):
                    # Conditional: (source, router, {route_value: target})
                    self._add_conditional(src, mid, third)
                else:
                    # Sequential chain: (A, B, C)
                    seq = [src, mid, third]
                    for i in range(len(seq) - 1):
                        self._add_sequential(seq[i], seq[i + 1])
            elif len(edge_def) > 3:
                chain = list(edge_def)
                for i in range(len(chain) - 1):
                    self._add_sequential(chain[i], chain[i + 1])

    def _register_node(self, node_or_id: str | Node) -> str:
        """注册节点并返回 node_id。已有节点保留原有类型。"""
        if isinstance(node_or_id, str):
            node_id = node_or_id
            if node_id not in self._node_registry:
                self._node_registry[node_id] = Node(node_id, NodeType.FUNCTION)
        else:
            node = node_or_id
            node_id = node.id
            if node_id in self._node_registry:
                existing = self._node_registry[node_id]
                if existing.node_type == NodeType.FUNCTION and node.node_type != NodeType.FUNCTION:
                    self._node_registry[node_id] = node
            else:
                self._node_registry[node_id] = node
        return node_id

    def _add_sequential(self, src: str | Node, tgt: str | Node) -> None:
        src_id = self._register_node(src)
        tgt_id = self._register_node(tgt)
        self._adjacency.setdefault(src_id, []).append(tgt_id)

    def _add_conditional(self, src: str | Node, router: str | Node,
                         route_map: dict) -> None:
        src_id = self._register_node(src)
        router_id = self._register_node(router)
        self._adjacency.setdefault(src_id, []).append(router_id)

        targets: dict[str, str] = {}
        for route_key, tgt in route_map.items():
            tgt_id = self._register_node(tgt)
            targets[str(route_key)] = tgt_id
            self._adjacency.setdefault(router_id, []).append(tgt_id)

        self._routes[router_id] = Route(
            source=router_id,
            targets=targets,
            default=targets.get("default", ""),
        )

    @property
    def start_node(self) -> Node:
        return self._node_registry.get("START", Node("START", NodeType.START))

    @property
    def end_node(self) -> Node:
        return self._node_registry.get("END", Node("END", NodeType.END))

    def get_successors(self, node_id: str) -> list[str]:
        """获取节点的后继."""
        return self._adjacency.get(node_id, [])

    def get_route(self, node_id: str) -> Route | None:
        return self._routes.get(node_id)

    def is_join(self, node_id: str) -> bool:
        """判断是否为 JoinNode: 多个前驱指向同一节点."""
        incoming = 0
        for src_list in self._adjacency.values():
            if node_id in src_list:
                incoming += 1
        return incoming > 1

    def add_node(self, nodes: Node) -> None:
        self._node_registry[nodes.id] = nodes

    # ── 拓扑排序 (分层并行) ──

    def toposort_layers(self) -> list[list[str]]:
        """返回拓扑分层: [[layer0_nodes], [layer1_nodes], ...].

        同一层的节点可并行执行.
        """
        in_degree: dict[str, int] = {}
        for node_id in self._node_registry:
            in_degree[node_id] = 0
        for src, tgts in self._adjacency.items():
            for tgt in tgts:
                in_degree[tgt] = in_degree.get(tgt, 0) + 1

        layers: list[list[str]] = []
        queue = [n for n, d in in_degree.items() if d == 0]

        while queue:
            current_layer = list(queue)
            layers.append(current_layer)
            next_queue = []

            for node_id in current_layer:
                for tgt in self._adjacency.get(node_id, []):
                    in_degree[tgt] -= 1
                    if in_degree[tgt] == 0:
                        next_queue.append(tgt)

            queue = next_queue

        return layers

    # ── 执行 ──

    async def execute(
        self,
        ctx: InvocationContext,
        input_data: dict[str, Any] | None = None,
    ) -> AsyncIterator[Event]:
        """异步执行工作流，每步 yield Event.

        执行流程:
          1. 拓扑排序 → 分层
          2. 每层内并行执行节点
          3. 层间顺序: JoinNode 等待所有前驱完成
          4. 条件路由: Router 输出决定下一节点
        """
        input_data = input_data or {}
        layers = self.toposort_layers()
        # 累积状态: node_id → execution_result
        node_results: dict[str, Any] = {}

        for layer_idx, layer in enumerate(layers):
            layer_tasks = []

            for node_id in layer:
                node = self._node_registry.get(node_id)
                if node is None:
                    continue

                # 收集上游数据
                upstream_data = self._collect_upstream(node_id, node_results)

                if node.node_type == NodeType.START:
                    node_results[node_id] = {"output": input_data}
                    continue

                if node.node_type == NodeType.END:
                    continue

                # 路由节点: 根据上游输出决定下一跳
                if node_id in self._routes:
                    route = self._routes[node_id]
                    route_source = node_results.get(node_id, {})
                    route_value = str(route_source.get("output", ""))
                    next_node = route.targets.get(route_value, route.default)
                    if next_node:
                        node_results[node_id] = {
                            "output": route_value,
                            "next": next_node,
                        }
                    yield Event.assistant_message(
                        content=f"[Router] {node.label or node_id} → {route_value}",
                        invocation_id=ctx.invocation_id,
                        state_delta={f"wf:route_{node_id}": route_value},
                    )
                    continue

                # 执行节点
                task = self._execute_node(node, upstream_data, ctx)
                layer_tasks.append(task)

            # 并行执行本层节点
            if layer_tasks:
                results = await asyncio.gather(*layer_tasks, return_exceptions=True)
                for task, result in zip(layer_tasks, results):
                    node_id = task.__name__ if hasattr(task, "__name__") else str(task)
                    if isinstance(result, Exception):
                        yield Event.assistant_message(
                            content=f"[Error] {node_id}: {result}",
                            invocation_id=ctx.invocation_id,
                            error=str(result),
                        )
                        node_results[node_id] = {"error": str(result)}
                    else:
                        node_id, output = result
                        node_results[node_id] = output
                        yield Event.assistant_message(
                            content=f"[{node_id}] {output.get('summary', 'done')}",
                            invocation_id=ctx.invocation_id,
                            state_delta={f"wf:{node_id}": output},
                        )

        # 最终状态
        yield Event.assistant_message(
            content="Workflow complete",
            invocation_id=ctx.invocation_id,
            turn_complete=True,
            state_delta={"wf:complete": True, "wf:results": node_results},
        )

    def _collect_upstream(self, node_id: str,
                          node_results: dict[str, Any]) -> dict[str, Any]:
        """收集上游节点的输出作为当前节点的输入."""
        upstream: dict[str, Any] = {}
        for src, tgts in self._adjacency.items():
            if node_id in tgts and src in node_results:
                upstream[src] = node_results[src].get("output", node_results[src])
        return upstream

    async def _execute_node(self, node: Node, upstream_data: dict,
                            ctx: InvocationContext) -> tuple[str, dict]:
        """执行单个节点，返回 (node_id, output_dict)."""
        if node.node_type == NodeType.FUNCTION and node.func is not None:
            # 在线程池中执行同步函数
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, node.func, upstream_data,
            )
            return (node.id, {"output": result, "summary": str(result)[:100]})

        if node.node_type == NodeType.AGENT and node.agent_name:
            # 调用 Agent 工具 (引擎内部编排: 显式内部上下文)
            from haip.a2a import call as a2a_call
            from haip.a2a import internal_permission_context
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: a2a_call(node.agent_name,
                                 upstream_data.get("tool", "reason"),
                                 upstream_data,
                                 perm_ctx=internal_permission_context()),
            )
            return (node.id, {"output": result, "summary": str(result.get("reply", str(result)))[:100]})

        return (node.id, {"output": upstream_data, "summary": "pass-through"})


# ── 工作流构建器 (Builder Pattern) ──

class WorkflowBuilder:
    """流式 API 构建工作流."""

    def __init__(self, name: str, label: str = ""):
        self._name = name
        self._label = label
        self._nodes: list[Node] = []
        self._edges: list[tuple] = []
        self._route_maps: dict[str, dict] = {}

    def add_agent(self, node_id: str, agent_name: str, label: str = "") -> WorkflowBuilder:
        self._nodes.append(Node(node_id, NodeType.AGENT, label, agent_name=agent_name))
        return self

    def add_function(self, node_id: str, func: Callable, label: str = "") -> WorkflowBuilder:
        self._nodes.append(Node(node_id, NodeType.FUNCTION, label, func=func))
        return self

    def add_join(self, node_id: str, label: str = "") -> WorkflowBuilder:
        self._nodes.append(Node(node_id, NodeType.JOIN, label))
        return self

    def chain(self, *node_ids: str) -> WorkflowBuilder:
        """顺序链: chain("A", "B", "C") → A→B→C."""
        self._edges.append(tuple(node_ids))
        return self

    def route(self, source: str, route_map: dict[str, str]) -> WorkflowBuilder:
        """条件路由: route("A", {"high": "B", "low": "C"})."""
        self._route_maps[source] = route_map
        # 创建一个隐式路由节点
        router_id = f"{source}_router"
        self._nodes.append(Node(router_id, NodeType.FUNCTION, f"Router:{source}"))
        self._edges.append((source, router_id, route_map))
        return self

    def fan_out(self, source: str, *targets: str) -> WorkflowBuilder:
        """扇出: fan_out("A", "B", "C") → A→B, A→C (并行)."""
        for tgt in targets:
            self._edges.append((source, tgt))
        return self

    def fan_in(self, join_id: str, *sources: str) -> WorkflowBuilder:
        """扇入: fan_in("J", "A", "B") → A→J, B→J (汇聚)."""
        for src in sources:
            self._edges.append((src, join_id))
        return self

    def build(self) -> ClinicalWorkflow:
        wf = ClinicalWorkflow(
            name=self._name,
            label=self._label,
            nodes={n.id: n for n in self._nodes},
            edges=self._edges,
        )
        return wf
