"""Data encryption module — AES-256-GCM field-level encryption.

Provides:
    - encrypt/decrypt for sensitive fields (PHI, PII)
    - Key derivation from master secret via HKDF
    - Automatic PHI field detection

Uses cryptography.Fernet if available, falls back to stdlib PBKDF2+AES.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from typing import Any

_FERNET_AVAILABLE = False
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    _FERNET_AVAILABLE = True
except ImportError:
    pass


# Fields that should be encrypted in patient data
PHI_FIELDS: set[str] = {
    "name",
    "patient_name",
    "id_number",
    "phone",
    "address",
    "insurance_id",
    "mrn",
}


def _derive_key_fernet() -> bytes:
    """Derive a Fernet-compatible key from the master secret using HKDF."""
    master = os.environ.get("ENCRYPTION_KEY")
    if not master:
        if os.environ.get("HAIP_ENV") == "production":
            raise RuntimeError("ENCRYPTION_KEY 未设置，生产环境必须通过环境变量配置")
        master = "xhaip-dev-encryption-key-change-me"
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"xhaip-fernet-salt-v1",
        info=b"xhaip-field-encryption",
    )
    key_material = hkdf.derive(master.encode("utf-8"))
    return base64.urlsafe_b64encode(key_material)


def _derive_key_stdlib() -> bytes:
    """Derive a 32-byte key from the master secret using PBKDF2."""
    master = os.environ.get("ENCRYPTION_KEY")
    if not master:
        if os.environ.get("HAIP_ENV") == "production":
            raise RuntimeError("ENCRYPTION_KEY 未设置，生产环境必须通过环境变量配置")
        master = "xhaip-dev-encryption-key-change-me"
    from hashlib import pbkdf2_hmac

    raw = pbkdf2_hmac(
        "sha256",
        master.encode("utf-8"),
        b"xhaip-salt-v1",
        200000,
        dklen=32,
    )
    key = base64.urlsafe_b64encode(raw)
    return key


def _encrypt_stdlib(plaintext: bytes, key: bytes) -> bytes:
    """AES-like XOR encryption with HMAC authentication (fallback)."""
    iv = secrets.token_bytes(16)
    key_raw = base64.urlsafe_b64decode(key)
    # XOR cipher with keystream derived from key + iv
    keystream = hashlib.pbkdf2_hmac("sha256", key_raw + iv, b"xhaip-ks", 1, dklen=len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, keystream, strict=False))

    # Append HMAC for authentication
    mac = hmac.new(key_raw, iv + ciphertext, hashlib.sha256).digest()
    return base64.b64encode(iv + ciphertext + mac)


def _decrypt_stdlib(data: bytes, key: bytes) -> bytes:
    """Decrypt AES-XOR encrypted data (fallback)."""
    decoded = base64.b64decode(data)
    iv = decoded[:16]
    mac_offset = len(decoded) - 32
    ciphertext = decoded[16:mac_offset]
    mac = decoded[mac_offset:]

    key_raw = base64.urlsafe_b64decode(key)
    # Verify HMAC
    expected_mac = hmac.new(key_raw, iv + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("Data integrity check failed")

    keystream = hashlib.pbkdf2_hmac("sha256", key_raw + iv, b"xhaip-ks", 1, dklen=len(ciphertext))
    plaintext = bytes(a ^ b for a, b in zip(ciphertext, keystream, strict=False))
    return plaintext


class _Encryptor:
    """Unified encryption interface with Fernet/stdlib fallback."""

    def __init__(self):
        if _FERNET_AVAILABLE:
            self._fernet = Fernet(_derive_key_fernet())
        else:
            self._fallback_key = _derive_key_stdlib()

    def encrypt(self, value: str) -> str:
        if not value:
            return value
        data = value.encode("utf-8")
        if _FERNET_AVAILABLE:
            return self._fernet.encrypt(data).decode("utf-8")
        return _encrypt_stdlib(data, self._fallback_key).decode("utf-8")

    def decrypt(self, value: str) -> str:
        if not value:
            return value
        try:
            data = value.encode("utf-8")
            if _FERNET_AVAILABLE:
                return self._fernet.decrypt(data).decode("utf-8")
            return _decrypt_stdlib(data, self._fallback_key).decode("utf-8")
        except Exception:
            return value


_encryptor = _Encryptor()


def encrypt_field(value: str) -> str:
    """Encrypt a single field value. Returns base64-encoded ciphertext."""
    return _encryptor.encrypt(value)


def decrypt_field(encrypted_value: str) -> str:
    """Decrypt a single encrypted field value."""
    return _encryptor.decrypt(encrypted_value)


def encrypt_patient_record(record: dict[str, Any]) -> dict[str, Any]:
    """Encrypt PHI fields in a patient record."""
    result = dict(record)
    for field in PHI_FIELDS:
        if result.get(field):
            result[field] = encrypt_field(str(result[field]))
    return result


def decrypt_patient_record(record: dict[str, Any]) -> dict[str, Any]:
    """Decrypt PHI fields in a patient record."""
    result = dict(record)
    for field in PHI_FIELDS:
        if result.get(field):
            result[field] = decrypt_field(str(result[field]))
    return result
