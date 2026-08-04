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


def is_production_mode() -> bool:
    """True when HAIP_ENV=production (or HAIP_STRICT_SECURITY=true for backward compat)."""
    return (
        os.environ.get("HAIP_ENV", "development") == "production"
        or _is_true(os.environ.get("HAIP_STRICT_SECURITY", ""))
    )


def _is_default_secret(value: str, known_defaults: set[str]) -> bool:
    """True when value 为空或命中已知默认/占位符值 (仓库示例、k8s secretGenerator 占位)."""
    return value.strip() in known_defaults


def check_security_baseline(strict: bool | None = None) -> list[str]:
    """检查安全基线, 返回违规清单。

    检查项:
      1. JWT_SECRET_KEY 必须显式配置 (禁用开发默认密钥)
      2. HAIP_ADMIN_PASSWORD 必须显式配置 (禁用 Admin@123456 默认口令)
      3. HAIP_DOCTOR_PASSWORD 必须显式配置 (禁用 Doctor@123 默认口令)
      4. 上述值不得为已知默认/占位符值 (仓库示例值、k8s secretGenerator 占位)

    Args:
        strict: True 时违规抛 SecurityBaselineError。None 时:
                - HAIP_ENV=production 或 HAIP_STRICT_SECURITY=true → strict=True
                - 否则仅 warning。
    """
    if strict is None:
        strict = is_production_mode()

    known_defaults: dict[str, set[str]] = {
        "JWT_SECRET_KEY": {
            "change-this-to-a-random-string-in-production",
            "replace-with-random",
            "your-secret-key",
            "dev-secret",
        },
        "ENCRYPTION_KEY": {
            "change-this-to-a-random-string-in-production",
            "replace-with-random",
        },
        "HAIP_ADMIN_PASSWORD": {"Admin@123456", "admin123", "replace-with-random"},
        "HAIP_DOCTOR_PASSWORD": {"Doctor@123", "doctor123", "replace-with-random"},
    }

    violations: list[str] = []
    for var, defaults in known_defaults.items():
        value = os.environ.get(var, "")
        if not value:
            violations.append(f"{var} 未配置 — 正在使用开发默认值, 生产环境必须显式设置")
        elif _is_default_secret(value, defaults):
            violations.append(f"{var} 命中已知默认/占位符值, 生产环境必须替换为随机强凭据")

    if violations:
        if strict:
            raise SecurityBaselineError(
                "安全基线不达标, 拒绝启动 (production mode):\n  - "
                + "\n  - ".join(violations))
        for v in violations:
            logger.warning("[security-baseline] %s", v)
    return violations
