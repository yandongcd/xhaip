"""HotReloadWatcher — stub re-export from haip.knowledge.runtime."""

from __future__ import annotations

import os
import threading
from pathlib import Path


class HotReloadWatcher:
    """Watches a directory for file changes and triggers reload callbacks."""

    def __init__(self, directory: str, interval: float = 1.0):
        self.directory = directory
        self.interval = interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._mtimes: dict[str, float] = {}

    def start(self) -> None:
        self._running = True
        self._stop_event.clear()
        self._mtimes = self._build_snapshot()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None

    def _scan(self) -> list[str]:
        """Scan for changes, return list of changed file paths."""
        current = self._build_snapshot()
        changed: list[str] = []
        for path_str, mtime in current.items():
            prev = self._mtimes.get(path_str)
            if prev is None or mtime > prev:
                changed.append(path_str)
        for path_str in self._mtimes:
            if path_str not in current:
                changed.append(path_str)
        self._mtimes = current
        return changed

    def _build_snapshot(self) -> dict[str, float]:
        snapshot: dict[str, float] = {}
        d = Path(self.directory)
        if d.exists():
            for path in d.rglob("*"):
                if path.is_file():
                    try:
                        snapshot[str(path)] = os.path.getmtime(path)
                    except OSError:
                        pass
        return snapshot

    def _watch_loop(self) -> None:
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.interval)
            if self._stop_event.is_set():
                break
            try:
                self._scan()
            except Exception:
                pass
