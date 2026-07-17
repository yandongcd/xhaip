"""共享 fixtures — fixtures + 统一 HAIP_TEST_MODE."""

import os

import pytest

from haip.llm.mock import MockProvider

os.environ.setdefault("HAIP_TEST_MODE", "true")


@pytest.fixture
def mock_llm() -> MockProvider:
    return MockProvider({
        "nutrition": {
            "content": "基于 NRS2002 评分，该患者营养风险评分为 4 分，属于高风险，建议启动肠内营养支持。",
            "input_tokens": 150,
            "output_tokens": 80,
        },
        "tpn": {
            "content": "TPN 配比计算结果: 氨基酸 85g/d, 脂肪乳 50g/d, 葡萄糖 250g/d。",
            "tool_calls": [
                {"name": "calculate_tpn", "arguments": {"patient_id": "P001", "energy_kcal": 1800}}
            ],
        },
    })


@pytest.fixture
def sample_patient() -> dict:
    return {
        "patient_id": "P001",
        "name": "张三",
        "age": 72,
        "gender": "male",
        "weight_kg": 70.0,
        "height_cm": 165.0,
        "diagnosis": "股骨转子间骨折",
        "lab_results": {
            "albumin": 32.0,
            "crp": 45.0,
            "glucose": 5.6,
            "creatinine": 88.0,
        },
    }
