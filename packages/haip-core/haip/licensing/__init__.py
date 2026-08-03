"""License management — RSA-signed (RS256 JWT) license keys with feature gating.

Provides:
    - License generation (offline tool, requires LICENSE_SIGNING_KEY)
    - License validation (startup + periodic heartbeat) via RS256 JWT
    - Feature gating based on license capabilities
    - Expiry warning (30d / 14d / 7d / 1d before expiry)
    - Production enforcement: startup gate + max_agents + max_users

License format (license.key JSON):
    payload:   JSON string of claims (for readability / API display)
    signature: RS256 JWT signing the claims
    Signed with LICENSE_SIGNING_KEY (RSA PEM, offline).
    Verified with LICENSE_PUBLIC_KEY (RSA PEM, runtime).

Security notes:
    - LICENSE_PUBLIC_KEY 未配置 → 验证 fail-closed (永不放行)
    - 所有受信任字段取自 JWT claims — license 文件顶层字段仅作展示, 不受信任
    - 生产模式 (HAIP_ENV=production / HAIP_STRICT_SECURITY=true):
        启动时 License 无效/过期 → LicenseError 阻断启动;
        agent 注册数 >= max_agents → 拒绝注册;
        活跃用户数 > max_users → 拒绝登录
    - 开发模式: 仅 logger.warning, 不阻断
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import jwt

logger = logging.getLogger(__name__)

_DEFAULT_LICENSE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "license.key"
)


class LicenseError(RuntimeError):
    """License 违规 — 生产模式下阻断启动或拒绝操作。"""


def _is_production() -> bool:
    """HAIP_ENV=production 或 HAIP_STRICT_SECURITY=true → 强制模式。"""
    from haip.security_baseline import is_production_mode

    return is_production_mode()


@dataclass
class LicenseInfo:
    """Decoded license information."""

    customer_name: str = ""
    customer_code: str = ""
    max_agents: int = 10
    max_users: int = 50
    expiry_date: str = ""  # YYYY-MM-DD
    issued_date: str = ""
    features: list[str] = field(default_factory=lambda: [
        "ai_suggestions",
        "guard_safety",
        "knowledge_base",
    ])
    signature: str = ""
    valid: bool = False
    error: str = ""


class LicenseManager:
    """Validates and enforces license constraints."""

    def __init__(self, license_file: str = ""):
        self._license: LicenseInfo | None = None
        self._license_file = license_file or self._find_license_file()
        self._public_key = self._load_public_key()
        self._last_warning_days: int | None = None

    def _find_license_file(self) -> str:
        """Find the license file from config or environment."""
        return os.environ.get("HAIP_LICENSE_FILE", _DEFAULT_LICENSE_FILE)

    def _load_public_key(self) -> str | None:
        """Load the RSA public key (PEM) for license verification.

        LICENSE_PUBLIC_KEY 未配置 → None → 所有验证 fail-closed。
        """
        pem = os.environ.get("LICENSE_PUBLIC_KEY", "").strip()
        return pem or None

    def validate(self) -> LicenseInfo:
        """Validate the license file. Returns LicenseInfo with valid flag."""
        info = LicenseInfo()

        if self._public_key is None:
            info.error = "LICENSE_PUBLIC_KEY 未配置 — License 验证失败 (fail-closed)"
            return info

        if not os.path.exists(self._license_file):
            info.error = "License file not found"
            return info

        try:
            with open(self._license_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            info.error = f"License file read error: {e}"
            return info

        if not isinstance(data, dict):
            info.error = "License file must be a JSON object"
            return info

        payload = data.get("payload", "")
        signature = data.get("signature", "")
        if not payload or not signature:
            info.error = "Missing license payload or signature"
            return info

        if not isinstance(payload, str):
            info.error = "License payload must be a JSON string"
            return info

        try:
            expected = json.loads(payload)
        except json.JSONDecodeError as e:
            info.error = f"Invalid license payload JSON: {e}"
            return info

        try:
            claims = jwt.decode(
                signature,
                self._public_key,
                algorithms=["RS256"],
                options={"verify_exp": False},
            )
        except jwt.InvalidSignatureError:
            info.error = "Invalid license signature"
            return info
        except jwt.InvalidTokenError as e:
            info.error = f"Invalid license token: {e}"
            return info

        # 防篡改: payload 必须与签名 claims 完全一致 (顶层文件字段不受信任)
        if claims != expected:
            info.error = "Invalid license signature"
            return info

        info.customer_name = claims.get("customer_name", "Trial")
        info.customer_code = claims.get("customer_code", "")
        try:
            info.max_agents = int(claims.get("max_agents", 10))
            info.max_users = int(claims.get("max_users", 50))
        except (TypeError, ValueError):
            info.error = "License claims max_agents/max_users must be numeric"
            return info
        info.expiry_date = claims.get("expiry_date", "")
        info.issued_date = claims.get("issued_date", "")
        features = claims.get("features", [])
        info.features = list(features) if isinstance(features, list) else []
        info.signature = signature

        # 过期检查: exp claim (签名内) 优先, expiry_date 字符串兜底
        exp = claims.get("exp")
        if isinstance(exp, (int, float)):
            exp_dt = datetime.fromtimestamp(exp)  # noqa: DTZ006 — 本地时区, 与 datetime.now() 一致
            if datetime.now() > exp_dt:
                info.error = f"License expired on {exp_dt.strftime('%Y-%m-%d')}"
                return info
        if info.expiry_date:
            try:
                expiry = datetime.strptime(info.expiry_date, "%Y-%m-%d")
                if datetime.now() > expiry:
                    info.error = f"License expired on {info.expiry_date}"
                    return info
            except ValueError:
                info.error = f"Invalid expiry date format: {info.expiry_date}"
                return info

        info.valid = True
        self._license = info
        return info

    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        if self._license is None:
            self.validate()
        return self._license is not None and self._license.valid

    def get_info(self) -> LicenseInfo | None:
        """Get current license info."""
        if self._license is None:
            self.validate()
        return self._license

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a specific feature is enabled by the license."""
        info = self.get_info()
        if not info or not info.valid:
            return False
        return feature in info.features

    def check_expiry_warning(self) -> str | None:
        """Check if license is approaching expiry and return warning message.

        Returns warning message if within 30 days of expiry, None otherwise.
        """
        info = self.get_info()
        if not info or not info.valid or not info.expiry_date:
            return None

        try:
            expiry = datetime.strptime(info.expiry_date, "%Y-%m-%d")
            days_left = (expiry - datetime.now()).days
        except ValueError:
            return None

        warning = None
        if days_left <= 1:
            warning = f"License expires TODAY ({info.expiry_date})"
        elif days_left <= 7:
            warning = f"License expires in {days_left} days ({info.expiry_date})"
        elif days_left <= 30:
            warning = f"License expires in {days_left} days"

        # Avoid spamming the same warning
        if warning and self._last_warning_days != days_left:
            self._last_warning_days = days_left
            return warning
        return None

    def get_limits(self) -> dict[str, int]:
        """Get the license limits for rate limiting."""
        info = self.get_info()
        if not info or not info.valid:
            return {"max_agents": 0, "max_users": 0}
        return {"max_agents": info.max_agents, "max_users": info.max_users}


