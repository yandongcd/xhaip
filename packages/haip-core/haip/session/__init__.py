"""Event/State Session — ADK 风格事件驱动的 Agent 会话持久化.

提供:
    - Event: 原子通信单元 (content + state_delta + artifact_delta)
    - AgentSession: 单次对话线程
    - SessionService: SQLite 持久化后端
    - InMemorySessionService: 内存后端 (测试/原型)
    - events_to_messages: 转换为 LLM messages 格式
    - SessionManager: 用户登录会话管理 (user_id, ip, expiry)
"""

from haip.session.store import (
    Event,
    AgentSession as Session,
    SessionService,
    InMemorySessionService,
    events_to_messages,
)

from haip.session.manager import SessionManager, get_session_manager

__all__ = [
    "Event",
    "Session",
    "SessionService",
    "InMemorySessionService",
    "events_to_messages",
    "SessionManager",
    "get_session_manager",
]
