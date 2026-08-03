"""时间窗口引擎 — 数据模型."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WindowStateEnum(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    WARNING = "warning"
    CRITICAL = "critical"
    EXPIRED = "expired"
    CLEARED = "cleared"


class WindowCategory(str, Enum):
    EMERGENCY = "emergency"
    URGENT = "urgent"
    MONITORING = "monitoring"
    FOLLOWUP = "followup"


class EscalationLevel(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class DeadlineUnit(str, Enum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


@dataclass
class DeadlineSpec:
    value: float
    unit: DeadlineUnit


@dataclass
class EscalationThreshold:
    at_value: float        # 剩余多少时间时触发
    unit: str              # minutes | hours | days
    level: EscalationLevel


@dataclass
class ReEvaluationSpec:
    active_interval_minutes: int = 0
    active_interval_hours: int = 0
    active_interval_days: int = 0
    escalation_threshold: list[EscalationThreshold] = field(default_factory=list)


@dataclass
class TimelineSpec:
    id: str
    name: str
    abbr: str
    category: WindowCategory
    department: str
    start_event: str
    deadline: DeadlineSpec
    re_evaluation: ReEvaluationSpec
    guideline_ref: list[str]
    trust_level: str = "T1"
    owner: str = ""
    status: str = "active"


@dataclass
class WindowEvent:
    timestamp: str
    event_type: str
    description: str = ""
    old_state: str = ""
    new_state: str = ""


@dataclass
class WindowState:
    window_token: str
    timeline_id: str
    patient_id: str
    state: WindowStateEnum
    start_time: str
    deadline: str
    events: list[WindowEvent]
    urgency: str = "normal"
    created_at: str = ""


@dataclass
class RegisterResult:
    window_token: str
    timeline_id: str
    state: str
    start_time: str
    deadline: str
    remaining_hours: float
    urgency: str
    escalation_plan: list[dict[str, Any]]


class SubWindowMode(str, Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"


class CompositionRule(str, Enum):
    CRITICAL_PATH = "critical_path"
    SUM = "sum"
    MAX = "max"


@dataclass
class SubWindowSpec:
    member_agent_id: str
    timeline_id: str
    mode: SubWindowMode = SubWindowMode.PARALLEL
    depends_on: list[str] = field(default_factory=list)
    trigger_condition: str | None = None
    deadline_hours: float = 0
    escalation_level: str = "warning"


@dataclass
class CompositeWindowSpec:
    parent_timeline_id: str
    composition_rule: CompositionRule = CompositionRule.CRITICAL_PATH
    sub_windows: list[SubWindowSpec] = field(default_factory=list)


@dataclass
class CompositeWindowState:
    parent_token: str
    parent_timeline_id: str
    patient_id: str
    sub_states: dict[str, str]
    critical_path: float
    available_slack: float
    status: str
    escalated_windows: list[str]
    sub_windows: list[SubWindowSpec] = field(default_factory=list)
    composition_rule: str = "critical_path"
    created_at: str = ""
    updated_at: str = ""


@dataclass
class SlaStats:
    department: str
    timeline_id: str
    period: dict[str, str]
    total_windows: int
    completed_on_time: int
    completed_late: int
    still_active: int
    compliance_rate: float
    median_completion_hours: float
    delay_root_causes: dict[str, int]
