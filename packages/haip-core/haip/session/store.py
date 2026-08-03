"""Event/State Session Store — ADK 风格的 Agent 会话持久化.

核心概念:
  Event   — 原子通信单元，携带 content + state_delta + artifact_delta
  AgentSession — 单次对话线程，包含 events 列表 + state dict
  SessionService — SQLite 持久化后端
  InMemorySessionService — 内存后端 (测试/原型)

状态提交时机: yield Event → Runner 处理 → SessionService.append_event() 持久化
temp: 前缀: invocation 级变量，invocation 结束后自动丢弃.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── Event Model ──

@dataclass
class Event:
    """ADK 兼容的事件模型 — Agent 执行流中的原子单元."""

    id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    invocation_id: str = ""
    author: str = ""
    timestamp: float = field(default_factory=time.time)
    content: str = ""
    role: str = ""
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    partial: bool = False
    state_delta: dict[str, Any] = field(default_factory=dict)
    artifact_delta: dict[str, Any] = field(default_factory=dict)
    turn_complete: bool = False
    error: str = ""
    branch: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "invocation_id": self.invocation_id,
            "author": self.author, "timestamp": self.timestamp,
            "content": self.content, "role": self.role,
            "tool_name": self.tool_name, "tool_args": self.tool_args,
            "partial": self.partial,
            "state_delta": self.state_delta,
            "artifact_delta": self.artifact_delta,
            "turn_complete": self.turn_complete,
            "error": self.error, "branch": self.branch,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Event:
        return cls(
            id=d.get("id", ""), invocation_id=d.get("invocation_id", ""),
            author=d.get("author", ""), timestamp=d.get("timestamp", 0.0),
            content=d.get("content", ""), role=d.get("role", ""),
            tool_name=d.get("tool_name", ""), tool_args=d.get("tool_args", {}),
            partial=d.get("partial", False),
            state_delta=d.get("state_delta", {}),
            artifact_delta=d.get("artifact_delta", {}),
            turn_complete=d.get("turn_complete", False),
            error=d.get("error", ""), branch=d.get("branch", ""),
        )

    @classmethod
    def user_message(cls, content: str, invocation_id: str = "") -> Event:
        return cls(invocation_id=invocation_id, author="user", role="user",
                   content=content, turn_complete=True)

    @classmethod
    def assistant_message(cls, content: str, invocation_id: str = "",
                          partial: bool = False, turn_complete: bool = False,
                          state_delta: dict | None = None,
                          error: str = "") -> Event:
        return cls(invocation_id=invocation_id, author="assistant",
                   role="assistant", content=content, partial=partial,
                   turn_complete=turn_complete, state_delta=state_delta or {},
                   error=error)

    @classmethod
    def tool_result(cls, name: str, content: str, invocation_id: str = "",
                    state_delta: dict | None = None) -> Event:
        return cls(invocation_id=invocation_id, author=name, role="tool",
                   tool_name=name, content=content, state_delta=state_delta or {})


# ── AgentSession ──

@dataclass
class AgentSession:
    """Agent 会话 — 单次对话线程，包含状态 + 事件历史."""

    id: str
    app_name: str = "xhaip"
    user_id: str = "default"
    state: dict[str, Any] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    last_update: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def apply_delta(self, delta: dict[str, Any]) -> None:
        for k, v in delta.items():
            if v is None:
                self.state.pop(k, None)
            else:
                self.state[k] = v
        self.last_update = time.time()

    def clear_temp_state(self) -> None:
        for k in list(self.state):
            if k.startswith("temp:"):
                del self.state[k]

    def token_estimate(self) -> int:
        total = 0
        for evt in self.events:
            total += len(evt.content) // 3
        return total


# ── SQLite Schema ──

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS agent_sessions (
    id TEXT PRIMARY KEY,
    app_name TEXT NOT NULL DEFAULT 'xhaip',
    user_id TEXT NOT NULL DEFAULT 'default',
    state_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    last_update REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    invocation_id TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT '',
    timestamp REAL NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT '',
    tool_name TEXT NOT NULL DEFAULT '',
    tool_args_json TEXT NOT NULL DEFAULT '{}',
    partial INTEGER NOT NULL DEFAULT 0,
    state_delta_json TEXT NOT NULL DEFAULT '{}',
    artifact_delta_json TEXT NOT NULL DEFAULT '{}',
    turn_complete INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    branch TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_events_session ON agent_events(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_timestamp ON agent_events(session_id, timestamp);
"""


