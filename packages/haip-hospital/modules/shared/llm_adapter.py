"""call_llm_structured compatibility adapter — bridges haip-core LLMProvider.

Ported from haip-0710 (agents.harness.llm.call_llm_structured).
Adapted: uses xhaip's LLMProvider abstraction (config/llm.yaml + Mock fallback),
so CI and offline runs never hit a real endpoint unless configured.

Usage (same contract as the original):
    result = call_llm_structured(prompt, agent="orthopedic-surgery",
                                 system_prompt=..., output_schema={...}, temperature=0.1)
    result == {"data": {...}} | {"error": str, ...}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_CACHE: dict[str, Any] = {}
_CONFIG_MTIME: float = 0.0


def _load_llm_config() -> dict[str, Any]:
    """Load config/llm.yaml from the repo root, with a small mtime cache."""
    global _CONFIG_MTIME
    cfg_path = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "config" / "llm.yaml"
    try:
        mtime = cfg_path.stat().st_mtime
        if mtime == _CONFIG_MTIME and _CONFIG_CACHE:
            return _CONFIG_CACHE
    except OSError:
        return {}

    import yaml
    try:
        with open(str(cfg_path), encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        _CONFIG_MTIME = mtime
        _CONFIG_CACHE = dict(raw.get("llm", {}) or {})
    except Exception:
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE


def _get_provider():
    """Create an LLMProvider; degrade to Mock when unconfigured or broken."""
    from haip.llm import LLMProvider
    from haip.llm.mock import MockProvider

    cfg = _load_llm_config()
    provider_name = cfg.get("provider", "mock")
    if provider_name != "mock" and not cfg.get("api_key"):
        return MockProvider({})
    try:
        return LLMProvider.from_config(cfg)
    except Exception:
        return MockProvider({})


def call_llm_structured(
    prompt: str,
    agent: str = "default",
    model: str = "",
    api_url: str = "",
    system_prompt: str = "你是一个医疗AI助手,请用中文回答 输出格式为JSON ",
    output_schema: dict | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    track: bool = True,
) -> dict[str, Any]:
    """Call LLM expecting JSON-structured output.

    Returns {"data": <parsed dict>, "raw": {...}} on success,
    or {"error": str, ...} on failure.
    """
    schema_instruction = ""
    if output_schema:
        schema_lines = "\n".join(f'  "{k}": "{v}"' for k, v in output_schema.items())
        schema_instruction = (
            "\n\n你必须以严格的JSON格式输出,不要包含markdown代码块标记,只输出纯JSON:\n"
            f"{{\n{schema_lines}\n}}"
        )

    provider = _get_provider()
    try:
        resp = provider.chat(
            messages=[
                {"role": "system", "content": system_prompt + schema_instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        return {"error": str(e)}

    content = (resp.content or "").strip()
    if not content:
        return {"error": "empty LLM response"}

    try:
        parsed = json.loads(content)
        return {"data": parsed, "raw": {
            "model": resp.model,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
        }}
    except json.JSONDecodeError:
        return {"error": "LLM output is not valid JSON", "raw_reply": content}
