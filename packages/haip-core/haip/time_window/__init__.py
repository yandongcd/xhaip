"""时间窗口引擎 — 全院时间窗口注册、状态追踪、复合窗口与 SLA 统计.

Ported from haip-0710 (agents.domains.haip.time_window) into haip-core as a
generic engine. Timeline definitions live in
packages/haip-hospital/knowledge/timelines/registry.yaml.
"""

from haip.time_window.engine import (
    clear_window,
    get_composite_state,
    get_window_state,
    list_active_windows,
    record_event,
    register_composite_window,
    register_sub_window,
    register_window,
    resolve_composite_verdict,
)
from haip.time_window.registry import (
    get_timeline,
    list_timelines,
    load_all,
    register_timeline,
)
from haip.time_window.sla import get_sla_stats

__all__ = [
    "register_window",
    "get_window_state",
    "list_active_windows",
    "clear_window",
    "record_event",
    "register_composite_window",
    "register_sub_window",
    "get_composite_state",
    "resolve_composite_verdict",
    "load_all",
    "get_timeline",
    "register_timeline",
    "list_timelines",
    "get_sla_stats",
]
