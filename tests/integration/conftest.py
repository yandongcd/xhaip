"""集成测试共享 fixtures."""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.agent import _registry, load_from_dir  # noqa: E402
from haip.a2a import clear_history  # noqa: E402

YAML_DIR = project_root / "packages" / "haip-hospital" / "agents" / "definitions"


@pytest.fixture(autouse=True)
def clean_registry():
    """每个测试前清空注册表和调用历史。"""
    _registry.clear()
    clear_history()


@pytest.fixture
def load_all_agents():
    """加载所有 YAML 定义（一次性）。"""
    load_from_dir(str(YAML_DIR))


@pytest.fixture
def sample_elderly_patient():
    return {
        "patient_id": "P001", "age": 78, "weight_kg": 55.0, "height_cm": 165.0,
        "lab_results": {"albumin": 28.0, "crp": 80.0, "creatinine": 120.0,
                        "troponin": 0.02, "inr": 2.5, "glucose": 7.2},
    }


@pytest.fixture
def sample_young_patient():
    return {
        "patient_id": "P002", "age": 35, "weight_kg": 75.0, "height_cm": 178.0,
        "lab_results": {"albumin": 45.0, "crp": 3.0, "creatinine": 88.0},
    }


@pytest.fixture
def sample_child_patient():
    return {
        "patient_id": "P003", "age_months": 48, "weight_kg": 16.0, "height_cm": 102.0,
        "symptoms": ["fever", "cough", "tachypnea"],
    }
