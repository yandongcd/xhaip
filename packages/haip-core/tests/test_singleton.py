"""测试 locked_singleton — 线程安全懒加载单例 (per-key 锁)."""

from __future__ import annotations

import threading
import time

from haip._singleton import locked_singleton


def test_returns_same_object():
    state: dict = {}
    assert locked_singleton(list, state, "k") is locked_singleton(list, state, "k")


def test_factory_called_once():
    state: dict = {}
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return object()

    a = locked_singleton(factory, state, "k")
    b = locked_singleton(factory, state, "k")
    assert a is b
    assert calls["n"] == 1


def test_different_keys_different_instances():
    state: dict = {}
    calls = {"a": 0, "b": 0}

    def factory_a():
        calls["a"] += 1
        return "A"

    def factory_b():
        calls["b"] += 1
        return "B"

    assert locked_singleton(factory_a, state, "a") == "A"
    assert locked_singleton(factory_b, state, "b") == "B"
    assert calls == {"a": 1, "b": 1}


def test_thread_safety_50_threads_single_instance():
    state: dict = {}
    calls = {"n": 0}
    results: list[object] = []

    def slow_factory():
        time.sleep(0.01)
        calls["n"] += 1
        return object()

    threads = [
        threading.Thread(
            target=lambda: results.append(locked_singleton(slow_factory, state, "k"))
        )
        for _ in range(50)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert calls["n"] == 1
    assert len(results) == 50
    assert all(r is results[0] for r in results)


def test_reset_state_yields_new_instance():
    state: dict = {}
    first = locked_singleton(list, state, "k")
    state.clear()
    second = locked_singleton(list, state, "k")
    assert second is not first


def test_per_key_isolation():
    state: dict = {}
    entered = threading.Event()
    release = threading.Event()
    results: dict[str, str] = {}

    def slow_factory():
        entered.set()
        release.wait(10)
        return "slow"

    def call_b():
        results["b"] = locked_singleton(lambda: "fast", state, "B")

    t = threading.Thread(target=lambda: locked_singleton(slow_factory, state, "A"))
    t.start()
    assert entered.wait(10)

    b_thread = threading.Thread(target=call_b)
    b_thread.start()
    b_thread.join(timeout=2)
    assert not b_thread.is_alive()

    release.set()
    t.join(timeout=10)
    assert results["b"] == "fast"
    assert state["A"] == "slow"
    assert state["B"] == "fast"
