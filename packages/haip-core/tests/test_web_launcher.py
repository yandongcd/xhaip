"""Tests for haip.web_launcher — Agent web service launcher."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from haip.web_launcher import DEFAULT_PORTS, _port_in_use, validate


class TestPortInUse:
    def test_port_free_on_high_port(self):
        assert not _port_in_use("127.0.0.1", 59999)

    def test_port_free_on_random_port(self):
        assert not _port_in_use("127.0.0.1", 63999)

    def test_invalid_host_returns_false(self):
        result = _port_in_use("255.255.255.255", 12345)
        assert not result


class TestDefaultPorts:
    def test_known_ports_exist(self):
        assert DEFAULT_PORTS["pharmacy"] == 8770
        assert DEFAULT_PORTS["orthopedic-surgery"] == 8765
        assert DEFAULT_PORTS["haip"] == 8769

    def test_agent_count(self):
        assert len(DEFAULT_PORTS) >= 10


class TestValidate:
    def test_validate_returns_dict(self):
        result = validate("127.0.0.1")
        assert isinstance(result, dict)
        assert "valid" in result
        assert "agents" in result
        assert "total" in result

    def test_validate_has_agents(self):
        result = validate("127.0.0.1")
        assert isinstance(result["agents"], dict)
        assert isinstance(result["total"], int)
