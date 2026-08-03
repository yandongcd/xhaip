"""Session Management — user login session tracking.

Provides:
    - Session creation on login
    - Session validation
    - Concurrent session control (max sessions per user)
    - Session activity tracking (last active, IP, user agent)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionRecord:
    """A user login session record."""

    session_id: str
    user_id: str
    username: str
    created_at: float
    last_active: float
    expires_at: float
    ip_address: str = ""
    user_agent: str = ""
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """Manages user login sessions."""

    def __init__(
        self,
        session_ttl_seconds: int = 3600,
        max_sessions_per_user: int = 5,
        cleanup_interval: int = 300,
    ):
        self._sessions: dict[str, SessionRecord] = {}
        self._by_user: dict[str, list[str]] = {}
        self.session_ttl = session_ttl_seconds
        self.max_sessions = max_sessions_per_user
        self._last_cleanup = time.time()
        self.cleanup_interval = cleanup_interval

    def create(
        self,
        user_id: str,
        username: str,
        ip_address: str = "",
        user_agent: str = "",
        ttl: int | None = None,
    ) -> SessionRecord:
        self._maybe_cleanup()

        existing = self._by_user.get(user_id, [])
        if len(existing) >= self.max_sessions:
            oldest_id = existing[0]
            self.destroy(oldest_id)

        session_id = uuid.uuid4().hex
        now = time.time()
        expire_seconds = ttl or self.session_ttl

        session = SessionRecord(
            session_id=session_id,
            user_id=user_id,
            username=username,
            created_at=now,
            last_active=now,
            expires_at=now + expire_seconds,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self._sessions[session_id] = session
        self._by_user.setdefault(user_id, []).append(session_id)
        return session

    def get(self, session_id: str) -> SessionRecord | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if time.time() > session.expires_at or not session.is_active:
            self.destroy(session_id)
            return None
        return session

    def touch(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.last_active = time.time()
        return True

    def destroy(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session:
            user_sessions = self._by_user.get(session.user_id, [])
            if session_id in user_sessions:
                user_sessions.remove(session_id)

    def destroy_all_for_user(self, user_id: str):
        for sid in list(self._by_user.get(user_id, [])):
            self.destroy(sid)

    def _maybe_cleanup(self):
        now = time.time()
        if now - self._last_cleanup < self.cleanup_interval:
            return
        self._last_cleanup = now
        expired = [
            sid for sid, s in self._sessions.items()
            if now > s.expires_at or not s.is_active
        ]
        for sid in expired:
            self.destroy(sid)

    def stats(self) -> dict[str, Any]:
        self._maybe_cleanup()
        active = sum(1 for s in self._sessions.values() if s.is_active)
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active,
            "unique_users": len(self._by_user),
            "session_ttl": self.session_ttl,
        }

    def list_user_sessions(self, user_id: str) -> list[SessionRecord]:
        sessions = []
        for sid in list(self._by_user.get(user_id, [])):
            s = self._sessions.get(sid)
            if s and s.is_active:
                sessions.append(s)
        return sessions


# Global singleton
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    return _session_manager
