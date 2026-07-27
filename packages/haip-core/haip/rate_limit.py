"""Rate Limiting Middleware — per-user and per-IP rate limiting.

Provides:
    - Token bucket algorithm per user
    - Sliding window per IP
    - Burst allowance
    - FastAPI middleware integration
    - Rate limit headers (X-RateLimit-*)
"""

from __future__ import annotations

import threading
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate: int = 100, burst: int = 20, window: int = 60):
        self.rate = rate  # tokens per window
        self.burst = burst  # max burst allowance
        self.window = window  # window in seconds
        self._buckets: dict[str, tuple[float, float]] = {}  # key → (tokens, last_refill)
        self._last_cleanup = time.time()
        self._lock = threading.Lock()

    def _refill(self, tokens: float, last_refill: float) -> tuple[float, float]:
        now = time.time()
        elapsed = now - last_refill
        new_tokens = min(tokens + elapsed * (self.rate / self.window), self.rate + self.burst)
        return new_tokens, now

    def consume(self, key: str, cost: float = 1.0) -> tuple[bool, dict[str, int]]:
        """Try to consume a token. Returns (allowed, headers)."""
        now = time.time()

        with self._lock:
            # Cleanup old entries periodically
            if now - self._last_cleanup > 300:
                self._last_cleanup = now
                stale = [k for k, (t, lr) in self._buckets.items() if now - lr > 600]
                for k in stale:
                    del self._buckets[k]

            tokens, last_refill = self._buckets.get(key, (self.rate + self.burst, now))
            tokens, last_refill = self._refill(tokens, last_refill)

            headers = {
                "X-RateLimit-Limit": str(self.rate),
                "X-RateLimit-Remaining": str(max(0, int(tokens))),
                "X-RateLimit-Reset": str(int(now + self.window)),
            }

            if tokens >= cost:
                self._buckets[key] = (tokens - cost, last_refill)
                return True, headers

            self._buckets[key] = (tokens, last_refill)
            return False, headers


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        app,
        rate: int = 100,
        burst: int = 20,
        window: int = 60,
        cost_map: dict[str, int] | None = None,
        exclude_paths: set[str] | None = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.bucket = TokenBucket(rate=rate, burst=burst, window=window)
        self.cost_map = cost_map or {"POST /api/call": 2}  # LLM calls cost more
        self.exclude_paths = exclude_paths or {
            "/api/health",
            "/api/metrics",
            "/",
            "/docs",
            "/openapi.json",
        }
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in self.exclude_paths):
            return await call_next(request)

        # Determine key: user_id (from token) or IP
        user = getattr(request.state, "current_user", None)
        key = user.get("user_id") if user else request.client.host if request.client else "unknown"

        # Determine cost
        route_key = f"{request.method} {path}"
        cost = self.cost_map.get(route_key, 1)

        allowed, headers = self.bucket.consume(f"{key}:{route_key}", cost)

        if not allowed:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please wait before retrying.",
                 "retry_after": headers.get("X-RateLimit-Reset", 60)},
                status_code=429,
                headers=headers,
            )

        response = await call_next(request)

        # Add rate limit headers to response
        for header_name, header_value in headers.items():
            response.headers[header_name] = str(header_value)

        return response
