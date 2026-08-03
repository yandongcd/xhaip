"""HAIP Core — Hospital AI Platform 核心引擎.

启动时自举:注入仓库内部路径 (packages/haip-hospital/modules 等),
使 handler 模块 (如 bladder_cancer.*) 无需 pip install / sitecustomize 即可导入。
"""

from __future__ import annotations

import sys
from pathlib import Path

__version__ = "1.0.0"

_HAIP_CORE_DIR = Path(__file__).resolve().parent  # packages/haip-core/haip
_REPO_ROOT = _HAIP_CORE_DIR.parent.parent.parent  # 仓库根

_INTERNAL_DIRS = (
    str(_REPO_ROOT / "packages" / "haip-hospital"),
    str(_REPO_ROOT / "packages" / "haip-hospital" / "modules"),
)

for _p in _INTERNAL_DIRS:
    if Path(_p).is_dir() and _p not in sys.path:
        sys.path.insert(0, _p)
