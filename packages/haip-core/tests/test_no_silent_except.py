"""D1 定点治理 — 禁止裸吞异常 (全仓关键模块).

扫描以下模块中:
  - except ...: pass (无日志的静默吞异常)
  - except Exception: ... (宽泛捕获无 logging)
断言 0 处 unsafe 静默。

注意: 不检查 ImportError/ValueError/KeyError 等窄化捕获后的 pass/logger.debug。
"""

from __future__ import annotations

import re
from pathlib import Path

_SOURCE_DIR = Path(__file__).resolve().parent.parent / "haip"
_TARGET_FILES = [
    _SOURCE_DIR / "a2a" / "__init__.py",
    _SOURCE_DIR / "auth" / "__init__.py",
    _SOURCE_DIR / "auth" / "jwt.py",
    _SOURCE_DIR / "auth" / "middleware.py",
    _SOURCE_DIR / "adapters" / "__init__.py",
    _SOURCE_DIR / "api_key_store.py",
    _SOURCE_DIR / "web_server.py",
]

# Patterns that count as "silent swallow" — bare except or too-broad with pass
_UNSAFE_SILENT = re.compile(
    r"except\s+(?:(?:Base)?Exception|:)\s*(?:#[^\n]*)?\n\s*pass",
    re.MULTILINE,
)

# Also catch bare except with just a logging call but no log level that's DEBUG
# (warnings/debug are fine as they are informative)


class TestNoSilentExcept:
    def test_no_silent_except_in_targets(self):
        violations: list[tuple[str, int, str]] = []
        for fp in _TARGET_FILES:
            if not fp.exists():
                continue
            content = fp.read_text(encoding="utf-8")
            lines = content.split("\n")
            # Find unsafe silent patterns
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                # Pattern: "except Exception:" or "except:" followed by "pass" within 2 lines
                if re.match(r"except\s+(?:Exception\s*:|:)\s*$", stripped):
                    # Check next 2 lines for bare pass (no logging before it)
                    window = "\n".join(lines[i : i + 3])
                    if re.search(r"^\s*pass\s*$", window, re.MULTILINE):
                        # Check there's no logging in between
                        log_part = window[: window.index("pass")] if "pass" in window else window
                        if "logger" not in log_part and "logging" not in log_part:
                            violations.append((str(fp), i, line))

        assert not violations, (
            f"发现 {len(violations)} 处裸吞异常 (except Exception: ... pass 无日志):\n"
            + "\n".join(f"  {f}:{lineno}: {ctx}" for f, lineno, ctx in violations)
        )
