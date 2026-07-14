"""Workflow Runner — Session + Hook + AgentTool 集成的可执行工作流引擎.

将 ClinicalWorkflow DSL 编译为可执行管道:
  1. 解析 graph → 拓扑分层
  2. 每层: Agent 节点 → AsyncAgentLoop, Function 节点 → 直接调用
  3. 通过 InvocationContext 传递 state
  4. 每步 yield Event
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from haip.session.store import Event
from haip.llm import LLMProvider
from haip.loop.context import InvocationContext
from haip.loop.hooks import HookChain
from haip.orchestrator.graph import ClinicalWorkflow, Node, NodeType


async def run_workflow(
    workflow: ClinicalWorkflow,
    ctx: InvocationContext,
    llm: LLMProvider | None = None,
    hooks: HookChain | None = None,
    agent_tools: list | None = None,
    input_data: dict[str, Any] | None = None,
) -> AsyncIterator[Event]:
    """执行 ClinicalWorkflow，每步 yield Event.

    Args:
        workflow: 编译后的工作流图
        ctx: 执行上下文 (session + state)
        llm: Agent 节点使用的 LLM
        hooks: 全局钩子链
        agent_tools: 预构建的 AgentTool 列表 (用于 agent 节点)
        input_data: 初始输入数据

    Yields:
        Event: 每步执行结果
    """
    input_data = input_data or {}
    layers = workflow.toposort_layers()
    node_results: dict[str, Any] = {}

    for layer_idx, layer in enumerate(layers):
        layer_tasks = []
        node_order: list[str] = []

        for node_id in layer:
            node = workflow._node_registry.get(node_id)
            if node is None:
                continue

            if node.node_type == NodeType.START:
                node_results[node_id] = {"output": input_data}
                continue
            if node.node_type == NodeType.END:
                continue

            # 路由节点
            if node_id in workflow._routes:
                route = workflow._routes[node_id]
                route_source = node_results.get(node_id, {})
                route_value = str(route_source.get("output", ""))
                next_node = route.targets.get(route_value, route.default)
                if next_node:
                    node_results[node_id] = {"output": route_value, "next": next_node}
                yield Event.assistant_message(
                    content=f"[Workflow] Route: {node.label or node_id} → {route_value}",
                    invocation_id=ctx.invocation_id,
                    state_delta={f"wf:route_{node_id}": route_value},
                )
                continue

            # 收集上游数据
            upstream = _collect_upstream(node_id, node_results, workflow._adjacency)
            node_order.append(node_id)

            # 创建 async task
            task = _execute_node_async(
                node, upstream, ctx, llm, hooks, agent_tools,
            )
            layer_tasks.append((node_id, task))

        # 并行执行本层
        if layer_tasks:
            tasks = [t for _, t in layer_tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for (node_id, _), result in zip(layer_tasks, results):
                if isinstance(result, Exception):
                    yield Event.assistant_message(
                        content=f"[Workflow Error] {node_id}: {result}",
                        invocation_id=ctx.invocation_id,
                        error=str(result),
                    )
                    node_results[node_id] = {"error": str(result)}
                else:
                    output = result
                    node_results[node_id] = output

                    # yield 每个 agent 节点的中间事件
                    sub_events = output.get("_events", [])
                    for se in sub_events:
                        if isinstance(se, Event):
                            yield se
                        elif isinstance(se, dict):
                            yield Event.from_dict(se)

                    yield Event.assistant_message(
                        content=f"[{node.label or node_id}] {str(output.get('summary', output.get('reply', 'done')))[:200]}",
                        invocation_id=ctx.invocation_id,
                        state_delta={f"wf:{node_id}": {
                            k: v for k, v in output.items()
                            if not k.startswith("_") and k != "events"
                        }},
                    )

    # 最终
    yield Event.assistant_message(
        content="Workflow completed",
        invocation_id=ctx.invocation_id,
        turn_complete=True,
        state_delta={"wf:complete": True, "wf:results": {k: v for k, v in node_results.items() if not k.startswith("_")}},
    )


def _collect_upstream(node_id: str, node_results: dict,
                      adjacency: dict[str, list[str]]) -> dict[str, Any]:
    """收集上游节点输出."""
    upstream: dict[str, Any] = {}
    for src, tgts in adjacency.items():
        if node_id in tgts and src in node_results:
            upstream[src] = node_results[src].get("output", node_results[src])
    return upstream


async def _execute_node_async(
    node: Node,
    upstream: dict,
    ctx: InvocationContext,
    llm: LLMProvider | None,
    hooks: HookChain | None,
    agent_tools: list | None,
) -> dict[str, Any]:
    """异步执行单个节点."""

    # Function 节点 — 在线程池中执行
    if node.node_type == NodeType.FUNCTION and node.func is not None:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, node.func, upstream)
        return {"output": result, "summary": str(result)[:200]}

    # Agent 节点 — 通过 AsyncAgentLoop 执行
    if node.node_type == NodeType.AGENT and node.agent_name:
        from haip.a2a import call_with_loop
        from haip.loop import AsyncAgentLoop
        from haip.agent import get as get_agent

        plugin = get_agent(node.agent_name)
        if plugin is None:
            return {"summary": f"Agent '{node.agent_name}' not found", "output": {}}

        # 从上游数据提取 query
        query = _extract_query(upstream)

        # 如果提供了 agent_tools，使用 agent 委派
        if agent_tools:
            from haip.orchestrator.agent_tool import create_agent_tool_executor
            executor = create_agent_tool_executor(agent_tools)
            loop = AsyncAgentLoop(
                llm=llm or _mock_llm(),
                system_prompt=plugin.prompt.system,
                tool_executor=executor,
                tools=[],  # AgentTool schemas 会由 LLM 接口处理
                agent_name=node.agent_name,
                ctx=ctx,
                hooks=hooks,
            )
            events = []
            async for evt in loop.run(query):
                events.append(evt.to_dict())
            return {"output": events, "summary": f"Agent {node.agent_name}: {query[:80]}", "_events": events}

        # 简单调用
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, call_with_loop, node.agent_name, query,
        )
        return {"output": result, "summary": str(result.get("reply", ""))[:200]}

    # Join 节点 — 汇聚上游结果
    if node.node_type == NodeType.JOIN:
        merged = {k: v for k, v in upstream.items()}
        return {"output": merged, "summary": f"Joined {len(merged)} results"}

    return {"output": upstream, "summary": "pass-through"}


def _extract_query(upstream: dict) -> str:
    """从上游数据中提取用户 query."""
    for key in ("query", "text", "message", "task"):
        for val in upstream.values():
            if isinstance(val, dict) and key in val:
                return str(val[key])
            if isinstance(val, str) and key in val.lower():
                return str(val)
    # 聚合
    parts = []
    for val in upstream.values():
        if isinstance(val, dict):
            parts.append(str(val.get("output", str(val)[:200])))
        elif isinstance(val, str):
            parts.append(val[:200])
    return " ".join(parts) if parts else "process"


def _mock_llm() -> LLMProvider:
    from haip.llm.mock import MockProvider
    return MockProvider({})


# ── 同步便捷封装 ──

def run_workflow_sync(
    workflow: ClinicalWorkflow,
    ctx: InvocationContext,
    llm: LLMProvider | None = None,
    hooks: HookChain | None = None,
    agent_tools: list | None = None,
    input_data: dict[str, Any] | None = None,
) -> list[Event]:
    """同步执行工作流，返回所有 events."""
    async def _run():
        events = []
        async for evt in run_workflow(workflow, ctx, llm, hooks, agent_tools, input_data):
            events.append(evt)
        return events
    return asyncio.run(_run())
