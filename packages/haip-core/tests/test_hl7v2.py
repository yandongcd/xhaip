"""Tests for haip.hl7v2 — HL7 v2.x message parser."""

import pytest
from haip.hl7v2 import (
    parse_hl7,
    HL7Message,
    build_hl7_adt,
    build_hl7_oru,
    validate_hl7,
)


class TestParseHL7:
    def test_parse_minimal_adt(self):
        msg = (
            "MSH|^~\\&|HIS|HOSPITAL|||202401010800||ADT^A01|MSG001|P|2.5\r"
            "PID|1||P001||张三^ZHANG^SAN||19900101|M\r"
            "PV1|1|I|ICU^01^01||||1234^王五^WANG"
        )
        result = parse_hl7(msg)
        assert isinstance(result, HL7Message)
        assert result.message_type == "ADT"
        assert result.trigger_event == "A01"
        assert result.message_control_id == "MSG001"
        assert result.patient_id == "P001"
        assert result.patient_name == "张三ZHANGSAN"
        assert result.patient_dob == "19900101"
        assert result.patient_gender == "M"

    def test_parse_oru_observation(self):
        msg = (
            "MSH|^~\\&|LIS|LAB|||202401010900||ORU^R01|MSG002|P|2.5\r"
            "PID|1||P002||李四\r"
            "OBR|1|||1554-5^Glucose^LN\r"
            "OBX|1|NM|1554-5^Glucose^LN||5.6|mmol/L|3.9-6.1|N|||F"
        )
        result = parse_hl7(msg)
        # Both OBR and OBX go into observations
        assert len(result.observations) == 2
        obr = result.observations[0]
        assert obr["type"] == "OBR"
        assert obr["data"]["test_code"] == "1554-5^Glucose^LN"
        obx = result.observations[1]
        assert obx["type"] == "OBX"
        assert obx["data"]["test_code"] == "1554-5"
        assert obx["data"]["test_name"] == "Glucose"
        assert obx["data"]["value"] == "5.6"

    def test_parse_multiple_obx(self):
        msg = (
            "MSH|^~\\&|HIS|HOSPITAL|||202401011000||ORU^R01|MSG003|P|2.5\r"
            "PID|1||P003||王五\r"
            "OBR|1|||24323-8^CBC^LN\r"
            "OBX|1|NM|26453-1^RBC^LN||4.5|10^12/L|3.5-5.5|N|||F\r"
            "OBX|2|NM|26464-8^WBC^LN||7.2|10^9/L|4.0-10.0|N|||F\r"
            "OBX|3|NM|26474-7^HGB^LN||140|g/L|120-160|N|||F"
        )
        result = parse_hl7(msg)
        # 1 OBR + 3 OBX = 4 observations
        assert len(result.observations) == 4
        assert result.observations[0]["type"] == "OBR"
        assert result.observations[1]["type"] == "OBX"
        assert result.observations[1]["data"]["value"] == "4.5"
        assert result.observations[3]["data"]["test_name"] == "HGB"

    def test_parse_windows_newlines(self):
        msg = (
            "MSH|^~\\&|HIS|HOSPITAL|||202401010800||ADT^A01|MSG004|P|2.5\r\n"
            "PID|1||P004||赵六"
        )
        result = parse_hl7(msg)
        assert result.patient_id == "P004"

    def test_parse_regular_newlines(self):
        msg = (
            "MSH|^~\\&|HIS|HOSPITAL|||202401010800||ADT^A01|MSG005|P|2.5\n"
            "PID|1||P005||钱七"
        )
        result = parse_hl7(msg)
        assert result.patient_id == "P005"

    def test_parse_empty_segments(self):
        msg = (
            "MSH|^~\\&|HIS|HOSPITAL|||202401010800||ADT^A01|MSG006|P|2.5\n\n"
            "PID|1||P006||孙八\n"
            "\n\n"
        )
        result = parse_hl7(msg)
        assert result.patient_id == "P006"

    def test_parse_without_pv1(self):
        msg = (
            "MSH|^~\\&|HIS|HOSPITAL|||202401010800||ADT^A01|MSG007|P|2.5\r"
            "PID|1||P007||周九"
        )
        result = parse_hl7(msg)
        assert result.patient_id == "P007"
        assert result.visit_number == ""

    def test_parse_pv1_fields(self):
        msg = (
            "MSH|^~\\&|HIS|HOSPITAL|||202401010800||ADT^A01|MSG008|P|2.5\r"
            "PID|1||P008||吴十\r"
            "PV1|1|I|ICU^01^01||||1234^王五^WANG"
        )
        result = parse_hl7(msg)
        assert result.visit_number == ""
        assert result.attending_doctor == "1234 王五 WANG"

    def test_parse_obr_only(self):
        msg = (
            "MSH|^~\\&|LIS|LAB|||202401011200||ORU^R01|MSG009|P|2.5\r"
            "PID|1||P009||TEST\r"
            "OBR|1|||1554-5^Glucose^LN||202401011200|202401011230|||||5678^DR_LI"
        )
        result = parse_hl7(msg)
        # OBR now adds to observations
        assert len(result.observations) == 1
        assert result.observations[0]["type"] == "OBR"
        assert result.observations[0]["data"]["test_code"] == "1554-5^Glucose^LN"
        assert "OBR" in result.raw_segments

    def test_parse_hl7_message_with_empty_fields(self):
        msg = (
            "MSH|^~\\&|HIS|||LAB||202401010800||ORU^R01|MSG010|P|2.5\r"
            "PID|1||P010||\r"
            "OBX|1|NM|test^Test|||mmol/L|3.9-6.1|N|||F"
        )
        result = parse_hl7(msg)
        assert result.patient_id == "P010"


