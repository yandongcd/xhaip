"""tests/ 统一测试环境 — env + sys.path, 消除测试文件间隐式依赖."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for p in (ROOT / "packages" / "haip-core", ROOT / "packages" / "haip-hospital",
          ROOT / "packages" / "haip-hospital" / "modules"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

os.environ.setdefault("HAIP_TEST_MODE", "true")
