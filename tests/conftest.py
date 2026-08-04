"""tests/ 统一测试环境 — env + sys.path, 消除测试文件间隐式依赖."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

for p in (ROOT / "packages" / "haip-core", ROOT / "packages" / "haip-hospital",
          ROOT / "packages" / "haip-hospital" / "modules"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

os.environ.setdefault("HAIP_TEST_MODE", "true")


@pytest.fixture(scope="session", autouse=True)
def _ensure_full_registry():
    """Session 开始时确保 agent 注册表为完整生产集 (83 个 YAML).

    web_server 在模块级 load_from_dir 仅执行一次, 测试清空 registry 后
    不会自动重载; 此 fixture 幂等预加载, 防止清空型测试出现在最前面时
    后续 UI/页面测试拿到空注册表.
    """
    from haip.agent import _registry, list_all, load_from_dir
    if len(list_all()) < 50:
        yaml_dir = ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
        _registry.clear()
        load_from_dir(str(yaml_dir))


@pytest.fixture(autouse=True)
def _restore_agent_registry():
    """每个测试后恢复 agent 注册表快照.

    兜底 tests/ 下 19 处 `_registry.clear()` 清空后不恢复导致的跨测试污染
    (UI 契约/页面测试遍历空注册表 → 404 / 断言失败).
    """
    from haip.agent import _registry
    snapshot = dict(_registry)
    yield
    _registry.clear()
    _registry.update(snapshot)
