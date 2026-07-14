"""Audit Middleware — FastAPI middleware for automatic API call auditing."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from haip.audit import get_audit_logger


class AuditMiddleware(BaseHTTPMiddleware):
    """Automatically records all API calls to the audit log."""

    def __init__(self, app, exclude_paths: Optional[set[str]] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or {
            "/api/health",
            "/api/history",
            "/api/knowledge/stats",
        }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        start = time.time()

        # Skip excluded paths
        if path in self.exclude_paths or path.startswith("/static/"):
            return await call_next(request)

        # Extract user info
        user = getattr(request.state, "current_user", None)
        user_id = user.get("user_id") if user else None
        username = user.get("username") if user else None
        ip = request.client.host if request.client else ""

        response = await call_next(request)

        status = "success" if response.status_code < 400 else "failure"
        elapsed_ms = round((time.time() - start) * 1000, 2)

        logger = get_audit_logger()
        logger.log(
            action=self._infer_action(path, request.method),
            resource=path,
            status=status,
            user_id=user_id,
            username=username,
            detail={
                "method": request.method,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
            },
            ip_address=ip,
        )

        return response

    @staticmethod
    def _infer_action(path: str, method: str) -> str:
        if "/api/auth/login" in path:
            return "login"
        if "/api/auth/logout" in path:
            return "logout"
        if "/api/call" in path:
            return "agent_call"
        if "/patients" in path:
            return "patient_access"
        if "/api/auth/register" in path:
            return "user_create"
        if "/api/auth/users" in path:
            return "user_manage"
        return "api_call"
