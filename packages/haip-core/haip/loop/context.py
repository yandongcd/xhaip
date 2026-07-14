"""InvocationContext — ADK 风格的执行上下文.

包装 session + agent + services，提供统一的 state 访问接口.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from haip.session.store import AgentSession, Event


@dataclass
class InvocationContext:
    """执行上下文 — 在一次 invocation 中贯穿所有 Agent 操作.

    提供:
      - 统一的 state 读写 (temp: 前缀支持)
      - session events 访问
      - 便捷方法: save_state(), yield_event()
    """

    session: AgentSession
    agent_name: str = ""
    invocation_id: str = ""
    session_service: Any = None  # SessionService | InMemorySessionService

    # 累积的 state_delta (本轮 invocation 未提交的变更)
    _pending_delta: dict[str, Any] = field(default_factory=dict)
    # 最近产生的事件 (用于后续 yield)
    _last_event: Event | None = None

    @property
    def state(self) -> dict[str, Any]:
        """返回 agent 视角的 state (包含当期 invocation 未提交的变更)."""
        merged = dict(self.session.state)
        merged.update(self._pending_delta)
        return merged

    def get_state(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """写入 state (暂存到 pending_delta，直到 Event yield 后提交)."""
        self._pending_delta[key] = value

    def delete_state(self, key: str) -> None:
        self._pending_delta[key] = None  # None = 删除标记

    def commit_event(self, event: Event) -> None:
        """将 pending_delta 合并到 event 并提交到 SessionService."""
        if self._pending_delta:
            event.state_delta.update(self._pending_delta)
            self._pending_delta.clear()

        if self.session_service is not None:
            self.session_service.append_event(self.session, event)

        self._last_event = event

    def save_artifact(self, name: str, data: Any) -> None:
        """保存文件 artifact (暂存到 pending)."""
        self._pending_delta[f"artifact:{name}"] = data

    def list_artifacts(self) -> list[str]:
        return [k[9:] for k in self.state if k.startswith("artifact:")]

    def get_artifact(self, name: str) -> Any:
        return self.state.get(f"artifact:{name}")
