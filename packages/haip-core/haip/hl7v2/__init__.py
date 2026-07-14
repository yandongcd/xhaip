"""HL7 v2 Message Parser — ADT/ORM/ORU message parsing.

Parses standard HL7 v2.x segments:
    - MSH (Message Header)
    - PID (Patient Identification)
    - OBR (Observation Request)
    - OBX (Observation Result)
    - PV1 (Patient Visit)

Supports message types: ADT^A01, ADT^A02, ADT^A03, ADT^A08, ORM^O01, ORU^R01

The parser is self-contained (no external HL7 library required).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Parsed data structures ──


@dataclass
class HL7Message:
    """Parsed HL7 v2 message."""

    message_type: str = ""
    trigger_event: str = ""
    sending_app: str = ""
    sending_facility: str = ""
    receiving_app: str = ""
    receiving_facility: str = ""
    message_datetime: str = ""
    message_control_id: str = ""

    patient_id: str = ""
    patient_name: str = ""
    patient_dob: str = ""
    patient_gender: str = ""
    patient_address: str = ""
    patient_phone: str = ""

    visit_number: str = ""
    admission_date: str = ""
    service: str = ""
    attending_doctor: str = ""

    observations: list[dict[str, Any]] = field(default_factory=list)
    raw_segments: dict[str, list[str]] = field(default_factory=dict)


# ── Parser ──


def parse_hl7(raw_message: str) -> HL7Message:
    """Parse a raw HL7 v2 message string into a structured HL7Message.

    Args:
        raw_message: Raw HL7 message with segment separators (CR or \\r).

    Returns:
        HL7Message with parsed fields.

    Example:
        >>> msg = "MSH|^~\\&|HIS|HOSPITAL|||20260712100000||ADT^A01|MSG001|P|2.5\\rPID|||P001^^^HOSPITAL||张^三||19800601|M"
        >>> parsed = parse_hl7(msg)
        >>> parsed.patient_id
        'P001'
    """
    msg = raw_message.replace("\r\n", "\r").replace("\n", "\r")
    result = HL7Message()

    for segment_line in msg.strip().split("\r"):
        if not segment_line:
            continue

        fields = segment_line.split("|")
        segment_id = fields[0]

        _parse_segment(result, segment_id, fields)

    return result


def _parse_segment(result: HL7Message, segment_id: str, fields: list[str]):
    """Parse a single HL7 segment."""

    if segment_id == "MSH":
        _parse_msh(result, fields)
    elif segment_id == "PID":
        _parse_pid(result, fields)
    elif segment_id == "PV1":
        _parse_pv1(result, fields)
    elif segment_id == "OBR":
        _parse_obr(result, fields)
    elif segment_id == "OBX":
        _parse_obx(result, fields)

    result.raw_segments.setdefault(segment_id, []).append(fields)


def _parse_msh(result: HL7Message, fields: list[str]):
    result.sending_app = _safe_field(fields, 2, "")
    result.sending_facility = _safe_field(fields, 3, "")
    result.receiving_app = _safe_field(fields, 4, "")
    result.receiving_facility = _safe_field(fields, 5, "")
    result.message_datetime = _safe_field(fields, 6, "")
    # MSH-9 = message type^trigger event
    msg_type = _safe_field(fields, 8, "")
    parts = msg_type.split("^") if "^" in msg_type else [msg_type, ""]
    result.message_type = parts[0]
    result.trigger_event = parts[1] if len(parts) > 1 else ""
    result.message_control_id = _safe_field(fields, 9, "")


def _parse_pid(result: HL7Message, fields: list[str]):
    # PID.3 = patient identifier list
    pid_list = _safe_field(fields, 3, "")
    pid_parts = pid_list.split("^")
    result.patient_id = pid_parts[0] if pid_parts else ""

    # PID.5 = patient name (last^first^middle)
    name = _safe_field(fields, 5, "")
    result.patient_name = name.replace("^", "")

    # PID.7 = date of birth
    result.patient_dob = _safe_field(fields, 7, "")

    # PID.8 = administrative sex
    result.patient_gender = _safe_field(fields, 8, "")

    # PID.11 = address
    result.patient_address = _safe_field(fields, 11, "")

    # PID.13 = phone
    result.patient_phone = _safe_field(fields, 13, "")


def _parse_pv1(result: HL7Message, fields: list[str]):
    # PV1.2 = patient class
    result.visit_number = _safe_field(fields, 19, "")  # visit number
    result.service = _safe_field(fields, 3, "")  # service
    result.admission_date = _safe_field(fields, 44, "")  # admit date/time
    # PV1.7 = attending doctor
    result.attending_doctor = _safe_field(fields, 7, "").replace("^", " ")


def _parse_obr(result: HL7Message, fields: list[str]):
    obr = {
        "set_id": _safe_field(fields, 1, ""),
        "test_code": _safe_field(fields, 4, ""),
        "test_name": _safe_field(fields, 4, "").split("^")[1] if "^" in _safe_field(fields, 4, "") else "",
        "order_date": _safe_field(fields, 7, ""),
        "ordering_provider": _safe_field(fields, 16, ""),
        "result_date": _safe_field(fields, 22, ""),
    }
    result.observations.append({"type": "OBR", "data": obr})


def _parse_obx(result: HL7Message, fields: list[str]):
    obx = {
        "set_id": _safe_field(fields, 1, ""),
        "value_type": _safe_field(fields, 2, ""),
        "test_code": _safe_field(fields, 3, "").split("^")[0],
        "test_name": _safe_field(fields, 3, "").split("^")[1] if "^" in _safe_field(fields, 3, "") else "",
        "value": _safe_field(fields, 5, ""),
        "units": _safe_field(fields, 6, ""),
        "reference_range": _safe_field(fields, 7, ""),
        "abnormal_flags": _safe_field(fields, 8, ""),
        "result_date": _safe_field(fields, 14, ""),
    }
    result.observations.append({"type": "OBX", "data": obx})


def _safe_field(fields: list[str], index: int, default: str = "") -> str:
    """Safely get a field by 1-based index."""
    if index < len(fields):
        return fields[index].strip()
    return default


# ── Message builders ──


def build_hl7_adt(
    patient_id: str,
    patient_name: str,
    event_type: str = "A01",
    gender: str = "",
    dob: str = "",
) -> str:
    """Build a simple HL7 ADT message.

    Args:
        patient_id: Patient identifier.
        patient_name: Patient name (will be formatted as last^first).
        event_type: ADT event type (A01=admit, A02=transfer, A03=discharge, A08=update).
        gender: M or F.
        dob: Date of birth (YYYYMMDD).
    """
    from datetime import datetime

    now = datetime.now().strftime("%Y%m%d%H%M%S")
    control_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

    segments = [
        f"MSH|^~\\&|xhaip|HOSPITAL|||{now}||ADT^{event_type}|MSG_{control_id}|P|2.5",
        f"PID|||{patient_id}^^^HOSPITAL||{patient_name}||{dob}|{gender}",
    ]

    if event_type == "A01":
        segments.append(f"PV1||I|||||||||||||||||VISIT_{patient_id}|||||||||||||||||||||||||{now}")

    return "\r".join(segments)


def build_hl7_oru(
    patient_id: str,
    patient_name: str,
    observations: list[dict[str, str]],
) -> str:
    """Build an HL7 ORU^R01 (observation result) message.

    Args:
        patient_id: Patient identifier.
        patient_name: Patient name.
        observations: List of dicts with keys: test_code, test_name, value, units.
    """
    from datetime import datetime

    now = datetime.now().strftime("%Y%m%d%H%M%S")
    control_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

    segments = [
        f"MSH|^~\\&|LIS|LAB|||{now}||ORU^R01|MSG_{control_id}|P|2.5",
        f"PID|||{patient_id}^^^HOSPITAL||{patient_name}",
        f"OBR|1|||ALL|||{now}",
    ]

    for i, obs in enumerate(observations, 1):
        code = obs.get("test_code", "")
        name = obs.get("test_name", "")
        value = obs.get("value", "")
        units = obs.get("units", "")
        ref_range = obs.get("reference_range", "")
        flags = obs.get("flags", "")

        segments.append(
            f"OBX|{i}|NM|{code}^{name}||{value}|{units}|{ref_range}|{flags}||||F"
        )

    return "\r".join(segments)


# ── Validation ──


def validate_hl7(raw_message: str) -> tuple[bool, list[str]]:
    """Validate an HL7 message. Returns (is_valid, errors)."""
    errors = []

    if not raw_message.strip():
        return False, ["Empty message"]

    lines = raw_message.replace("\r\n", "\r").replace("\n", "\r").strip().split("\r")

    if not lines[0].startswith("MSH"):
        errors.append("First segment must be MSH")

    fields = lines[0].split("|")
    if len(fields) < 12:
        errors.append("MSH segment has fewer than 12 fields")

    # Check encoding characters
    if fields[0] != "MSH" and len(fields) >= 2:
        pass  # MSH.1 is the field separator, already consumed

    # Check for PID segment (required for most message types)
    has_pid = any(line.startswith("PID") for line in lines)
    if not has_pid and any("PID" in line for line in lines[:3]):
        has_pid = True
    if not has_pid:
        # Some messages (ACK) don't need PID
        msg_type_line = lines[0]
        if "ACK" not in msg_type_line:
            errors.append("Missing PID segment")

    return len(errors) == 0, errors
