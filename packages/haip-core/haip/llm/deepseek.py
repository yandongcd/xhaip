"""DeepSeek Provider — OpenAI 兼容 API."""

from __future__ import annotations

import json
import time
from typing import Any, Iterator

import httpx

from haip.llm import ChatResponse, LLMProvider, ToolCall


class DeepSeekProvider(LLMProvider):
    def __init__(
        self,
        api_key: str = "",
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _build_body(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
        stream: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            body["tools"] = self._convert_tools(tools)
            body["tool_choice"] = "auto"
        return body

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": t} for t in tools
        ]

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        body = self._build_body(messages, tools, temperature, max_tokens, stream=False)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = ""
        for attempt in range(self.max_retries):
            try:
                resp = httpx.post(
                    url, json=body, headers=headers,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                return self._parse_response(data)
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    time.sleep(min(2 ** attempt, 8))
        return ChatResponse(content=f"LLM error after {self.max_retries} retries: {last_error}")

    def _parse_response(self, data: dict[str, Any]) -> ChatResponse:
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        tool_calls = []
        for tc in msg.get("tool_calls", []):
            func = tc.get("function", {})
            args_str = func.get("arguments", "{}")
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(
                id=tc.get("id", ""),
                name=func.get("name", ""),
                arguments=args,
            ))
        return ChatResponse(
            content=msg.get("content") or "",
            tool_calls=tool_calls,
            model=data.get("model", self.model),
            input_tokens=(data.get("usage") or {}).get("prompt_tokens", 0),
            output_tokens=(data.get("usage") or {}).get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Iterator[ChatResponse]:
        body = self._build_body(messages, tools, temperature, max_tokens, stream=True)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.stream("POST", url, json=body, headers=headers, timeout=self.timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        yield self._parse_response(data)
                    except json.JSONDecodeError:
                        continue
