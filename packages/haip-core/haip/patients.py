"""数字病人统一加载 — 全部 UI 渲染器共用的唯一入口.

patients.json 支持两种顶层格式:
  - dict: {"total": N, "patients": [...]}
  - list: [...]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PATIENTS_FILE = PROJECT_ROOT / "packages" / "haip-hospital" / "data" / "patients.json"


def load_patients(agent_name: str, limit: int = 8, only_compatible: bool = False) -> list[dict]:
    """加载与 agent 兼容的数字病人.

    Args:
        agent_name: Agent 技术名, 匹配 patient["compatible_agents"].
        limit: 返回条数上限.
        only_compatible: True 时无兼容患者返回 [] (不回退全量).
    """
    if not PATIENTS_FILE.exists():
        logger.warning("patients.json 不存在: %s", PATIENTS_FILE)
        return []
    try:
        data = json.loads(PATIENTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("patients.json 加载失败: %s", e)
        return []
    all_pts = data.get("patients", []) if isinstance(data, dict) else data
    if not isinstance(all_pts, list):
        logger.warning("patients.json 顶层结构异常: %s", type(all_pts).__name__)
        return []
    matched = [p for p in all_pts if agent_name in p.get("compatible_agents", [])]
    if matched:
        return matched[:limit]
    if only_compatible:
        return []
    return all_pts[:limit]
