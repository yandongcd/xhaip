"""A2A Router — 从 YAML Agent 定义自动构建路由表.

与老系统的区别:
  - 老系统: A2A_AGENTS 硬编码 15 个映射, 新增 Agent 需手工修改
  - 新系统: 从 DomainPlugin 注册表自动生成, 新增 Agent 只需写 YAML
"""

from __future__ import annotations

from haip.agent import list_all


def build_routes() -> dict[str, dict]:
    """从已注册的 DomainPlugin 列表自动构建路由表.
    
    Returns:
        {agent_name: {"module": handler_module, "tools": {tool_name: handler_func}}}
    """
    routes: dict[str, dict] = {}
    for name, plugin in list_all().items():
        if not plugin.tools:
            continue
        # 提取所有 handler 所在的模块 (取第一个 handler 的模块路径)
        modules: set[str] = set()
        tool_map: dict[str, str] = {}
        for t in plugin.tools:
            module_name, func_name = t.handler.rsplit(".", 1)
            modules.add(module_name)
            tool_map[t.name] = func_name
        routes[name] = {
            "modules": [f"haip_hospital.modules.{m}" for m in modules],
            "tools": tool_map,
        }
    return routes


def resolve_handler(agent_name: str, tool_name: str) -> list[str] | None:
    """解析 Agent 的 tool 对应的模块路径和函数名.
    
    Returns:
        (module_path, function_name) 或 None
    """
    from haip.agent import get
    plugin = get(agent_name)
    if plugin is None:
        return None
    for t in plugin.tools:
        if t.name == tool_name:
            return t.handler.rsplit(".", 1)
    return None
