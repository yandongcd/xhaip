"""Tests for haip.licensing — 真实 RSA (RS256 JWT) License + 生产模式强制.

覆盖:
    - 有效 License 通过 / 篡改 payload / 篡改 signature / 过期 / 错公钥 / 缺公钥 fail-closed
    - generate_license 缺 LICENSE_SIGNING_KEY → ValueError
    - 生产模式: 启动校验 / max_agents / max_users 强制; 开发模式放行
"""

import json
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from haip.licensing import (
    LicenseError,
    LicenseInfo,
    LicenseManager,
    check_agent_capacity,
    check_user_capacity,
    enforce_startup,
    generate_license,
    license_limits,
    write_license_file,
)


def _gen_keypair() -> tuple[str, str]:
    """生成 RSA 密钥对, 返回 (private_pem, public_pem)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")
    pub_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return priv_pem, pub_pem


@pytest.fixture
def keypair():
    return _gen_keypair()


@pytest.fixture
def licensed_env(keypair, monkeypatch):
    """环境: LICENSE_PUBLIC_KEY + LICENSE_SIGNING_KEY 均已配置."""
    priv, pub = keypair
    monkeypatch.setenv("LICENSE_PUBLIC_KEY", pub)
    monkeypatch.setenv("LICENSE_SIGNING_KEY", priv)
    return priv, pub


class TestLicenseInfo:
    def test_valid_license(self):
        info = LicenseInfo(
            customer_name="南方医院",
            max_agents=50,
            max_users=200,
            expiry_date="2027-12-31",
            features=["pharmacy", "orthopedic"],
            signature="validsig",
            valid=True,
        )
        assert info.customer_name == "南方医院"
        assert info.max_agents == 50
        assert info.valid is True


class TestGenerateLicense:
    def test_generate_without_signing_key_raises(self, monkeypatch):
        """无 LICENSE_SIGNING_KEY → ValueError (无开发后门)."""
        monkeypatch.delenv("LICENSE_SIGNING_KEY", raising=False)
        with pytest.raises(ValueError):
            generate_license("测试医院", "TEST001")

    def test_generate_has_required_fields(self, licensed_env):
        data = generate_license(
            "测试医院",
            "TEST001",
            max_agents=30,
            max_users=100,
            expiry_days=365,
            features=["orthopedic", "cardiology"],
        )
        assert data["customer_name"] == "测试医院"
        assert data["max_agents"] == 30
        assert data["max_users"] == 100
        assert "signature" in data
        assert len(data["signature"]) > 0
        assert data["signature"].count(".") == 2  # JWT 三段式 (header.payload.sig)

    def test_generate_default_expiry(self, licensed_env):
        data = generate_license("默认医院", "DEFAULT01", max_agents=10, max_users=50)
        assert "expiry_date" in data
        assert len(data["features"]) >= 1

    def test_write_license_file(self, licensed_env):
        data = generate_license("TestWrite", "FILE01", max_agents=10, max_users=50)
        path = tempfile.mktemp(suffix=".json")
        try:
            write_license_file(data, path)
            with open(path) as f:
                written = json.load(f)
            assert written["customer_name"] == "TestWrite"
            assert "signature" in written
        finally:
            Path(path).unlink(missing_ok=True)


def _write_to_temp(data, suffix=".json"):
    """Helper: write license data to a temp file, returning the path."""
    path = tempfile.mktemp(suffix=suffix)
    write_license_file(data, path)
    return path


class TestLicenseManager:
    def test_load_valid_license(self, licensed_env):
        data = generate_license("有效医院", "VALID01", max_agents=20, max_users=80)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            assert mgr.is_valid() is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_get_info(self, licensed_env):
        data = generate_license("信息医院", "INFO01", max_agents=20, max_users=80,
                                features=["pharmacy"])
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            info = mgr.get_info()
            assert info.customer_name == "信息医院"
            assert info.max_agents == 20
        finally:
            Path(path).unlink(missing_ok=True)

    def test_is_feature_enabled(self, licensed_env):
        data = generate_license("功能医院", "FEAT01", max_agents=20, max_users=80,
                                features=["pharmacy", "orthopedic"])
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            assert mgr.is_feature_enabled("pharmacy") is True
            assert mgr.is_feature_enabled("orthopedic") is True
            assert mgr.is_feature_enabled("cardiology") is False
        finally:
            Path(path).unlink(missing_ok=True)

    def test_get_limits(self, licensed_env):
        data = generate_license("限制医院", "LIMIT01", max_agents=15, max_users=60)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            limits = mgr.get_limits()
            assert limits["max_agents"] == 15
            assert limits["max_users"] == 60
        finally:
            Path(path).unlink(missing_ok=True)

    def test_invalid_license_no_signature(self, keypair, monkeypatch):
        monkeypatch.setenv("LICENSE_PUBLIC_KEY", keypair[1])
        bad_data = {"customer_name": "伪造", "max_agents": 10, "max_users": 50,
                    "expiry_date": "2027-12-31"}
        path = tempfile.mktemp(suffix=".json")
        try:
            with open(path, "w") as f:
                json.dump(bad_data, f)
            mgr = LicenseManager(path)
            info = mgr.validate()
            assert info.valid is False
            assert "payload" in info.error
        finally:
            Path(path).unlink(missing_ok=True)

    def test_tampered_payload(self, licensed_env):
        """篡改 payload (未签名部分) → 与签名 claims 不符 → 拒绝."""
        data = generate_license("原版", "ORIG01", max_agents=20, max_users=80)
        data["payload"] = data["payload"].replace('"max_agents": 20', '"max_agents": 999')
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            info = mgr.validate()
            assert info.valid is False
            assert "Invalid license signature" in info.error
        finally:
            Path(path).unlink(missing_ok=True)

    def test_tampered_signature(self, licensed_env):
        """篡改 signature (JWT) → RS256 验签失败 → 拒绝."""
        data = generate_license("原版", "ORIG01", max_agents=20, max_users=80)
        # 篡改签名中部字符 (末位字符落在 base64 padding 位, 不影响解码字节)
        mid = len(data["signature"]) // 2
        data["signature"] = data["signature"][:mid] + "A" + data["signature"][mid + 1:]
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            info = mgr.validate()
            assert info.valid is False
            assert "signature" in info.error.lower()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_top_level_fields_not_trusted(self, licensed_env):
        """篡改 license 文件顶层字段 (未签名) 不影响限额 — 限额取自 claims."""
        data = generate_license("信任医院", "TRUST01", max_agents=20, max_users=80)
        data["max_agents"] = 99999
        data["max_users"] = 99999
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            assert mgr.is_valid() is True
            info = mgr.get_info()
            assert info.max_agents == 20
            assert info.max_users == 80
        finally:
            Path(path).unlink(missing_ok=True)

    def test_expired_license(self, licensed_env):
        """过期 License (expiry_days=-1) → 拒绝."""
        data = generate_license("过期医院", "EXP01", max_agents=10, max_users=50,
                                expiry_days=-1)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            info = mgr.validate()
            assert info.valid is False
            assert "expired" in info.error.lower()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_wrong_public_key(self, keypair, monkeypatch):
        """用另一把公钥验证 → 拒绝."""
        priv, _pub = keypair
        _other_priv, other_pub = _gen_keypair()
        monkeypatch.setenv("LICENSE_SIGNING_KEY", priv)
        data = generate_license("错钥医院", "WK01", max_agents=10, max_users=50)
        monkeypatch.setenv("LICENSE_PUBLIC_KEY", other_pub)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            info = mgr.validate()
            assert info.valid is False
            assert "signature" in info.error.lower()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_public_key_fails_closed(self, keypair, monkeypatch):
        """缺 LICENSE_PUBLIC_KEY → fail-closed, 永不放行."""
        priv, _pub = keypair
        monkeypatch.setenv("LICENSE_SIGNING_KEY", priv)
        data = generate_license("无钥医院", "NOKEY01", max_agents=10, max_users=50)
        path = _write_to_temp(data)
        monkeypatch.delenv("LICENSE_PUBLIC_KEY", raising=False)
        try:
            mgr = LicenseManager(path)
            info = mgr.validate()
            assert info.valid is False
            assert "未配置" in info.error
        finally:
            Path(path).unlink(missing_ok=True)

    def test_expiry_warning_far_future(self, licensed_env):
        data = generate_license("远医院", "FAR01", max_agents=10, max_users=50, expiry_days=365)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            warning = mgr.check_expiry_warning()
            assert warning is None  # far away
        finally:
            Path(path).unlink(missing_ok=True)

    def test_expiry_warning_approaching(self, licensed_env):
        data = generate_license("临期", "SOON01", max_agents=10, max_users=50, expiry_days=7)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            warning = mgr.check_expiry_warning()
            assert warning is not None
            assert "days" in warning
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_features_means_no_access(self, licensed_env):
        data = generate_license("无功能", "NOFEAT01", max_agents=10, max_users=50, features=[])
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            assert mgr.is_feature_enabled("anything") is False
        finally:
            Path(path).unlink(missing_ok=True)


class TestLicenseLimitsAccessor:
    def test_limits_zero_without_valid_license(self, monkeypatch):
        monkeypatch.delenv("LICENSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("HAIP_LICENSE_FILE", raising=False)
        limits = license_limits()
        assert limits == {"max_agents": 0, "max_users": 0}

    def test_limits_from_valid_license(self, licensed_env, monkeypatch, tmp_path):
        data = generate_license("限额医院", "QL01", max_agents=7, max_users=99)
        lic_file = tmp_path / "license.key"
        write_license_file(data, str(lic_file))
        monkeypatch.setenv("HAIP_LICENSE_FILE", str(lic_file))
        limits = license_limits()
        assert limits == {"max_agents": 7, "max_users": 99}


class TestStartupEnforcement:
    def test_production_invalid_license_blocks_startup(self, monkeypatch):
        """生产模式 + 无效 License → 阻断启动."""
        monkeypatch.setenv("HAIP_ENV", "production")
        monkeypatch.delenv("LICENSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("HAIP_LICENSE_FILE", raising=False)
        with pytest.raises(LicenseError):
            enforce_startup()

    def test_production_valid_license_passes(self, keypair, monkeypatch, tmp_path):
        monkeypatch.setenv("HAIP_ENV", "production")
        priv, pub = keypair
        monkeypatch.setenv("LICENSE_PUBLIC_KEY", pub)
        monkeypatch.setenv("LICENSE_SIGNING_KEY", priv)
        data = generate_license("生产医院", "PROD01", max_agents=48, max_users=100)
        lic_file = tmp_path / "license.key"
        write_license_file(data, str(lic_file))
        monkeypatch.setenv("HAIP_LICENSE_FILE", str(lic_file))
        enforce_startup()  # 不抛

    def test_dev_mode_permissive(self, monkeypatch):
        """开发模式 + 无效 License → 仅告警, 不阻断."""
        monkeypatch.delenv("LICENSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("HAIP_LICENSE_FILE", raising=False)
        monkeypatch.delenv("HAIP_ENV", raising=False)
        monkeypatch.delenv("HAIP_STRICT_SECURITY", raising=False)
        enforce_startup()  # 不抛


class TestAgentCapacityEnforcement:
    def test_max_agents_enforced_in_production(self, keypair, monkeypatch, tmp_path):
        """生产模式: 注册数 >= max_agents → 拒绝."""
        from haip.agent import DomainPlugin, _registry, register
        _registry.clear()
        monkeypatch.setenv("HAIP_ENV", "production")
        priv, pub = keypair
        monkeypatch.setenv("LICENSE_PUBLIC_KEY", pub)
        monkeypatch.setenv("LICENSE_SIGNING_KEY", priv)
        data = generate_license("上限医院", "LIM01", max_agents=2, max_users=10)
        lic_file = tmp_path / "license.key"
        write_license_file(data, str(lic_file))
        monkeypatch.setenv("HAIP_LICENSE_FILE", str(lic_file))

        assert register(DomainPlugin(name="a1", type="business")) is True
        assert register(DomainPlugin(name="a2", type="business")) is True
        assert register(DomainPlugin(name="a3", type="business")) is False  # 2 >= 2 → 拒绝
        assert len(_registry) == 2

    def test_max_agents_reegister_allowed_at_limit(self, keypair, monkeypatch, tmp_path):
        """同名校重注册 = 覆盖更新, 不占新增名额."""
        from haip.agent import DomainPlugin, _registry, register
        _registry.clear()
        monkeypatch.setenv("HAIP_ENV", "production")
        priv, pub = keypair
        monkeypatch.setenv("LICENSE_PUBLIC_KEY", pub)
        monkeypatch.setenv("LICENSE_SIGNING_KEY", priv)
        data = generate_license("上限医院", "LIM02", max_agents=1, max_users=10)
        lic_file = tmp_path / "license.key"
        write_license_file(data, str(lic_file))
        monkeypatch.setenv("HAIP_LICENSE_FILE", str(lic_file))

        assert register(DomainPlugin(name="b1", type="business")) is True
        assert register(DomainPlugin(name="b1", type="specialist")) is True  # 覆盖更新
        assert len(_registry) == 1

    def test_dev_mode_no_agent_enforcement(self, keypair, monkeypatch, tmp_path):
        """开发模式: 注册不限额."""
        from haip.agent import DomainPlugin, _registry, register
        _registry.clear()
        monkeypatch.delenv("HAIP_ENV", raising=False)
        monkeypatch.delenv("HAIP_STRICT_SECURITY", raising=False)
        priv, pub = keypair
        monkeypatch.setenv("LICENSE_PUBLIC_KEY", pub)
        monkeypatch.setenv("LICENSE_SIGNING_KEY", priv)
        data = generate_license("开发医院", "DEV01", max_agents=2, max_users=10)
        lic_file = tmp_path / "license.key"
        write_license_file(data, str(lic_file))
        monkeypatch.setenv("HAIP_LICENSE_FILE", str(lic_file))

        for i in range(6):
            assert register(DomainPlugin(name=f"d{i}", type="business")) is True

    def test_check_agent_capacity_dev_permissive(self, monkeypatch):
        monkeypatch.delenv("HAIP_ENV", raising=False)
        monkeypatch.delenv("HAIP_STRICT_SECURITY", raising=False)
        assert check_agent_capacity(999) == (True, "")


class TestUserCapacityEnforcement:
    def _make_auth(self):
        from haip.auth import AuthService
        return AuthService(backend="memory")

    def _set_prod_license(self, keypair, monkeypatch, tmp_path, max_users):
        monkeypatch.setenv("HAIP_ENV", "production")
        # auth.jwt 在生产模式下 import 即要求 JWT_SECRET_KEY (既有门禁)
        monkeypatch.setenv("JWT_SECRET_KEY", "test-prod-secret-" + "x" * 24)
        priv, pub = keypair
        monkeypatch.setenv("LICENSE_PUBLIC_KEY", pub)
        monkeypatch.setenv("LICENSE_SIGNING_KEY", priv)
        data = generate_license("用户上限", "USR01", max_agents=48, max_users=max_users)
        lic_file = tmp_path / "license.key"
        write_license_file(data, str(lic_file))
        monkeypatch.setenv("HAIP_LICENSE_FILE", str(lic_file))

    def test_max_users_enforced_in_production(self, keypair, monkeypatch, tmp_path):
        """生产模式: 活跃用户数超过 max_users → 拒绝登录."""
        self._set_prod_license(keypair, monkeypatch, tmp_path, max_users=3)
        auth = self._make_auth()
        for i in range(1, 4):
            auth.create_user(f"user{i}", "StrongPass@123", roles=["doctor"])

        # 恰在上限 (3 用户, max 3) → 可登录
        r = auth.authenticate("user1", "StrongPass@123")
        assert r["access_token"]

        # 超过上限 (4 > 3) → 拒绝
        auth.create_user("user4", "StrongPass@123", roles=["doctor"])
        with pytest.raises(ValueError) as exc:
            auth.authenticate("user1", "StrongPass@123")
        assert "License" in str(exc.value) or "上限" in str(exc.value)

    def test_dev_mode_no_user_enforcement(self, keypair, monkeypatch, tmp_path):
        """开发模式: 登录不受 License 用户数限制."""
        monkeypatch.delenv("HAIP_ENV", raising=False)
        monkeypatch.delenv("HAIP_STRICT_SECURITY", raising=False)
        priv, pub = keypair
        monkeypatch.setenv("LICENSE_PUBLIC_KEY", pub)
        monkeypatch.setenv("LICENSE_SIGNING_KEY", priv)
        data = generate_license("开发医院", "DEV02", max_agents=48, max_users=2)
        lic_file = tmp_path / "license.key"
        write_license_file(data, str(lic_file))
        monkeypatch.setenv("HAIP_LICENSE_FILE", str(lic_file))

        auth = self._make_auth()
        for i in range(1, 6):
            auth.create_user(f"dev{i}", "StrongPass@123", roles=["doctor"])
        r = auth.authenticate("dev5", "StrongPass@123")
        assert r["access_token"]

    def test_check_user_capacity_dev_permissive(self, monkeypatch):
        monkeypatch.delenv("HAIP_ENV", raising=False)
        monkeypatch.delenv("HAIP_STRICT_SECURITY", raising=False)
        assert check_user_capacity(999) == (True, "")
