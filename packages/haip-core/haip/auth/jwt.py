"""JWT token creation, validation, and refresh."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import jwt

logger = logging.getLogger(__name__)

_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
if not _SECRET_KEY:
    if os.environ.get("HAIP_ENV") == "production":
        from haip.security_baseline import SecurityBaselineError
        raise SecurityBaselineError("JWT_SECRET_KEY 未设置，生产环境必须通过环境变量配置")
    _SECRET_KEY = "xhaip-dev-secret-change-in-production"
    if os.environ.get("HAIP_TEST_MODE") != "true" and os.environ.get("AUTH_ENABLED") != "false":
        logger.warning("JWT_SECRET_KEY 未设置, 正在使用开发默认密钥 — 生产环境必须通过环境变量配置")
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE = int(os.environ.get("JWT_ACCESS_EXPIRE", "900"))  # 15 minutes
_REFRESH_TOKEN_EXPIRE = int(os.environ.get("JWT_REFRESH_EXPIRE", "604800"))  # 7 days

# In-memory refresh token blacklist (PostgreSQL-backed in P1)
_revoked_refresh_tokens: set[str] = set()
_revoke_lock = threading.Lock()


def create_access_token(
    user_id: str,
    username: str,
    roles: list[str],
    permissions: list[str],
    tenant_id: str | None = None,
    expires_in: int | None = None,
) -> tuple[str, int]:
    """Create an access token and return (token, seconds_until_expiry)."""
    expire_seconds = expires_in or _ACCESS_TOKEN_EXPIRE
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "roles": roles,
        "permissions": permissions,
        "tenant_id": tenant_id,
        "type": "access",
        "iat": now,
        "exp": now + expire_seconds,
    }
    token = jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)
    return token, expire_seconds


def create_refresh_token(
    user_id: str,
    expires_in: int | None = None,
) -> tuple[str, int]:
    """Create a refresh token and return (token, seconds_until_expiry)."""
    expire_seconds = expires_in or _REFRESH_TOKEN_EXPIRE
    now = int(time.time())
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + expire_seconds,
        "jti": _generate_jti(),
    }
    token = jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)
    return token, expire_seconds


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises on invalid/expired."""
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Validate refresh token and return new token pair data."""
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise ValueError("Token is not a refresh token")

    jti = payload.get("jti", "")
    if jti in _revoked_refresh_tokens:
        raise ValueError("Refresh token has been revoked")

    return {
        "user_id": payload["sub"],
        "jti": jti,
    }


def revoke_refresh_token(refresh_token: str) -> None:
    """Revoke a refresh token so it cannot be used again."""
    try:
        payload = decode_token(refresh_token)
        jti = payload.get("jti", "")
        if jti:
            with _revoke_lock:
                _revoked_refresh_tokens.add(jti)
    except Exception:
        logger.debug("refresh token 吊销失败 (token 已失效?)", exc_info=True)


def _generate_jti() -> str:
    """Generate a unique JWT ID."""
    import uuid
    return uuid.uuid4().hex
