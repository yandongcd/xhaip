"""YAML 热重载 — 文件变更监听 + 自动重新加载 Agent 定义."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Callable


class HotReloadWatcher:
    """监听 YAML 定义目录的文件变更, 自动触发 reload。

    用法:
        watcher = HotReloadWatcher(definitions_dir, callback=on_reload)
        watcher.start()
        # ... Agent 运行中 ...
        watcher.stop()
    """

    def __init__(self, watch_dir: str | Path, callback: Callable | None = None,
                 interval: float = 2.0):
        self.watch_dir = Path(watch_dir)
        self.callback = callback or self._default_callback
        self.interval = interval
        self._thread: threading.Thread | None = None
        self._running = False
        self._mtime_map: dict[str, float] = {}
        self.stats = {"reloads": 0, "last_reload": "", "files_changed": []}

    def start(self):
        if self._running:
            return
        self._running = True
        self._scan()  # 初始扫描
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _scan(self) -> list[str]:
        """扫描目录, 返回变更文件列表。"""
        changed: list[str] = []
        if not self.watch_dir.exists():
            return changed

        for yaml_file in self.watch_dir.glob("*.yaml"):
            if yaml_file.name.startswith("_"):
                continue
            mtime = os.path.getmtime(yaml_file)
            key = str(yaml_file)
            if key not in self._mtime_map or mtime > self._mtime_map[key]:
                changed.append(yaml_file.name)
                self._mtime_map[key] = mtime
        return changed

    def _watch_loop(self):
        while self._running:
            time.sleep(self.interval)
            changed = self._scan()
            if changed:
                self.stats["reloads"] += 1
                self.stats["last_reload"] = time.strftime("%H:%M:%S")
                self.stats["files_changed"] = changed
                try:
                    self.callback(changed)
                except Exception as e:
                    self.stats["last_error"] = str(e)

    @staticmethod
    def _default_callback(changed: list[str]):
        """默认回调: 重新加载所有 YAML 定义到 Registry。"""
        from haip.agent import _registry, load_from_dir
        # 尝试从 project_root 推断 YAML 目录
        candidates = [
            Path.cwd() / "agents" / "definitions",
            Path.cwd() / "packages" / "haip-hospital" / "agents" / "definitions",
        ]
        for d in candidates:
            if d.exists():
                _registry.clear()
                load_from_dir(str(d))
                break


def enable_hotreload(definitions_dir: str | Path,
                    interval: float = 2.0) -> HotReloadWatcher:
    """便捷函数: 启动热重载监听。"""
    watcher = HotReloadWatcher(definitions_dir, interval=interval)
    watcher.start()
    return watcher
