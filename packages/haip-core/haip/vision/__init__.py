"""VisionProvider 抽象 (L7/G11) — 多模态影像理解统一接口.

务实路径: 不自研模型, 适配开源 VLM (Qwen2.5-VL / LLaVA-Med 等).
MockVision 用于 CI; 真实 adapter 由配置切换.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VisionResult:
    """影像理解结果."""
    modality: str                  # xray / ct / mri / ecg / ultrasound
    findings: list[str] = field(default_factory=list)
    classification: str = ""
    confidence: float = 0.0
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "modality": self.modality,
            "findings": self.findings,
            "classification": self.classification,
            "confidence": round(self.confidence, 3),
        }


class VisionProvider(ABC):
    """影像理解抽象 — 类似 LLMProvider 的模式."""

    @abstractmethod
    def analyze(self, image_path: str, modality: str = "xray") -> VisionResult:
        """分析医学影像, 返回结构化发现."""


class MockVisionProvider(VisionProvider):
    """Mock 影像理解 — CI 用 (无外部模型依赖)."""

    def analyze(self, image_path: str, modality: str = "xray") -> VisionResult:
        import os
        fname = os.path.basename(image_path).lower()
        if "ecg" in fname or modality == "ecg":
            return VisionResult(
                modality="ecg",
                findings=["窦性心律", "ST-T 无明显异常"],
                classification="正常心电图",
                confidence=0.9,
                raw_text="mock ecg analysis",
            )
        return VisionResult(
            modality=modality,
            findings=["未见明确骨折线", "骨皮质连续"],
            classification="未见异常" if "normal" in fname else "疑似骨折",
            confidence=0.7,
            raw_text="mock vision analysis",
        )


class OpenVLAdapter(VisionProvider):
    """开源 VLM 适配器 (Qwen2.5-VL / LLaVA-Med).

    通过 config 配置 base_url + model; 未配置时降级 Mock.
    """

    def __init__(self, base_url: str = "", model: str = "qwen2.5-vl-7b",
                 api_key: str = "", provider: Any = None):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self._provider = provider  # 可选: 复用 LLMProvider 做多模态 chat

    def analyze(self, image_path: str, modality: str = "xray") -> VisionResult:
        if not self.base_url and self._provider is None:
            return MockVisionProvider().analyze(image_path, modality)
        # TODO: 实现 OpenAI-compatible 多模态 chat (image_url + prompt)
        return MockVisionProvider().analyze(image_path, modality)


_vision_instance: VisionProvider | None = None


def get_vision_provider() -> VisionProvider:
    global _vision_instance
    if _vision_instance is None:
        _vision_instance = MockVisionProvider()
    return _vision_instance


def set_vision_provider(provider: VisionProvider) -> None:
    global _vision_instance
    _vision_instance = provider