# ── SessionService ──

# Schema version for PRAGMA user_version tracking
SESSION_SERVICE_VERSION = 2

class SessionService:
    """SQLite 后端 Agent 会话持久化."""

    def __init__(self, db_path: str | Path = ":memory:"):
        self._db_path = str(db_path)
        self._lock = threading.Lock()

        with self._get_conn() as conn:
            conn.executescript(SCHEMA_V1)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            from haip.schema_version import ensure_version
            ensure_version(conn, SESSION_SERVICE_VERSION)

    @contextmanager
    def _get_conn(self) -> Iterator[sqlite3.Connection]:
        if self._db_path == ":memory:":
            if not hasattr(self, "_mem_conn") or self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:")
                self._mem_conn.row_factory = sqlite3.Row
                self._mem_conn.executescript(SCHEMA_V1)
            yield self._mem_conn
        else:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def create_session(self, app_name="xhaip", user_id="default",
                       state: dict | None = None, session_id: str | None = None) -> AgentSession:
        sid = session_id or f"ses_{uuid.uuid4().hex[:16]}"
        now = time.time()
        state_json = json.dumps(state or {}, ensure_ascii=False)
        meta_json = json.dumps({}, ensure_ascii=False)

        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO agent_sessions(id, app_name, user_id, state_json, metadata_json, created_at, last_update) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?)",
                    (sid, app_name, user_id, state_json, meta_json, now, now),
                )
                conn.commit()
        return AgentSession(id=sid, app_name=app_name, user_id=user_id,
                            state=state or {}, last_update=now)

    def get_session(self, session_id, app_name="xhaip", user_id="default") -> AgentSession | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent_sessions WHERE id = ? AND app_name = ? AND user_id = ?",
                (session_id, app_name, user_id),
            ).fetchone()
            if row is None:
                return None
            events = self._load_events(conn, session_id)
            return AgentSession(id=row["id"], app_name=row["app_name"],
                                user_id=row["user_id"],
                                state=json.loads(row["state_json"]),
                                metadata=json.loads(row["metadata_json"]),
                                events=events, last_update=row["last_update"])

    def get_or_create_session(self, session_id, app_name="xhaip", user_id="default") -> AgentSession:
        s = self.get_session(session_id, app_name, user_id)
        return s if s is not None else self.create_session(app_name, user_id, session_id=session_id)

    def list_sessions(self, app_name="xhaip", user_id="default", limit=50) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, created_at, last_update, state_json FROM agent_sessions "
                "WHERE app_name = ? AND user_id = ? ORDER BY last_update DESC LIMIT ?",
                (app_name, user_id, limit),
            ).fetchall()
            return [{"id": r["id"], "created_at": r["created_at"],
                     "last_update": r["last_update"],
                     "state_keys": list(json.loads(r["state_json"]).keys())} for r in rows]

    def delete_session(self, session_id) -> bool:
        with self._lock, self._get_conn() as conn:
            cur = conn.execute("DELETE FROM agent_sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cur.rowcount > 0

    def append_event(self, session: AgentSession, event: Event) -> None:
        if event.partial:
            return
        with self._lock, self._get_conn() as conn:
            if event.state_delta:
                session.apply_delta(event.state_delta)
                conn.execute(
                    "UPDATE agent_sessions SET state_json = ?, last_update = ? WHERE id = ?",
                    (json.dumps(session.state, ensure_ascii=False), time.time(), session.id),
                )
            conn.execute(
                """INSERT INTO agent_events(id, session_id, invocation_id, author, timestamp,
                       content, role, tool_name, tool_args_json, partial,
                       state_delta_json, artifact_delta_json, turn_complete, error, branch)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event.id, session.id, event.invocation_id, event.author,
                 event.timestamp, event.content, event.role,
                 event.tool_name, json.dumps(event.tool_args, ensure_ascii=False),
                 1 if event.partial else 0,
                 json.dumps(event.state_delta, ensure_ascii=False),
                 json.dumps(event.artifact_delta, ensure_ascii=False),
                 1 if event.turn_complete else 0, event.error, event.branch),
            )
            conn.commit()
        session.events.append(event)

    def _load_events(self, conn, session_id) -> list[Event]:
        rows = conn.execute(
            "SELECT * FROM agent_events WHERE session_id = ? AND partial = 0 ORDER BY timestamp ASC",
            (session_id,),
        ).fetchall()
        return [Event(id=r["id"], invocation_id=r["invocation_id"],
                      author=r["author"], timestamp=r["timestamp"],
                      content=r["content"], role=r["role"],
                      tool_name=r["tool_name"],
                      tool_args=json.loads(r["tool_args_json"]),
                      state_delta=json.loads(r["state_delta_json"]),
                      artifact_delta=json.loads(r["artifact_delta_json"]),
                      turn_complete=bool(r["turn_complete"]),
                      error=r["error"], branch=r["branch"]) for r in rows]

    def rewind_session(self, session: AgentSession, keep_events: int) -> None:
        if keep_events >= len(session.events):
            return
        new_state: dict[str, Any] = {}
        for evt in session.events[:keep_events]:
            for k, v in evt.state_delta.items():
                if v is None:
                    new_state.pop(k, None)
                else:
                    new_state[k] = v
        with self._lock, self._get_conn() as conn:
            delete_ids = [e.id for e in session.events[keep_events:]]
            if delete_ids:
                placeholders = ",".join("?" * len(delete_ids))
                conn.execute(
                    f"DELETE FROM agent_events WHERE id IN ({placeholders})",
                    delete_ids,
                )
            conn.execute(
                "UPDATE agent_sessions SET state_json = ?, last_update = ? WHERE id = ?",
                (json.dumps(new_state, ensure_ascii=False), time.time(), session.id),
            )
            conn.commit()
        session.state = new_state
        session.events = session.events[:keep_events]

    def begin_invocation(self, session: AgentSession) -> str:
        return f"inv_{uuid.uuid4().hex[:12]}"

    def end_invocation(self, session: AgentSession) -> None:
        session.clear_temp_state()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE agent_sessions SET state_json = ?, last_update = ? WHERE id = ?",
                (json.dumps(session.state, ensure_ascii=False), time.time(), session.id),
            )
            conn.commit()

    def close(self) -> None:
        if hasattr(self, "_mem_conn") and self._mem_conn is not None:
            self._mem_conn.close()
            self._mem_conn = None


# ── InMemorySessionService ──

class InMemorySessionService:
    """无持久化的会话服务 — 带 LRU + TTL 淘汰.

    会话按 (user_id, session_id) 复合键隔离 — 与 SQLite 后端相同的
    user 作用域语义 (IDOR 修复): 同名 session_id 在不同用户间互不可见。
    """

    def __init__(self, max_sessions: int = 1000, session_ttl: float = 3600.0):
        self._sessions: dict[str, AgentSession] = {}
        self._access_times: dict[str, float] = {}
        self._max_sessions = max_sessions
        self._session_ttl = session_ttl
        self._lock = threading.Lock()

    @staticmethod
    def _key(user_id: str, session_id: str) -> str:
        return f"{user_id}:{session_id}"

    def _evict_expired(self, now: float) -> None:
        expired = [
            sid for sid, t in self._access_times.items()
            if now - t > self._session_ttl
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._access_times.pop(sid, None)

    def _evict_lru(self) -> None:
        while len(self._sessions) >= self._max_sessions and self._access_times:
            oldest = min(self._access_times, key=self._access_times.get)
            self._sessions.pop(oldest, None)
            self._access_times.pop(oldest, None)

    def create_session(self, app_name="xhaip", user_id="default",
                       state=None, session_id=None) -> AgentSession:
        sid = session_id or f"ses_{uuid.uuid4().hex[:12]}"
        s = AgentSession(id=sid, app_name=app_name, user_id=user_id, state=state or {})
        with self._lock:
            self._evict_expired(time.time())
            if len(self._sessions) >= self._max_sessions:
                self._evict_lru()
            key = self._key(user_id, sid)
            self._sessions[key] = s
            self._access_times[key] = time.time()
        return s

    def get_session(self, session_id, app_name="xhaip", user_id="default") -> AgentSession | None:
        key = self._key(user_id, session_id)
        s = self._sessions.get(key)
        if s is not None:
            self._access_times[key] = time.time()
        return s

    def get_or_create_session(self, session_id, app_name="xhaip", user_id="default") -> AgentSession:
        s = self.get_session(session_id, app_name, user_id)
        return s if s is not None else self.create_session(app_name, user_id, session_id=session_id)

    def list_sessions(self, app_name="xhaip", user_id="default", limit=50) -> list[dict]:
        return [{"id": s.id, "last_update": s.last_update,
                 "state_keys": list(s.state.keys())}
                for s in list(self._sessions.values())
                if s.user_id == user_id][:limit]

    def delete_session(self, session_id) -> bool:
        with self._lock:
            key = next((k for k, s in self._sessions.items() if s.id == session_id), None)
            if key is None:
                return False
            self._access_times.pop(key, None)
            self._sessions.pop(key, None)
            return True

    def append_event(self, session: AgentSession, event: Event) -> None:
        if event.partial:
            return
        with self._lock:
            if event.state_delta:
                session.apply_delta(event.state_delta)
            session.events.append(event)
            self._access_times[self._key(session.user_id, session.id)] = time.time()

    def rewind_session(self, session: AgentSession, keep_events: int) -> None:
        if keep_events >= len(session.events):
            return
        new_state = {}
        for evt in session.events[:keep_events]:
            for k, v in evt.state_delta.items():
                if v is None:
                    new_state.pop(k, None)
                else:
                    new_state[k] = v
        session.state = new_state
        session.events = session.events[:keep_events]

    def begin_invocation(self, session: AgentSession) -> str:
        return f"inv_{uuid.uuid4().hex[:12]}"

    def end_invocation(self, session: AgentSession) -> None:
        session.clear_temp_state()

    def close(self) -> None:
        self._sessions.clear()
        self._access_times.clear()


# ── 消息转换 ──

def events_to_messages(
    events: list[Event], system_prompt: str = "",
    max_turns: int = 0, summarize_older: bool = False,
) -> list[dict[str, Any]]:
    """将 events 转换为 LLM messages 格式."""
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    dialog_events = [e for e in events if e.role in ("user", "assistant", "tool")]

    if max_turns > 0:
        user_indices = [i for i, e in enumerate(dialog_events) if e.role == "user"]
        if len(user_indices) > max_turns:
            dialog_events = dialog_events[user_indices[-max_turns]:]

    for evt in dialog_events:
        if evt.role == "user":
            messages.append({"role": "user", "content": evt.content})
        elif evt.role == "assistant":
            messages.append({"role": "assistant", "content": evt.content})
        elif evt.role == "tool":
            messages.append({"role": "tool", "tool_call_id": evt.id, "content": evt.content})

    return messages