class TestBuildHL7:
    def test_build_adt_a01(self):
        msg = build_hl7_adt("P100", "测试病人", event_type="A01", gender="M", dob="19900101")
        assert "ADT^A01" in msg
        assert "P100" in msg
        assert "测试病人" in msg

    def test_build_adt_a08(self):
        msg = build_hl7_adt("P101", "李病人", event_type="A08", gender="F", dob="19850515")
        assert "ADT^A08" in msg
        assert "P101" in msg

    def test_build_oru(self):
        observations = [
            {"test_code": "1554-5", "test_name": "Glucose", "value": "5.6", "units": "mmol/L", "reference_range": "3.9-6.1"},
            {"test_code": "26464-8", "test_name": "WBC", "value": "7.2", "units": "10^9/L", "reference_range": "4.0-10.0"},
        ]
        msg = build_hl7_oru("P102", "王病人", observations)
        assert "ORU^R01" in msg
        assert "P102" in msg
        assert "Glucose" in msg
        assert "WBC" in msg

    def test_build_oru_empty_observations(self):
        msg = build_hl7_oru("P103", "空", [])
        assert "ORU^R01" in msg
        assert "P103" in msg


class TestValidateHL7:
    def test_valid_message(self):
        msg = build_hl7_adt("P200", "测试", event_type="A01", gender="M", dob="19900101")
        valid, errors = validate_hl7(msg)
        assert valid is True
        assert len(errors) == 0

    def test_empty_message(self):
        valid, errors = validate_hl7("")
        assert valid is False
        assert len(errors) > 0

    def test_missing_msh(self):
        valid, errors = validate_hl7("PID|1||P201||病人")
        assert valid is False

    def test_short_pid(self):
        valid, errors = validate_hl7("MSH|^~\\&|HIS|HOSPITAL|||2024||ADT|1|P\nPID|1|")
        assert valid is False


class TestHL7MessageModel:
    def test_default_values(self):
        msg = HL7Message()
        assert msg.message_type == ""
        assert msg.patient_id == ""
        assert msg.patient_name == ""
        assert msg.observations == []

    def test_raw_segments(self):
        hl7 = parse_hl7(
            "MSH|^~\\&|HIS|HOSPITAL|||202401010800||ADT^A01|MSG020|P|2.5\r"
            "PID|1||P020||测试\r"
            "NTE|1||备注信息"
        )
        assert len(hl7.raw_segments) > 0
        assert "MSH" in hl7.raw_segments
