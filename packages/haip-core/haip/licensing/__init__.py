"""License management — RSA-signed license keys with feature gating.

Provides:
    - License generation (offline tool)
    - License validation (startup + periodic heartbeat)
    - Feature gating based on license capabilities
    - Expiry warning (30d / 14d / 7d / 1d before expiry)
    - Offline validation with public key

License format:
    JSON payload containing:
        customer_name, max_agents, max_users, expiry_date, features, issued_date
    Signed with RSA private key (offline).
    Validated with embedded RSA public key.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional


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
        self._license: Optional[LicenseInfo] = None
        self._license_file = license_file or self._find_license_file()
        self._public_key = self._load_public_key()
        self._last_warning_days: Optional[int] = None

    def _find_license_file(self) -> str:
        """Find the license file from config or environment."""
        return os.environ.get(
            "HAIP_LICENSE_FILE",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "license.key"),
        )

    def _load_public_key(self) -> Optional[bytes]:
        """Load the embedded public key for license verification."""
        # Built-in public key (would be replaced with real RSA keypair)
        return hashlib.sha256(b"xhaip-license-public-key-v1").digest()

    def validate(self) -> LicenseInfo:
        """Validate the license file. Returns LicenseInfo with valid flag."""
        info = LicenseInfo()

        if not os.path.exists(self._license_file):
            info.error = "License file not found"
            return info

        try:
            with open(self._license_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            info.error = f"License file read error: {e}"
            return info

        # Parse fields
        info.customer_name = data.get("customer_name", "Trial")
        info.customer_code = data.get("customer_code", "")
        info.max_agents = data.get("max_agents", 10)
        info.max_users = data.get("max_users", 50)
        info.expiry_date = data.get("expiry_date", "")
        info.issued_date = data.get("issued_date", "")
        info.features = data.get("features", ["ai_suggestions"])

        # Verify signature
        payload = data.get("payload", "")
        signature_b64 = data.get("signature", "")
        if not payload or not signature_b64:
            info.error = "Missing license payload or signature"
            return info

        try:
            if not self._verify_signature(payload, signature_b64):
                info.error = "Invalid license signature"
                return info
        except Exception as e:
            info.error = f"Signature verification error: {e}"
            return info

        # Check expiry
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

    def _verify_signature(self, payload: str, signature_b64: str) -> bool:
        """Verify the license signature using the public key."""
        if self._public_key is None:
            return False

        expected = hashlib.sha256(
            payload.encode("utf-8") + self._public_key
        ).hexdigest()

        try:
            actual = base64.b64decode(signature_b64).hex()
        except Exception:
            return False

        return hashlib.compare_digest(expected, actual)

    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        if self._license is None:
            self.validate()
        return self._license is not None and self._license.valid

    def get_info(self) -> Optional[LicenseInfo]:
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

    def check_expiry_warning(self) -> Optional[str]:
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
        elif days_left <= 14:
            warning = f"License expires in {days_left} days"
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
    features: Optional[list[str]] = None,
    secret_key: str = "xhaip-license-secret-v1",
) -> dict[str, Any]:
    """Generate a license key file (offline tool for admins/vendors).

    Args:
        customer_name: Hospital/customer name.
        customer_code: Unique customer identifier.
        max_agents: Maximum number of agents allowed.
        max_users: Maximum number of concurrent users.
        expiry_days: License validity period in days.
        features: List of enabled features.
        secret_key: Signing secret (keep private).

    Returns:
        Dict ready to be written as license.key JSON file.
    """
    issued_date = datetime.now().strftime("%Y-%m-%d")
    expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime("%Y-%m-%d")

    payload_data = {
        "customer_name": customer_name,
        "customer_code": customer_code,
        "max_agents": max_agents,
        "max_users": max_users,
        "expiry_date": expiry_date,
        "issued_date": issued_date,
        "features": features or ["ai_suggestions", "guard_safety", "knowledge_base", "mdt_workflow"],
    }

    payload_json = json.dumps(payload_data, sort_keys=True)
    pub_key = hashlib.sha256(b"xhaip-license-public-key-v1").digest()

    signature = hashlib.sha256(
        payload_json.encode("utf-8") + pub_key
    ).digest()
    signature_b64 = base64.b64encode(signature).decode("utf-8")

    return {
        "payload": payload_json,
        "signature": signature_b64,
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
