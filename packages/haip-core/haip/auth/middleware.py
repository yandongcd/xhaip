"""FastAPI middleware and dependencies for authentication."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from haip.auth.jwt import decode_token

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


async def get_optional_user(request: Request) -> Optional[dict]:
    """FastAPI dependency: extracts user if authenticated, None otherwise."""
    return getattr(request.state, "current_user", None)