# ── License generator (offline tool) ──


def generate_license(
    customer_name: str,
    customer_code: str,
    max_agents: int = 48,
    max_users: int = 100,
    expiry_days: int = 365,
    features: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a license key file (offline tool for admins/vendors).

    Requires LICENSE_SIGNING_KEY (RSA PEM) — raises ValueError if not configured.
    No dev backdoor: 未配置签名密钥时拒绝生成。

    Args:
        customer_name: Hospital/customer name.
        customer_code: Unique customer identifier.
        max_agents: Maximum number of agents allowed.
        max_users: Maximum number of users allowed.
        expiry_days: License validity period in days.
        features: List of enabled features.

    Returns:
        Dict ready to be written as license.key JSON file.
    """
    signing_key = os.environ.get("LICENSE_SIGNING_KEY", "").strip()
    if not signing_key:
        raise ValueError(
            "LICENSE_SIGNING_KEY 未配置 — 无法生成 License (仅离线签发工具需要)")

    issued_date = datetime.now().strftime("%Y-%m-%d")
    expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime("%Y-%m-%d")
    exp = int(datetime.strptime(expiry_date, "%Y-%m-%d").timestamp())

    payload_data = {
        "customer_name": customer_name,
        "customer_code": customer_code,
        "max_agents": max_agents,
        "max_users": max_users,
        "expiry_date": expiry_date,
        "issued_date": issued_date,
        "features": features or ["ai_suggestions", "guard_safety", "knowledge_base", "mdt_workflow"],
        "exp": exp,
    }

    payload_json = json.dumps(payload_data, sort_keys=True)
    token = jwt.encode(payload_data, signing_key, algorithm="RS256")

    return {
        "payload": payload_json,
        "signature": token,
        "customer_name": customer_name,
        "customer_code": customer_code,
        "max_agents": max_agents,
        "max_users": max_users,
        "expiry_date": expiry_date,
        "issued_date": issued_date,
        "features": payload_data["features"],
    }


def write_license_file(license_data: dict[str, Any], filepath: str = "license.key"):
    """Write a license key to a file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(license_data, f, indent=2, ensure_ascii=False)


# ── Module-level accessor + enforcement helpers ──

_limits_cache: dict[tuple[str, str], dict[str, int]] = {}
_limits_lock = threading.Lock()


def license_limits() -> dict[str, int]:
    """Get current license limits (max_agents/max_users).

    读 env (HAIP_LICENSE_FILE + LICENSE_PUBLIC_KEY) 并缓存 License 上限,
    每次调用廉价 (无单例框架)。无效 License → {"max_agents": 0, "max_users": 0}。
    """
    path = os.environ.get("HAIP_LICENSE_FILE", _DEFAULT_LICENSE_FILE)
    pub = os.environ.get("LICENSE_PUBLIC_KEY", "")
    cache_key = (path, pub)
    with _limits_lock:
        cached = _limits_cache.get(cache_key)
    if cached is not None:
        return cached
    mgr = LicenseManager(path)
    limits = mgr.get_limits()
    with _limits_lock:
        _limits_cache[cache_key] = limits
    return limits


def check_agent_capacity(current_count: int) -> tuple[bool, str]:
    """生产模式: 已注册 Agent 数 >= max_agents → 拒绝新注册. 开发模式恒放行."""
    if not _is_production():
        return True, ""
    limits = license_limits()
    max_agents = limits.get("max_agents", 0)
    if max_agents <= 0:
        # 无有效 License 上限 → 放行 (启动校验已由 enforce_startup 把关)
        return True, ""
    if current_count >= max_agents:
        return False, (
            f"License 限制: 已注册 Agent 数 ({current_count}) 已达上限 "
            f"({max_agents}), 请联系管理员扩容"
        )
    return True, ""


def check_user_capacity(active_count: int) -> tuple[bool, str]:
    """生产模式: 活跃用户数超过 max_users → 拒绝登录. 开发模式恒放行."""
    if not _is_production():
        return True, ""
    limits = license_limits()
    max_users = limits.get("max_users", 0)
    if max_users <= 0:
        # 无有效 License 上限 → 放行 (启动校验已由 enforce_startup 把关)
        return True, ""
    if active_count > max_users:
        return False, (
            f"活跃用户数 ({active_count}) 已超过 License 上限 ({max_users}), "
            "请联系管理员扩容"
        )
    return True, ""


def enforce_startup() -> None:
    """启动 License 校验: 生产模式无效/过期 → 抛 LicenseError 阻断启动; 开发模式仅告警."""
    mgr = LicenseManager()
    info = mgr.get_info()
    if info is not None and info.valid:
        return
    reason = info.error if info is not None else "License 未加载"
    msg = f"License 无效: {reason}"
    if _is_production():
        raise LicenseError(msg)
    logger.warning("[license] %s (开发模式放行; 生产模式将阻断启动)", msg)
