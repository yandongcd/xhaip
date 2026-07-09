"""BaseTool — 工具抽象基类."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolResult(BaseModel):
    success: bool = True
    output: str = ""
    error: str = ""
    data: dict[str, Any] = {}
    citations: list[dict[str, str]] = []
    confidence: float = 0.0


class BaseTool(ABC):
    name: str = ""
    description: str = ""

    def parameters(self) -> dict[str, Any]:
        return {}

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        ...
