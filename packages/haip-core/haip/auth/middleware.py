"""FastAPI middleware and dependencies for authentication."""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from haip.auth.jwt import decode_token

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(
    scheme_name="Bearer",
    description="JWT access token",
    auto_error=False,
)

# Paths that don't require authentication
PUBLIC_PATHS: set[str] = {
    "/",
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def is_public_path(path: str) -> bool:
    """Check if a path is publicly accessible without auth."""
    for public in PUBLIC_PATHS:
        if path == public or path.startswith(public + "/"):
            return True
    return False


DEV_USER: dict = {
    "user_id": "dev-user",
    "username": "dev",
    "roles": ["admin"],
    "permissions": ["agent:read", "agent:execute", "patient:read", "admin:*"],
    "tenant_id": None,
}

# 开发免登录仅限本机回环地址 — 远程匿名请求不得获得 admin 身份
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _allow_dev_autologin(client_host: str | None) -> bool:
    """是否允许开发模式免登录 (仅 loopback 客户端)."""
    return bool(client_host) and client_host in _LOOPBACK_HOSTS


@lru_cache(maxsize=1)
def _warn_dev_auth_bypass() -> bool:
    logger.warning(
        "开发模式免登录: 无 JWT 请求以内置 dev 用户放行 "
        "(设 HAIP_ENV=production 或 HAIP_STRICT_SECURITY=true 强制登录)")
    return True


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates JWT tokens on protected routes.

    Attaches decoded user info to request.state.current_user.
    Bypassed when HAIP_TEST_MODE=true or AUTH_ENABLED=false env vars are set.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        import os

        # Skip auth in test mode or when explicitly disabled
        if os.environ.get("HAIP_TEST_MODE") == "true" or os.environ.get("AUTH_ENABLED") == "false":
            request.state.current_user = {
                "user_id": "test-user",
                "username": "test",
                "roles": ["admin"],
                "permissions": ["agent:read", "agent:execute", "patient:read", "admin:*"],
                "tenant_id": None,
            }
            return await call_next(request)

        path = request.url.path

        if is_public_path(path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            from haip.security_baseline import is_production_mode
            client_host = request.client.host if request.client else None
            if not is_production_mode() and _allow_dev_autologin(client_host):
                # 开发模式免登录仅限本机: 前端尚无登录流程 (commercial-readiness R1),
                # 仅 loopback 客户端缺失 Authorization 时注入 dev 用户;
                # 远程/非回环匿名请求 401 (fail-visible), 携带非法 token 仍 401。
                _warn_dev_auth_bypass()
                request.state.current_user = dict(DEV_USER)
                return await call_next(request)
            return JSONResponse(
                {"detail": "Missing or invalid Authorization header"},
                status_code=401,
            )

        token = auth_header[7:]
        try:
            payload = decode_token(token)
        except Exception:
            return JSONResponse(
                {"detail": "Invalid or expired token"},
                status_code=401,
            )

        if payload.get("type") != "access":
            return JSONResponse(
                {"detail": "Not an access token"},
                status_code=401,
            )

        request.state.current_user = {
            "user_id": payload["sub"],
            "username": payload.get("username", ""),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", []),
            "tenant_id": payload.get("tenant_id"),
        }

        return await call_next(request)


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extracts the current authenticated user.

    Must be used after AuthMiddleware is installed.
    """
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_optional_user(request: Request) -> dict | None:
    """FastAPI dependency: extracts user if authenticated, None otherwise."""
    return getattr(request.state, "current_user", None)
