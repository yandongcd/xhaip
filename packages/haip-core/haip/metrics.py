"""Prometheus metrics — HTTP counters, agent call metrics, LLM usage.

Provides:
    - Request counter by endpoint/method/status
    - Agent call counter by agent/tool/status
    - Agent call duration histogram
    - LLM token usage counter
    - Guard trigger counter
    - Active user gauge
    - FastAPI /metrics endpoint
"""

from __future__ import annotations


from fastapi import FastAPI

# Optional: prometheus_client may not be installed
PROMETHEUS_AVAILABLE = False
try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    pass


class MetricsCollector:
    """Prometheus-based metrics collector. Falls back to no-op if not installed."""

    def __init__(self):
        self._enabled = PROMETHEUS_AVAILABLE
        if not self._enabled:
            return

        self.http_requests = Counter(
            "xhaip_http_requests_total",
            "Total HTTP requests",
            ["endpoint", "method", "status"],
        )
        self.http_duration = Histogram(
            "xhaip_http_duration_seconds",
            "HTTP request duration",
            ["endpoint", "method"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )
        self.agent_calls = Counter(
            "xhaip_agent_calls_total",
            "Total agent tool calls",
            ["agent", "tool", "status"],
        )
        self.agent_duration = Histogram(
            "xhaip_agent_duration_seconds",
            "Agent call duration",
            ["agent", "tool"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
        self.llm_tokens = Counter(
            "xhaip_llm_tokens_total",
            "Total LLM token usage",
            ["model", "direction"],
        )
        self.guard_checks = Counter(
            "xhaip_guard_checks_total",
            "Total guard safety checks",
            ["agent", "result"],
        )
        self.active_users = Gauge(
            "xhaip_active_users",
            "Number of active user sessions",
        )

    def record_http(self, endpoint: str, method: str, status: int, duration_s: float):
        if not self._enabled:
            return
        self.http_requests.labels(endpoint=endpoint, method=method, status=str(status)).inc()
        self.http_duration.labels(endpoint=endpoint, method=method).observe(duration_s)

    def record_agent_call(self, agent: str, tool: str, status: str, duration_s: float):
        if not self._enabled:
            return
        self.agent_calls.labels(agent=agent, tool=tool, status=status).inc()
        self.agent_duration.labels(agent=agent, tool=tool).observe(duration_s)

    def record_llm_tokens(self, model: str, input_tokens: int, output_tokens: int):
        if not self._enabled:
            return
        if input_tokens > 0:
            self.llm_tokens.labels(model=model, direction="input").inc(input_tokens)
        if output_tokens > 0:
            self.llm_tokens.labels(model=model, direction="output").inc(output_tokens)

    def record_guard_check(self, agent: str, passed: bool):
        if not self._enabled:
            return
        result = "pass" if passed else "fail"
        self.guard_checks.labels(agent=agent, result=result).inc()

    def set_active_users(self, count: int):
        if not self._enabled:
            return
        self.active_users.set(count)

    def get_metrics_response(self):
        """Generate Prometheus metrics text response."""
        if not self._enabled:
            return "Prometheus client not installed. Install: pip install prometheus-client", 200
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


# Global singleton
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _metrics


class MetricsMiddleware:
    """FastAPI middleware that records HTTP request metrics automatically."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time
        start = time.monotonic()

        async def _send(message):
            if message["type"] == "http.response.start":
                status = message["status"]
                endpoint = scope.get("path", "/")
                method = scope.get("method", "GET")
                duration = time.monotonic() - start
                _metrics.record_http(endpoint=endpoint, method=method, status=status, duration_s=duration)
            await send(message)

        await self.app(scope, receive, _send)


def setup_metrics(app: FastAPI, prefix: str = "/api/metrics"):
    """Register /metrics endpoint on the FastAPI app."""

    def metrics_endpoint():
        data, status_code, headers = get_metrics().get_metrics_response()
        from fastapi.responses import Response
        return Response(content=data, status_code=status_code, media_type=headers.get("Content-Type"))

    app.add_api_route(f"{prefix}", metrics_endpoint, methods=["GET"])
