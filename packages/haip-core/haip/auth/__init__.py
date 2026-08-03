"""Authentication service — user management + login/register API.

Provides:
    - Dual-backend user store: in-memory (test) / SQLite (production, HAIP_AUTH_DB)
    - FastAPI router for auth endpoints
    - Dependency injection helpers
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from haip.auth.jwt import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    revoke_refresh_token,
)
from haip.auth.middleware import get_current_user
from haip.auth.models import (
    PORTAL_IDENTITY_ROLES,
    LoginResponse,
    Permission,
    TokenRefreshRequest,
    TokenResponse,
    UserCreateRequest,
    UserInfo,
    UserLoginRequest,
)
from haip.auth.password import hash_password, validate_password_strength, verify_password
from haip.auth.rbac import get_permissions_for_roles, has_permission

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# 12 门户身份种子账户显示名 (R1a)
_DEMO_IDENTITY_NAMES: dict[str, str] = {
    "director": "院长",
    "secretary": "党委书记",
    "vice-director": "副院长",
    "dept-head": "科主任",
    "attending": "主治医师",
    "head-nurse": "护士长",
    "pharmacist": "临床药师",
    "anesthesiologist": "麻醉医师",
    "med-tech": "医技技师",
    "admin": "系统管理员",
    "resident": "住院医师",
    "intern": "实习医师",
}


def _default_db_path() -> str:
    """Resolve default SQLite path: HAIP_AUTH_DB env > data/auth.db."""
    env_path = os.environ.get("HAIP_AUTH_DB", "")
    if env_path:
        return env_path
    return str(_PROJECT_ROOT / "data" / "auth.db")


class AuthService:
    """Manages user accounts and authentication sessions.

    backend="memory": pure in-memory dict (default under HAIP_TEST_MODE).
    backend="sqlite": dict working-set mirrored to SQLite (db_path / HAIP_AUTH_DB).
    """

    def __init__(self, backend: str | None = None, db_path: str | None = None):
        if backend is None:
            if db_path is not None:
                backend = "sqlite"
            elif os.environ.get("HAIP_TEST_MODE") == "true":
                backend = "memory"
            else:
                backend = "sqlite"
        self.backend = backend
        self._users: dict[str, dict[str, Any]] = {}
        self._conn: sqlite3.Connection | None = None
        self._db_lock = threading.RLock()
        if backend == "sqlite":
            self.db_path = db_path or _default_db_path()
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
            self._load_from_db()

    # ── SQLite backend ──

    def _init_schema(self) -> None:
        assert self._conn is not None
        with self._db_lock:
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    id TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    display_name TEXT,
                    department TEXT DEFAULT '',
                    roles TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1
                )"""
            )
            self._conn.commit()

    def _load_from_db(self) -> None:
        assert self._conn is not None
        with self._db_lock:
            rows = self._conn.execute("SELECT * FROM users").fetchall()
        for row in rows:
            try:
                roles = json.loads(row["roles"])
            except (ValueError, TypeError):
                roles = ["doctor"]
            self._users[row["username"]] = {
                "id": row["id"],
                "username": row["username"],
                "password_hash": row["password_hash"],
                "email": row["email"],
                "display_name": row["display_name"],
                "department": row["department"] or "",
                "roles": roles,
                "created_at": row["created_at"] or "",
                "is_active": bool(row["is_active"]),
            }

    def _persist_user(self, user: dict[str, Any]) -> None:
        if self._conn is None:
            return
        with self._db_lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO users
                   (username, id, password_hash, email, display_name,
                    department, roles, created_at, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user["username"],
                    user["id"],
                    user["password_hash"],
                    user.get("email"),
                    user.get("display_name"),
                    user.get("department", ""),
                    json.dumps(user.get("roles", []), ensure_ascii=False),
                    user.get("created_at", ""),
                    1 if user.get("is_active", True) else 0,
                ),
            )
            self._conn.commit()

    def close(self) -> None:
        """Close the SQLite connection (no-op for memory backend)."""
        if self._conn is not None:
            with self._db_lock:
                self._conn.close()
            self._conn = None

    # ── User management ──

    def create_user(
        self,
        username: str,
        password: str,
        email: str | None = None,
        display_name: str | None = None,
        department: str | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new user account."""
        is_strong, msg = validate_password_strength(password)
        if not is_strong:
            raise ValueError(msg)

        user_id = uuid.uuid4().hex[:12]
        user_roles = roles or ["doctor"]
        user_permissions = get_permissions_for_roles(user_roles)

        user = {
            "id": user_id,
            "username": username,
            "password_hash": hash_password(password),
            "email": email,
            "display_name": display_name or username,
            "department": department or "",
            "roles": user_roles,
            "created_at": "",
            "is_active": True,
        }
        with self._db_lock:
            if username in self._users:
                raise ValueError(f"User '{username}' already exists")
            self._users[username] = user
            self._persist_user(user)
        return {
            "id": user_id,
            "username": username,
            "display_name": user["display_name"],
            "email": email,
            "department": department,
            "roles": user_roles,
            "permissions": user_permissions,
        }

    def seed_demo_identities(self) -> int:
        """Seed the 12 portal identity demo accounts (idempotent).

        Skipped in HAIP_ENV=production unless HAIP_SEED_DEMO_USERS is set.
        Returns the number of accounts created this call.
        """
        if (
            os.environ.get("HAIP_ENV", "development") == "production"
            and not os.environ.get("HAIP_SEED_DEMO_USERS")
        ):
            logger.info("生产环境未设置 HAIP_SEED_DEMO_USERS, 跳过演示账户种子")
            return 0
        demo_password = os.environ.get("HAIP_DEMO_PASSWORD")
        if not demo_password:
            if os.environ.get("HAIP_ENV") == "production":
                raise ValueError("HAIP_DEMO_PASSWORD 未设置，生产环境必须通过环境变量配置")
            logger.warning("HAIP_DEMO_PASSWORD 未设置, 使用默认密码 (安全风险!)")
            demo_password = "Demo@123456"
        created = 0
        for identity, role in PORTAL_IDENTITY_ROLES.items():
            if identity in self._users:
                continue
            try:
                self.create_user(
                    username=identity,
                    password=demo_password,
                    display_name=_DEMO_IDENTITY_NAMES.get(identity, identity),
                    department="演示",
                    roles=[role],
                )
                created += 1
            except ValueError as e:
                logger.warning("演示账户 %s 创建失败: %s", identity, e)
        if created:
            logger.info("已种子 %d 个门户身份演示账户", created)
        return created

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate a user and return user info with tokens."""
        user = self._users.get(username)
        if user is None or not user["is_active"]:
            raise ValueError("Invalid username or password")

        if not verify_password(password, user["password_hash"]):
            raise ValueError("Invalid username or password")

        roles = user["roles"]
        permissions = get_permissions_for_roles(roles)

        access_token, access_expire = create_access_token(
            user_id=user["id"],
            username=username,
            roles=roles,
            permissions=permissions,
        )
        refresh_token, _ = create_refresh_token(user_id=user["id"])

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": access_expire,
            "user": {
                "id": user["id"],
                "username": username,
                "display_name": user["display_name"],
                "email": user.get("email"),
                "department": user.get("department"),
                "roles": roles,
                "permissions": permissions,
                "tenant_id": None,
            },
        }

    def get_user(self, username: str) -> dict[str, Any] | None:
        """Get user by username."""
        return self._users.get(username)

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user by ID."""
        for user in self._users.values():
            if user["id"] == user_id:
                return user
        return None

    def list_users(self) -> list[dict[str, Any]]:
        """List all users (without password hashes)."""
        return [
            {
                "id": u["id"],
                "username": u["username"],
                "display_name": u["display_name"],
                "email": u.get("email"),
                "department": u.get("department"),
                "roles": u["roles"],
                "is_active": u["is_active"],
            }
            for u in self._users.values()
        ]

    def set_active(self, username: str, active: bool) -> bool:
        """Activate or deactivate a user account."""
        user = self._users.get(username)
        if user is None:
            return False
        user["is_active"] = active
        self._persist_user(user)
        return True

    def assign_role(self, username: str, role: str) -> bool:
        """Add a role to a user."""
        user = self._users.get(username)
        if user is None:
            return False
        if role not in user["roles"]:
            user["roles"].append(role)
            self._persist_user(user)
        return True

    def remove_role(self, username: str, role: str) -> bool:
        """Remove a role from a user."""
        user = self._users.get(username)
        if user is None:
            return False
        if role in user["roles"]:
            user["roles"].remove(role)
            self._persist_user(user)
        return True


# Global singleton (lazy — honors env at first use)
_auth_service: AuthService | None = None
_auth_service_lock = threading.Lock()


def get_auth_service() -> AuthService:
    """Dependency: get the AuthService singleton (lazy init)."""
    global _auth_service
    if _auth_service is None:
        with _auth_service_lock:
            if _auth_service is None:
                _auth_service = AuthService()
    return _auth_service


def reset_auth_service() -> None:
    """Close and drop the AuthService singleton (tests / re-config)."""
    global _auth_service
    with _auth_service_lock:
        if _auth_service is not None:
            _auth_service.close()
        _auth_service = None


# ── Auth API Endpoints ──


@auth_router.post("/register")
def register(
    body: UserCreateRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Register a new user account."""
    try:
        user = auth.create_user(
            username=body.username,
            password=body.password,
            email=body.email,
            display_name=body.display_name,
            department=body.department,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "user": user}


