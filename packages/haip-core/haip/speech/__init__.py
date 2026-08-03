"""STTProvider 抽象 (L8) — 语音识别统一接口.

务实路径: 先抽象后实现 (参考 speech-evaluation.md 评估报告).
MultiMed 自托管 或 商业 API (Corti) 作为 adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class STTResult:
    """语音识别结果."""
    text: str
    language: str = "zh-CN"
    confidence: float = 0.0
    segments: list[dict[str, Any]] = field(default_factory=list)  # 分段+时间戳

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "language": self.language,
                "confidence": round(self.confidence, 3)}


class STTProvider(ABC):
    """语音识别抽象 — 流式/批处理."""

    @abstractmethod
    def transcribe_file(self, audio_path: str, language: str = "zh-CN") -> STTResult:
        """批处理: 转录音频文件."""

    def transcribe_stream(self, audio_chunks: Any, language: str = "zh-CN") -> STTResult:
        """流式 (默认降级到批处理)."""
        raise NotImplementedError


class MockSTTProvider(STTProvider):
    """Mock 语音识别 — CI 用."""

    def transcribe_file(self, audio_path: str, language: str = "zh-CN") -> STTResult:
        import os
        fname = os.path.basename(audio_path)
        return STTResult(
            text=f"[mock转录 {fname}] 医生: 您哪里不舒服? 患者: 我摔了一跤, 左腿很疼",
            language=language,
            confidence=0.9,
            segments=[{"start": 0.0, "end": 2.0, "text": "您哪里不舒服?"},
                      {"start": 2.5, "end": 5.0, "text": "我摔了一跤, 左腿很疼"}],
        )


class MultiMedAdapter(STTProvider):
    """MultiMed 开源医学语音适配器 (待实现).

    参考: github.com/leduckhai/MultiMed (EMNLP 2025, 多语言医学语音).
    """

    def transcribe_file(self, audio_path: str, language: str = "zh-CN") -> STTResult:
        # TODO: 接入 MultiMed ASR 模型
        return MockSTTProvider().transcribe_file(audio_path, language)


_stt_instance: STTProvider | None = None


def get_stt_provider() -> STTProvider:
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = MockSTTProvider()
    return _stt_instance


def set_stt_provider(provider: STTProvider) -> None:
    global _stt_instance
    _stt_instance = provider
