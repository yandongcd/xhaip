"""xhaip 免安装自举：启动时注入内部包路径，无需 pip install -e。

Python 启动时若仓库根目录在 sys.path 上（从根目录运行 python -m ...），
本文件自动执行，使 packages/ 下的包无需安装即可导入。

注入顺序保证 modules 优先级最高（index 最小），并在 reload 时
强制重排, 防止其他模块的 sys.path.insert 污染顺序。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_INTERNAL_DIRS = (
    "packages/haip-core",
    "packages/haip-hospital",
    "packages/haip-hospital/modules",
)

for _rel in _INTERNAL_DIRS:
    _d = ROOT / _rel
    if _d.is_dir():
        _p = str(_d)
        if _p in sys.path:
            sys.path.remove(_p)
        sys.path.insert(0, _p)
