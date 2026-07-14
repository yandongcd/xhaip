"""Event/State Session — ADK 风格事件驱动的会话持久化 (Agent 会话, 非用户 login session).

与 haip.session (auth session) 互补:
  - haip.session: 用户登录会话 (user_id, ip, expiry)
  - haip.session.store: Agent 对话会话 (events, state_delta, memory)
"""

from haip.session.store import (
    Event, Session as AgentSession, SessionService, InMemorySessionService,
    events_to_messages,
)

__all__ = [
    "Event", "AgentSession", "SessionService", "InMemorySessionService",
    "events_to_messages",
]
