"""Shared lab reference-range helper — WS/T 404 ranges via haip-core roles.

Ported from haip-0710 (agents.domains.haip.rules.core.knowledge).
Adapted: reference-range implementation now lives in haip.togaf.roles.
"""

from __future__ import annotations

from typing import Any

try:
    from haip.togaf.roles import check_range as _core_check_range
except ImportError:  # haip-core not importable (partial env)
    _core_check_range = None


def check_range(test_name: str, value: Any) -> dict[str, Any]:
    """Check if a lab value is within reference range.

    Returns {"abnormal": bool, "direction": "偏低"|"偏高"|""}.
    Unknown test names and unparseable values never flag abnormal (fail-safe).
    """
    if _core_check_range is None:
        return {"abnormal": False, "direction": ""}
    try:
        result = _core_check_range(test_name, value)
    except Exception:
        return {"abnormal": False, "direction": ""}
    if result is None:
        return {"abnormal": False, "direction": ""}
    return result
