"""LLM Gateway / Chat Proxy — unified LLM access with rate limiting, caching, fallback.

Provides:
    - Multi-provider routing (DeepSeek, OpenAI-compatible)
    - Token usage tracking and cost monitoring
    - Rate limiting per user/tenant
    - Response caching for common queries
    - Fallback chain on provider failure
    - Model switching via configuration
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from haip.llm import DEFAULT_MAX_TOKENS


@dataclass
class LLMGatewayConfig:
    """Configuration for the LLM Gateway."""
    primary_provider: str = "deepseek"
    fallback_providers: list[str] = field(default_factory=list)
    rate_limit_per_minute: int = 100
    cache_ttl_seconds: int = 300  # 5 minutes
    max_retries: int = 2
    timeout_seconds: int = 30


@dataclass
class GatewayStats:
    """Gateway usage statistics."""
    total_requests: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    fallback_uses: int = 0
    last_request_time: float = 0.0


class LLMGateway:
    """Unified LLM access layer with rate limiting, caching, and fallback.

    This replaces the previous direct DeepSeek call pattern with a managed
    gateway that supports:
    - Per-user rate limiting
    - Response caching (identical queries returned from cache)
    - Automatic fallback to secondary providers
    - Token cost tracking
    - Circuit breaker on repeated failures
    """

    def __init__(self, config: LLMGatewayConfig | None = None):
        self.config = config or LLMGatewayConfig()
        self.stats = GatewayStats()
        self._cache: dict[str, tuple[float, Any]] = {}
        self._rate_tracker: dict[str, list[float]] = {}
        self._rate_tracker_last_cleanup: float = 0.0
        self._failure_counts: dict[str, int] = {}
        self._circuit_open: set[str] = set()
        self._circuit_reset_time: dict[str, float] = {}

    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit."""
        now = time.time()
        window = now - 60  # 1-minute sliding window

        # Periodic cleanup of stale keys (every 300s)
        if now - self._rate_tracker_last_cleanup > 300:
            self._rate_tracker_last_cleanup = now
            stale = [k for k, ts in self._rate_tracker.items()
                     if not ts or max(ts) < window]
            for k in stale:
                del self._rate_tracker[k]

        timestamps = self._rate_tracker.get(user_id, [])
        timestamps = [t for t in timestamps if t > window]
        timestamps.append(now)
        self._rate_tracker[user_id] = timestamps
        return len(timestamps) <= self.config.rate_limit_per_minute

    def _check_cache(self, cache_key: str) -> Any | None:
        """Check response cache."""
        if cache_key in self._cache:
            ts, result = self._cache[cache_key]
            if time.time() - ts < self.config.cache_ttl_seconds:
                self.stats.cache_hits += 1
                return result
        self.stats.cache_misses += 1
        return None

    def _set_cache(self, cache_key: str, result: Any):
        """Store in response cache."""
        self._cache[cache_key] = (time.time(), result)
        # Prune old entries
        if len(self._cache) > 1000:
            now = time.time()
            self._cache = {
                k: v for k, v in self._cache.items()
                if now - v[0] < self.config.cache_ttl_seconds * 2
            }

    def _cache_key(self, messages: list[dict], tools: list | None = None) -> str:
        """Generate a cache key from messages."""
        import hashlib
        import json
        payload = json.dumps({"msgs": messages, "tools": tools}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()[:32]

    def _is_circuit_open(self, provider: str) -> bool:
        """Check if circuit breaker is open for a provider."""
        if provider not in self._circuit_open:
            return False
        reset_time = self._circuit_reset_time.get(provider, 0)
        if time.time() > reset_time:
            self._circuit_open.discard(provider)
            self._failure_counts[provider] = 0
            return False
        return True

    def _record_failure(self, provider: str):
        """Record a provider failure and potentially open circuit breaker."""
        self._failure_counts[provider] = self._failure_counts.get(provider, 0) + 1
        if self._failure_counts[provider] >= 5:
            self._circuit_open.add(provider)
            self._circuit_reset_time[provider] = time.time() + 30  # 30s cooldown

    def _record_success(self, provider: str):
        """Record success and reset failure counter."""
        self._failure_counts[provider] = 0
        self._circuit_open.discard(provider)

    def chat(
        self,
        messages: list[dict],
        *,
        tools: list | None = None,
        temperature: float = 0.3,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        user_id: str = "default",
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Chat with LLM through the gateway.

        Returns:
            {"content": str, "tool_calls": list, "tokens_in": int, "tokens_out": int,
             "provider": str, "cached": bool}
        """
        self.stats.total_requests += 1
        self.stats.last_request_time = time.time()

        # Rate limit check
        if not self._check_rate_limit(user_id):
            return {"content": "", "error": "Rate limit exceeded", "provider": "gateway"}

        # Cache check
        if use_cache:
            ck = self._cache_key(messages, tools)
            cached = self._check_cache(ck)
            if cached is not None:
                cached["cached"] = True
                return cached

        # Try primary provider
        from haip.llm import LLMProvider

        providers = [self.config.primary_provider] + self.config.fallback_providers
        last_error = None

        for provider_name in providers:
            if self._is_circuit_open(provider_name):
                continue

            try:
                provider_config = self._get_provider_config(provider_name)
                llm = LLMProvider.from_config(provider_config)
                resp = llm.chat(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                self._record_success(provider_name)
                self.stats.total_tokens_in += getattr(resp, "input_tokens", 0)
                self.stats.total_tokens_out += getattr(resp, "output_tokens", 0)

                result = {
                    "content": resp.content,
                    "tool_calls": [
                        {"name": tc.name, "arguments": tc.arguments}
                        for tc in (resp.tool_calls or [])
                    ] if resp.tool_calls else [],
                    "tokens_in": getattr(resp, "input_tokens", 0),
                    "tokens_out": getattr(resp, "output_tokens", 0),
                    "provider": provider_name,
                    "cached": False,
                }

                if use_cache:
                    self._set_cache(self._cache_key(messages, tools), result)

                return result

            except Exception as e:
                last_error = str(e)
                self._record_failure(provider_name)
                if provider_name == self.config.primary_provider:
                    self.stats.fallback_uses += 1
                continue

        self.stats.errors += 1
        return {"content": "", "error": f"All providers failed. Last: {last_error}", "provider": "gateway"}

    def _get_provider_config(self, provider_name: str) -> dict[str, Any]:
        """Get LLM provider configuration."""
        from pathlib import Path

        import yaml

        # Default configs — never fall through to mock in production
        configs = {
            "deepseek": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "api_key": "${DEEPSEEK_API_KEY}",
                "api_base": "https://api.deepseek.com/v1",
                "temperature": 0.3,
                "max_tokens": DEFAULT_MAX_TOKENS,
            },
            "fail-closed": {
                "provider": "fail-closed",
                "mode": "production",
            },
        }

        # Remove "mock" as default — this was the dangerous fallback
        mock_config = configs.pop("mock", None)

        # Try loading from config file
        config_path = (
            Path(__file__).resolve().parent.parent.parent.parent / "config" / "llm.yaml"
        )
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            if "llm" in cfg:
                configs[provider_name] = cfg["llm"]

        return configs.get(provider_name, configs["fail-closed"])


# Global singleton
_singleton_state: dict = {}


def get_llm_gateway() -> LLMGateway:
    """Get the global LLM gateway singleton."""
    from haip._singleton import locked_singleton
    return locked_singleton(LLMGateway, _singleton_state, "gateway")
