"""运维模块 — Agent层级 + 协作工具 + 内存管理 + 权限 + 构建器."""

from __future__ import annotations

from typing import Any

# ════════════════════════════════════
# Agent 层级拓扑 (hierarchy)
# ════════════════════════════════════

def get_agent_tree() -> dict[str, Any]:
    """获取 Agent 树形拓扑 (Parent-Child 层级)。"""
    from haip.agent import list_all
    agents = list_all()
    tree: dict[str, Any] = {"root": [], "nodes": {}}

    for name, p in agents.items():
        tree["nodes"][name] = {
            "type": p.type, "cn_name": p.cn_name, "port": p.port,
            "parent": p.parent, "sub_agents": p.sub_agents,
            "depends_on": p.depends_on, "tools": len(p.tools),
        }
        if not p.parent:
            tree["root"].append(name)
    return tree


def get_dependency_graph() -> dict[str, list[str]]:
    """Agent 间依赖图 (谁依赖谁)。"""
    from haip.agent import list_all
    graph: dict[str, list[str]] = {}
    for name, p in list_all().items():
        deps = [d["agent"] for d in p.depends_on]
        graph[name] = deps
    return graph


# ════════════════════════════════════
# 协作工具 (coord_tools)
# ════════════════════════════════════

def coordinate_agents(task: str, available: list[str] | None = None) -> dict[str, Any]:
    """多 Agent 协作建议: 根据任务推荐 Agent 组合。"""
    from haip.agent import list_all
    agents = list_all()
    result: list[dict] = []

    kw = task.lower()
    for name, p in agents.items():
        if available and name not in available:
            continue
        score = 0
        # 关键词匹配
        cn = p.cn_name.lower()
        for token in kw.split():
            if token in cn:
                score += 2
            if token in name.lower():
                score += 1
        if score > 0:
            result.append({"agent": name, "cn_name": p.cn_name, "type": p.type,
                           "score": score, "tools": [t.name for t in p.tools]})
    result.sort(key=lambda x: x["score"], reverse=True)
    return {"task": task, "recommendations": result[:5]}


# ════════════════════════════════════
# Agent 内存 (memory)
# ════════════════════════════════════

class AgentMemory:
    """Agent 上下文记忆: 会话历史管理。"""

    def __init__(self, max_history: int = 20):
        self.sessions: dict[str, list[dict[str, str]]] = {}
        self.max_history = max_history

    def remember(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": role, "content": content})
        if len(self.sessions[session_id]) > self.max_history * 2:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history * 2:]

    def recall(self, session_id: str, limit: int = 10) -> list[dict[str, str]]:
        return self.sessions.get(session_id, [])[-limit:]

    def clear(self, session_id: str = ""):
        if session_id:
            self.sessions.pop(session_id, None)
        else:
            self.sessions.clear()

    def summary(self, session_id: str) -> dict[str, Any]:
        history = self.sessions.get(session_id, [])
        return {"session_id": session_id, "turns": len(history) // 2,
                "total_messages": len(history)}


# ════════════════════════════════════
# 权限管理 (permissions)
# ════════════════════════════════════

class PermissionManager:
    """角色权限矩阵。"""

    def __init__(self):
        self.roles: dict[str, list[str]] = {
            "admin": ["*"],  # 全部权限
            "attending": ["pharmacy.*", "orthopedic-surgery.*", "cardio-surgery.*",
                         "pediatrics.*", "cardio-risk.*", "medical-record.read"],
            "pharmacist": ["pharmacy.*", "medical-record.read"],
            "nurse": ["medical-record.read", "orthopedic-surgery.nursing_plan"],
            "anesthesiologist": ["anesthesia-risk.*", "cardio-risk.*", "medical-record.read"],
        }

    def can(self, role: str, action: str) -> bool:
        """检查角色是否有权执行操作。"""
        if role not in self.roles:
            return False
        allowed = self.roles[role]
        if "*" in allowed:
            return True
        for pattern in allowed:
            if pattern == action:
                return True
            if pattern.endswith(".*") and action.startswith(pattern[:-2]):
                return True
        return False

    def grant(self, role: str, actions: list[str]):
        if role not in self.roles:
            self.roles[role] = []
        for a in actions:
            if a not in self.roles[role]:
                self.roles[role].append(a)


# ════════════════════════════════════
# Agent 构建器 (builders)
# ════════════════════════════════════

def scaffold_agent(name: str, cn_name: str = "", agent_type: str = "business",
                   port: int = 0, tools: list[dict] | None = None) -> str:
    """生成新 Agent 的 YAML 模板。"""
    tools = tools or []
    yaml_lines = [
        f"name: {name}",
        f"cn_name: {cn_name or name}",
        "version: \"1.0.0\"",
        f"type: {agent_type}",
        f"port: {port}",
        "",
        "prompt:",
        "  system: |",
        "    你是一个医疗AI助手。",
        "  temperature: 0.3",
        "  max_tokens: 4096",
        "",
        "tools:",
    ]
    for t in tools:
        yaml_lines.append(f"  - name: {t['name']}")
        yaml_lines.append(f"    description: {t.get('description', '')}")
        default_handler = f"{name}.handlers.{t['name']}"
        yaml_lines.append(f"    handler: {t.get('handler', default_handler)}")

    if not tools:
        yaml_lines.append("  # - name: my_tool")
        yaml_lines.append("  #   description: 工具描述")
        yaml_lines.append("  #   handler: module.function")

    yaml_lines.extend(["", "guard:", "  triggers: []", "  high_risk_scenarios: []"])
    return "\n".join(yaml_lines)
