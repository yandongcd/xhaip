"""线程安全的懒加载单例辅助函数。

统一解决模块级 `_x = None; def get_x(): if _x is None: _x = X()` 的
double-checked locking 缺失问题（多线程首调竞态）。
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

_key_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)


def locked_singleton(factory: Callable[[], T], state: dict[str, Any], key: str) -> T:
    """线程安全的懒加载单例（per-key 锁，避免不同单例互相阻塞）。

    Args:
        factory: 创建实例的函数。
        state: 存放单例的模块级字典（如 ``_singleton_state``）。
        key: 单例键名。

    Example:
        >>> _state: dict = {}
        >>> def get_engine() -> DecisionEngine:
        ...     return locked_singleton(DecisionEngine, _state, "engine")
    """
    obj = state.get(key)
    if obj is None:
        with _key_locks[key]:
            obj = state.get(key)
            if obj is None:
                obj = factory()
                state[key] = obj
    return obj
