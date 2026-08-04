"""API Key Store — web 端配置 API key, 持久化到 data/llm_key.json.

_get 优先级: data/llm_key.json 持久值 > 环境变量 DEEPSEEK_API_KEY
(UI 配置优先于系统 env: 用户显式设置是最明确意图; env 仅作无配置时默认)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_PERSIST_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "llm_key.json"


def get_api_key() -> str:
    """获取 API key — 持久化文件优先, env 兜底.

    优先级: data/llm_key.json (UI 配置) > DEEPSEEK_API_KEY (默认值).
    原因: UI 显式配置是最明确用户意图; 系统 env 可能残留过期 key 堵住配置.
    """
    try:
        if _PERSIST_FILE.exists():
            data = json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
            key = data.get("api_key", "").strip()
            if key:
                return key
    except Exception:
        logger.debug("API key 文件读取失败", exc_info=True)
    return os.environ.get("DEEPSEEK_API_KEY", "")


def set_api_key(key: str) -> None:
    """写入持久化文件 + 同步到环境变量 (进程内立即生效)。"""
    key = key.strip()
    _PERSIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PERSIST_FILE.write_text(json.dumps({"api_key": key, "updated_at": ""}, ensure_ascii=False),
                             encoding="utf-8")
    os.environ["DEEPSEEK_API_KEY"] = key
    logger.info("API key 已配置 (持久化到 %s)", _PERSIST_FILE)


def clear_api_key() -> None:
    """清除持久化 key (仅恢复 env 原值生效)。"""
    if _PERSIST_FILE.exists():
        _PERSIST_FILE.unlink()
    if "DEEPSEEK_API_KEY" in os.environ:
        del os.environ["DEEPSEEK_API_KEY"]
    logger.info("API key 已清除")


def is_configured() -> bool:
    return bool(get_api_key())
