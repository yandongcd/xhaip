"""xhaip 自包含回归测试：仓库内不得引用 xhaip 文件夹之外的路径/包。"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_BACKSLASH = chr(92)
_FORBIDDEN_PATTERNS = (
    "D:" + _BACKSLASH + "FC",
    "D:" + "/" + "FC",
    "D:" + _BACKSLASH + "dst" + _BACKSLASH + "projects" + _BACKSLASH + "haip",
    "D:" + "/" + "dst" + "/" + "projects" + "/" + "haip",
    "C:" + _BACKSLASH + "Users",
    "C:" + "/" + "Users",
)

_SKIP_DIRS = {
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "htmlcov", ".audit", ".code-review-graph", "releases", "node_modules",
    ".superpowers",
}
_SKIP_PREFIXES = (
    os.path.join("docs", "superpowers", ""),
)
_TEXT_SUFFIXES = {
    ".py", ".md", ".yaml", ".yml", ".bat", ".ps1", ".toml", ".json",
    ".txt", ".cfg", ".ini", ".sh", ".example",
}


def _iter_text_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir != ".":
            rel = rel_dir + os.sep
            if any(rel.startswith(p) for p in _SKIP_PREFIXES):
                dirnames[:] = []
                continue
        for name in filenames:
            if Path(name).suffix.lower() in _TEXT_SUFFIXES:
                yield Path(dirpath) / name


def test_sitecustomize_injects_internal_paths():
    importlib.import_module("sitecustomize")
    importlib.reload(sys.modules["sitecustomize"])
    for rel in ("packages/haip-core", "packages/haip-hospital",
                "packages/haip-hospital/modules"):
        assert str(ROOT / rel) in sys.path, f"{rel} 未注入 sys.path"
