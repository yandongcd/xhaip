"""AgentTool — Agent 包装为可调用工具 (ADK 风格的 LLM 委派机制).

实现:
  1. AgentTool(agent_name) → 包装为 callable，可放入 tools 列表
  2. LLM 通过 function_call 触发委派 → 自动调用 a2a call/reason
  3. 支持两种模式:
     - single_turn: 单次工具调用 (同步返回结果)
     - task: 多步推理 (通过 AgentLoop 执行)

用法:
    coordinator = Agent("coordinator", tools=[
        AgentTool("cardiology"),     # LLM 可直接"调用"心内科
        AgentTool("pharmacy"),       # LLM 可直接"调用"药房
    ])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentTool:
    """将 Agent 包装为 LLM 可调用的工具.

    当 LLM 输出 function_call(name="cardiology", args={...}) 时:
      1. 查找对应 AgentTool
      2. 根据 mode 执行:
         - "single": a2a.call(agent, tool_name, params)  — 单次调用
         - "task":   a2a.call_with_loop(agent, query)    — 多步推理
      3. 返回结构化结果

    schema 自动从 agent YAML 定义生成.
    """

    agent_name: str
    tool_name: str = "reason"      # 目标 tool，默认触发 ReAct loop
    mode: str = "single"           # single | task
    label: str = ""                # 显示名

    def __post_init__(self):
        if not self.label:
            self.label = self.agent_name

    def get_schema(self) -> dict[str, Any]:
        """生成 OpenAI 兼容的 tool schema."""
        from haip.agent import get as get_agent
        plugin = get_agent(self.agent_name)

        description = f"Delegate to {self.label} agent"
        if plugin:
            description = f"Call the {plugin.cn_name} ({self.agent_name}) for {plugin.type} tasks"

        if self.mode == "task":
            description += ". The agent will autonomously reason and use its own tools."

        params: dict[str, Any] = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": f"The task/question for the {self.label} agent",
                },
            },
            "required": ["query"],
        }

        # single mode: 暴露 agent 的真正 tool schemas
        if self.mode == "single" and plugin and plugin.tools:
            params["properties"]["tool"] = {
                "type": "string",
                "description": f"Tool to call on {self.label}. Available: "
                               + ", ".join(t.name for t in plugin.tools),
                "enum": [t.name for t in plugin.tools],
            }
            params["required"].append("tool")

        return {
            "name": self._tool_name(),
            "description": description,
            "parameters": params,
        }

    def _tool_name(self) -> str:
        """生成唯一 tool name: agent_xxx → 下划线命名."""
        return f"agent_{self.agent_name.replace('-', '_')}"

    def execute(self, **kwargs) -> dict[str, Any]:
        """执行 Agent 工具调用.

        Args:
            query: 委托任务描述 (task mode)
            tool: 具体工具名 (single mode)
            **kwargs: 传递给工具的参数
        """
        from haip.a2a import call as a2a_call
        from haip.a2a import call_with_loop

        if self.mode == "task":
            query = kwargs.get("query", "")
            return call_with_loop(self.agent_name, query)

        # single mode
        tool = kwargs.pop("tool", self.tool_name)
        if tool == "reason":
            query = kwargs.get("query", kwargs.get("message", ""))
            return call_with_loop(self.agent_name, query)

        return a2a_call(self.agent_name, tool, kwargs)

    def __call__(self, **kwargs) -> dict[str, Any]:
        return self.execute(**kwargs)


# ── 批量构建 ──

def build_agent_tools(
    agent_names: list[str],
    mode: str = "single",
) -> list[AgentTool]:
    """从 agent 名称列表创建 AgentTool 列表."""
    return [AgentTool(name, mode=mode) for name in agent_names]


def get_agent_tool_schemas(agent_tools: list[AgentTool]) -> list[dict[str, Any]]:
    """获取所有 AgentTool 的 OpenAI 兼容 schema."""
    schemas = []
    seen = set()
    for at in agent_tools:
        name = at._tool_name()
        if name not in seen:
            schemas.append(at.get_schema())
            seen.add(name)
    return schemas


# ── AgentTool 执行器 — 用于 AgentLoop ──

def create_agent_tool_executor(agent_tools: list[AgentTool]) -> callable:
    """创建工具执行器: function(name, args) → result.

    用于 AgentLoop.tool_executor.
    """
    tool_map = {at._tool_name(): at for at in agent_tools}

    def executor(name: str, args: dict) -> dict:
        at = tool_map.get(name)
        if at is None:
            return {"status": "error", "error": f"Unknown agent tool: {name}"}
        try:
            result = at.execute(**args)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    return executor
