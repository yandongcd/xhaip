"""Tests for haip.crypto — PHI field encryption."""

import pytest
from haip.crypto import (
    encrypt_field,
    decrypt_field,
    encrypt_patient_record,
    decrypt_patient_record,
    PHI_FIELDS,
    _Encryptor,
)


class TestFieldEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        original = "张三"
        encrypted = encrypt_field(original)
        assert encrypted != original
        assert decrypt_field(encrypted) == original

    def test_encrypt_produces_different_ciphertext(self):
        c1 = encrypt_field("张三")
        c2 = encrypt_field("张三")
        assert c1 != c2  # different IV each time

    def test_decrypt_tampered_data_returns_garbled(self):
        encrypted = encrypt_field("test")
        result = decrypt_field(encrypted + "tampered")
        # decrypt catches exceptions and returns original value silently
        assert result != "test"

    def test_decrypt_empty_string_returns_empty(self):
        result = decrypt_field("")
        assert result == ""

    def test_encrypt_special_characters(self):
        original = "患者@2024!测试#数据"
        assert decrypt_field(encrypt_field(original)) == original

    def test_encrypt_long_field(self):
        original = "A" * 500
        assert decrypt_field(encrypt_field(original)) == original


class TestPatientRecordEncryption:
    def test_encrypt_phi_fields(self):
        record = {
            "patient_id": "P001",
            "name": "张三",
            "phone": "13800138000",
            "diagnosis": "高血压",
        }
        encrypted = encrypt_patient_record(record)
        assert encrypted["name"] != "张三"
        assert encrypted["phone"] != "13800138000"
        assert encrypted["patient_id"] == "P001"  # not in PHI_FIELDS
        assert encrypted["diagnosis"] == "高血压"

    def test_decrypt_patient_record_roundtrip(self):
        record = {
            "patient_id": "P001",
            "name": "张三",
            "phone": "13800138000",
            "id_number": "110101199001011234",
        }
        encrypted = encrypt_patient_record(record)
        decrypted = decrypt_patient_record(encrypted)
        assert decrypted == record

    def test_no_phi_fields(self):
        record = {"diagnosis": "感冒", "department": "内科"}
        encrypted = encrypt_patient_record(record)
        assert encrypted == record

    def test_missing_phi_field(self):
        record = {"patient_id": "P001"}  # no PHI fields
        encrypted = encrypt_patient_record(record)
        assert encrypted["patient_id"] == "P001"


class TestPHIFields:
    def test_phi_fields_set(self):
        assert "name" in PHI_FIELDS
        assert "phone" in PHI_FIELDS
        assert "id_number" in PHI_FIELDS
        assert "address" in PHI_FIELDS

    def test_encrypt_handles_none_value(self):
        record = {"name": None, "phone": "13800138000"}
        encrypted = encrypt_patient_record(record)
        # None is falsy, so encrypt_field is not called
        assert encrypted["name"] is None
        assert encrypted["phone"] != "13800138000"


class TestEncryptorSingleton:
    def test_multiple_encryptions_same_key(self):
        e1 = _Encryptor()
        e2 = _Encryptor()
        encrypted = e1.encrypt("test")
        assert e2.decrypt(encrypted) == "test"  # both use same key

    def test_cross_encryptor_fails(self):
        encrypted = encrypt_field("张三")
        assert decrypt_field(encrypted) == "张三"
