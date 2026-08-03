"""A2A Service Authentication — HMAC signing for inter-agent calls.

In production, A2A calls may be cross-container HTTP. This module
provides HMAC-based service-to-service authentication so each agent
can verify the caller's identity.

For the current in-process (importlib) dispatch, signatures are
optional but the infrastructure is ready for HTTP-based A2A.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any

_AGENT_SECRET_KEYS: dict[str, str] = {}


def generate_agent_secret() -> str:
    """Generate a random secret key for an agent."""
    return hashlib.sha256(os.urandom(64)).hexdigest()


def register_agent_secret(agent_name: str, secret: str | None = None) -> str:
    """Register or retrieve a secret key for an agent."""
    if agent_name not in _AGENT_SECRET_KEYS:
        _AGENT_SECRET_KEYS[agent_name] = secret or generate_agent_secret()
    return _AGENT_SECRET_KEYS[agent_name]


def get_agent_secret(agent_name: str) -> str | None:
    """Get the secret key for an agent."""
    return _AGENT_SECRET_KEYS.get(agent_name)


def sign_a2a_request(
    caller_agent: str,
    tool: str,
    params: dict[str, Any],
    timestamp: int | None = None,
) -> dict[str, str]:
    """Create HMAC signature headers for an A2A call.

    Returns headers dict:
        X-A2A-Agent: caller_agent
        X-A2A-Timestamp: unix timestamp
        X-A2A-Signature: HMAC-SHA256 signature
    """
    ts = timestamp or int(time.time())
    secret = get_agent_secret(caller_agent)
    if not secret:
        secret = register_agent_secret(caller_agent)

    payload = json.dumps({
        "agent": caller_agent,
        "tool": tool,
        "params": params,
        "timestamp": ts,
    }, sort_keys=True, ensure_ascii=False)

    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "X-A2A-Agent": caller_agent,
        "X-A2A-Timestamp": str(ts),
        "X-A2A-Signature": signature,
    }


def verify_a2a_request(
    caller_agent: str,
    tool: str,
    params: dict[str, Any],
    timestamp: str,
    signature: str,
    max_age_seconds: int = 300,
) -> bool:
    """Verify an A2A call's HMAC signature.

    Args:
        caller_agent: The agent claiming to make the call.
        tool: The tool being called.
        params: The parameters being passed.
        timestamp: Unix timestamp from header.
        signature: HMAC signature from header.
        max_age_seconds: Maximum allowed age of the request (replay protection).

    Returns:
        True if the signature is valid and not expired.
    """
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return False

    now = int(time.time())
    if abs(now - ts) > max_age_seconds:
        return False

    secret = get_agent_secret(caller_agent)
    if not secret:
        return False

    payload = json.dumps({
        "agent": caller_agent,
        "tool": tool,
        "params": params,
        "timestamp": ts,
    }, sort_keys=True, ensure_ascii=False)

    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def init_agent_secrets(agent_names: list[str]):
    """Initialize secrets for all agents at startup."""
    for name in agent_names:
        register_agent_secret(name)
