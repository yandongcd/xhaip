"""数字病人统一加载 — 全部 UI 渲染器共用的唯一入口.

patients.json 支持两种顶层格式:
  - dict: {"total": N, "patients": [...]}
  - list: [...]
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PATIENTS_FILE = PROJECT_ROOT / "packages" / "haip-hospital" / "data" / "patients.json"

_cache_lock = threading.Lock()
_cache_key: tuple[str, int, int] | None = None
_cache_patients: list[dict] | None = None


def clear_cache() -> None:
    """清空患者缓存, 下次 load_patients 强制重读文件."""
    global _cache_key, _cache_patients
    with _cache_lock:
        _cache_key = None
        _cache_patients = None


def _read_all_patients() -> list[dict] | None:
    """读文件并返回患者列表; 失败返回 None (不污染缓存)."""
    try:
        data = json.loads(PATIENTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("patients.json 加载失败: %s", e)
        return None
    all_pts = data.get("patients", []) if isinstance(data, dict) else data
    if not isinstance(all_pts, list):
        logger.warning("patients.json 顶层结构异常: %s", type(all_pts).__name__)
        return None
    return all_pts


def load_patients(agent_name: str, limit: int = 8, only_compatible: bool = False) -> list[dict]:
    """加载与 agent 兼容的数字病人 (mtime+size 失效缓存, 线程安全).

    Args:
        agent_name: Agent 技术名, 匹配 patient["compatible_agents"].
        limit: 返回条数上限.
        only_compatible: True 时无兼容患者返回 [] (不回退全量).
    """
    if not PATIENTS_FILE.exists():
        logger.warning("patients.json 不存在: %s", PATIENTS_FILE)
        return []
    try:
        stat = PATIENTS_FILE.stat()
        key = (str(PATIENTS_FILE), stat.st_mtime_ns, stat.st_size)
    except OSError as e:
        logger.warning("patients.json stat 失败: %s", e)
        return []

    global _cache_key, _cache_patients
    with _cache_lock:
        all_pts: list[dict] | None
        if _cache_key == key and _cache_patients is not None:
            all_pts = _cache_patients
        else:
            all_pts = _read_all_patients()
            if all_pts is None:
                return []
            _cache_key = key
            _cache_patients = all_pts

    matched = [p for p in all_pts if agent_name in p.get("compatible_agents", [])]
    if matched:
        return matched[:limit]
    if only_compatible:
        return []
    return all_pts[:limit]
