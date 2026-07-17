"""安全基线检查 — 商用 M1: 生产环境强制安全配置.

用法:
    dev 模式 (默认): 违规项仅 logger.warning
    strict 模式 (HAIP_STRICT_SECURITY=true 或 strict=True): 违规即抛 SecurityBaselineError
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class SecurityBaselineError(RuntimeError):
    """安全基线违规 (strict 模式下阻断启动)。"""


def _is_true(v: str) -> bool:
    return v.strip().lower() in ("1", "true", "yes", "on")


def check_security_baseline(strict: bool | None = None) -> list[str]:
    """检查安全基线, 返回违规清单。

    检查项:
      1. JWT_SECRET_KEY 必须显式配置 (禁用开发默认密钥)
      2. HAIP_ADMIN_PASSWORD 必须显式配置 (禁用 Admin@123456 默认口令)
      3. HAIP_DOCTOR_PASSWORD 必须显式配置 (禁用 Doctor@123 默认口令)

    Args:
        strict: True 时违规抛 SecurityBaselineError; None 时读 HAIP_STRICT_SECURITY。
    """
    if strict is None:
        strict = _is_true(os.environ.get("HAIP_STRICT_SECURITY", ""))

    violations: list[str] = []
    if not os.environ.get("JWT_SECRET_KEY"):
        violations.append("JWT_SECRET_KEY 未配置 — 正在使用开发默认密钥, 生产环境必须显式设置")
    if not os.environ.get("HAIP_ADMIN_PASSWORD"):
        violations.append("HAIP_ADMIN_PASSWORD 未配置 — admin 账号将使用默认口令")
    if not os.environ.get("HAIP_DOCTOR_PASSWORD"):
        violations.append("HAIP_DOCTOR_PASSWORD 未配置 — doctor 演示账号将使用默认口令")

    if violations:
        if strict:
            raise SecurityBaselineError(
                "安全基线不达标, 拒绝启动 (HAIP_STRICT_SECURITY=true):\n  - "
                + "\n  - ".join(violations))
        for v in violations:
            logger.warning("[security-baseline] %s", v)
    return violations
