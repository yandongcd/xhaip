"""iData 知识库 Mock 适配器 — 模拟院内 iData 平台知识检索.

风险缓解 (Risk #10): priority: secondary，以本地 YAML knowledge 为主源。
当 iData 返回结果与本地知识冲突时，以本地 YAML 为准。
"""

from __future__ import annotations

from typing import Any

IDATA_KNOWLEDGE = {
    "hip_fracture_classification": {
        "garden": {
            "I": "不完全骨折，外展嵌插",
            "II": "完全骨折，无移位",
            "III": "完全骨折，部分移位",
            "IV": "完全骨折，完全移位",
            "source": "Garden RS. JBJS 1961",
        },
        "evans": {
            "I": "无移位/外展嵌插",
            "ID": "不稳定 — 后内侧壁粉碎",
            "source": "Evans EM. JBJS 1949",
        },
        "ao_ota": {
            "31A": "转子间骨折",
            "31B": "股骨颈骨折",
            "31C": "股骨头骨折",
            "source": "AO/OTA Fracture Classification 2018",
        },
    },
    "surgery_guidelines": {
        "tha_indicators": ["Garden III/IV 股骨颈骨折", "年龄 >=65", "活动量大", "预期寿命 >5年"],
        "ha_indicators": ["Garden III/IV", "年龄 >=80", "活动量低", "认知障碍"],
        "pfna_indicators": ["转子间骨折 Evans ID/不稳定", "转子下骨折", "粗隆间骨折"],
    },
    "complication_rates": {
        "dvt_without_prophylaxis": "30-50%",
        "dvt_with_prophylaxis": "5-10%",
        "mortality_30day": "5-10%",
        "mortality_1year": "20-30%",
        "source": "国家卫健委 2022 / NICE NG37",
    },
}

PRIORITY_NOTE = "priority: secondary — 以本地 YAML knowledge 为主源，iData 为补充参考"


def search_knowledge(*, query: str, category: str = "", **kwargs: Any) -> dict[str, Any]:
    """Mock iData 知识库检索.

    Args:
        query: 检索关键词 (e.g. "garden", "tha", "dvt")
        category: 知识类别过滤 (可选)

    Returns:
        知识条目，标注 _mock: true 和 priority: secondary
    """
    results = {}

    for cat, items in IDATA_KNOWLEDGE.items():
        if category and cat != category:
            continue
        if isinstance(items, dict):
            for key, val in items.items():
                if query.lower() in key.lower() or (isinstance(val, dict) and
                   any(query.lower() in str(v).lower() for v in val.values())):
                    if cat not in results:
                        results[cat] = {}
                    results[cat][key] = val

    if not results:
        results["note"] = f"iData 未找到匹配 '{query}' 的内容，请参考本地 YAML knowledge"

    return {
        "query": query,
        "category": category,
        "results": results,
        "_mock": True,
        "_mock_note": "模拟 iData 知识库查询，非真实 iData API",
        "priority": "secondary",
        "priority_note": PRIORITY_NOTE,
    }


def list_categories(**kwargs: Any) -> dict[str, Any]:
    """列出 iData 知识库中所有可用类别."""
    return {
        "categories": list(IDATA_KNOWLEDGE.keys()),
        "count": len(IDATA_KNOWLEDGE),
        "_mock": True,
        "priority": "secondary",
    }
