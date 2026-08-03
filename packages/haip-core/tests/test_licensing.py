"""Tests for haip.licensing — license management."""

import json
import tempfile
from pathlib import Path

import pytest

from haip.licensing import (
    LicenseInfo,
    LicenseManager,
    generate_license,
    write_license_file,
)


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
    def test_generate_has_required_fields(self):
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

    def test_generate_default_expiry(self):
        data = generate_license("默认医院", "DEFAULT01", max_agents=10, max_users=50)
        assert "expiry_date" in data
        assert len(data["features"]) >= 1

    def test_write_license_file(self):
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


def _write_to_temp(data):
    """Helper: write license data to a temp file, returning the path."""
    path = tempfile.mktemp(suffix=".json")
    write_license_file(data, path)
    return path


class TestLicenseManager:
    def test_load_valid_license(self):
        data = generate_license("有效医院", "VALID01", max_agents=20, max_users=80)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            assert mgr.is_valid() is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_get_info(self):
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

    def test_is_feature_enabled(self):
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

    def test_get_limits(self):
        data = generate_license("限制医院", "LIMIT01", max_agents=15, max_users=60)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            limits = mgr.get_limits()
            assert limits["max_agents"] == 15
            assert limits["max_users"] == 60
        finally:
            Path(path).unlink(missing_ok=True)

    def test_invalid_license_no_signature(self):
        bad_data = {"customer_name": "伪造", "max_agents": 10, "max_users": 50, "expiry_date": "2027-12-31"}
        path = tempfile.mktemp(suffix=".json")
        try:
            with open(path, "w") as f:
                json.dump(bad_data, f)
            mgr = LicenseManager(path)
            assert mgr.is_valid() is False
        finally:
            Path(path).unlink(missing_ok=True)

    def test_tampered_license(self):
        data = generate_license("原版", "ORIG01", max_agents=20, max_users=80)
        data["payload"] = data["payload"].replace('"max_agents": 20', '"max_agents": 999')
        path = tempfile.mktemp(suffix=".json")
        try:
            with open(path, "w") as f:
                json.dump(data, f)
            mgr = LicenseManager(path)
            assert mgr.is_valid() is False
        finally:
            Path(path).unlink(missing_ok=True)

    def test_expiry_warning_far_future(self):
        data = generate_license("远医院", "FAR01", max_agents=10, max_users=50, expiry_days=365)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            warning = mgr.check_expiry_warning()
            assert warning is None  # far away
        finally:
            Path(path).unlink(missing_ok=True)

    def test_expiry_warning_approaching(self):
        data = generate_license("临期", "SOON01", max_agents=10, max_users=50, expiry_days=7)
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            warning = mgr.check_expiry_warning()
            assert warning is not None
            assert "days" in warning
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_features_means_no_access(self):
        data = generate_license("无功能", "NOFEAT01", max_agents=10, max_users=50, features=[])
        path = _write_to_temp(data)
        try:
            mgr = LicenseManager(path)
            assert mgr.is_feature_enabled("anything") is False
        finally:
            Path(path).unlink(missing_ok=True)