@auth_router.post("/login", response_model=LoginResponse)
def login(
    body: UserLoginRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Login with username and password."""
    try:
        result = auth.authenticate(body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return result


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(body: TokenRefreshRequest):
    """Get a new access token using a refresh token."""
    try:
        data = refresh_access_token(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    auth = get_auth_service()
    user = auth.get_user_by_id(data["user_id"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    access_token, access_expire = create_access_token(
        user_id=user["id"],
        username=user["username"],
        roles=user["roles"],
        permissions=get_permissions_for_roles(user["roles"]),
    )
    return {
        "access_token": access_token,
        "refresh_token": body.refresh_token,
        "token_type": "bearer",
        "expires_in": access_expire,
    }


@auth_router.get("/me", response_model=UserInfo)
def me(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Get current authenticated user info."""
    # Use JWT payload directly for correct user_id (test mode fix)
    user_id = current_user.get("user_id", "")
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from haip.auth.jwt import decode_token
            payload = decode_token(auth_header[7:])
            user_id = payload["sub"]
        except Exception:
            logger.debug("/me token 解析失败, 回退 current_user.user_id", exc_info=True)

    auth = get_auth_service()
    user = auth.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "email": user.get("email"),
        "department": user.get("department"),
        "roles": user["roles"],
        "permissions": get_permissions_for_roles(user["roles"]),
        "tenant_id": current_user.get("tenant_id"),
    }


@auth_router.post("/logout")
def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Logout — revoke current refresh token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if token:
        try:
            revoke_refresh_token(token)
        except Exception:
            logger.debug("logout revoke 失败 (token 已失效?)", exc_info=True)
    return {"status": "ok"}


@auth_router.get("/users")
def list_users(
    current_user: dict = Depends(get_current_user),
):
    """List all users (admin only)."""
    if not has_permission(current_user.get("roles", []), Permission.ADMIN_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    auth = get_auth_service()
    return auth.list_users()


@auth_router.get("/roles")
def list_roles(current_user: dict = Depends(get_current_user)):
    """List all roles."""
    from haip.auth.rbac import list_roles as _list_roles
    return _list_roles()
