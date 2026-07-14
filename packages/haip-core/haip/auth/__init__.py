"""Authentication service — user management + login/register API.

Provides:
    - In-memory user store (PostgreSQL-backed in P1)
    - FastAPI router for auth endpoints
    - Dependency injection helpers
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from haip.auth.jwt import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    revoke_refresh_token,
)
from haip.auth.models import (
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
from haip.auth.middleware import get_current_user

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthService:
    """Manages user accounts and authentication sessions.

    In this phase (P0), uses an in-memory store. Will migrate to PostgreSQL in P1.
    """

    def __init__(self):
        self._users: dict[str, dict[str, Any]] = {}

    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        department: Optional[str] = None,
        roles: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Create a new user account."""
        if username in self._users:
            raise ValueError(f"User '{username}' already exists")

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
        self._users[username] = user
        return {
            "id": user_id,
            "username": username,
            "display_name": user["display_name"],
            "email": email,
            "department": department,
            "roles": user_roles,
            "permissions": user_permissions,
        }

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

    def get_user(self, username: str) -> Optional[dict[str, Any]]:
        """Get user by username."""
        return self._users.get(username)

    def get_user_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
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
        return True

    def assign_role(self, username: str, role: str) -> bool:
        """Add a role to a user."""
        user = self._users.get(username)
        if user is None:
            return False
        if role not in user["roles"]:
            user["roles"].append(role)
        return True

    def remove_role(self, username: str, role: str) -> bool:
        """Remove a role from a user."""
        user = self._users.get(username)
        if user is None:
            return False
        if role in user["roles"]:
            user["roles"].remove(role)
        return True


# Global singleton
_auth_service = AuthService()


def get_auth_service() -> AuthService:
    """Dependency: get the AuthService singleton."""
    return _auth_service


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
            pass

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
            pass
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
