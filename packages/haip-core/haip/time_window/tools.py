"""时间窗口引擎 — Tool Manifest（Nexent MCP 注册 + BaseTool 注册）."""

from __future__ import annotations

TOOL_MANIFEST: dict = {
    "name": "time_window",
    "description": "时间窗口引擎 — 全院时间窗口数据中心/注册/状态追踪/SLA统计",
    "agent_type": "master_data",
    "department": "信息中心",
    "maintainer": "信息中心平台组",
    "api_version": "v1",
    "dispatch_names": {
        "time_window.register": "register",
        "time_window.get_state": "get_state",
        "time_window.list_active": "list_active",
        "time_window.clear": "clear",
        "time_window.record_event": "record_event",
        "time_window.get_sla_stats": "get_sla_stats",
        "time_window.list_timelines": "list_timelines",
    },
    "tools": [
        {
            "name": "time_window.register",
            "description": "为指定患者注册一个时间窗口，返回窗口令牌。如需自动获取起点时间，不传 start_time 则使用当前时间",
            "parameters": {
                "patient_id": {"type": "string", "required": True, "description": "患者 ID"},
                "timeline_id": {"type": "string", "required": True, "description": "时间窗口定义 ID（如 'timeline-hip-fracture-48h'）"},
                "start_time": {"type": "string", "required": False, "description": "ISO 8601 起点时间，不提供则使用当前时间"},
            },
            "output_schema": {
                "window_token": "str",
                "timeline_id": "str",
                "state": "str",
                "start_time": "str",
                "deadline": "str",
                "remaining_hours": "float",
                "urgency": "str",
                "escalation_plan": "list",
            },
        },
        {
            "name": "time_window.get_state",
            "description": "查询指定窗口令牌的当前状态，含剩余时间、紧急度、事件历史",
            "parameters": {
                "window_token": {"type": "string", "required": True, "description": "register() 返回的窗口令牌"},
            },
            "output_schema": {
                "window_token": "str",
                "state": "str",
                "remaining_hours": "float",
                "urgency": "str",
                "deadline": "str",
                "events": "list",
            },
        },
        {
            "name": "time_window.list_active",
            "description": "列出指定患者的所有活跃（非 expired/cleared）窗口",
            "parameters": {
                "patient_id": {"type": "string", "required": True, "description": "患者 ID"},
                "category": {"type": "string", "required": False, "description": "按类别筛选: emergency/urgent/monitoring/followup"},
                "sort_by": {"type": "string", "required": False, "description": "排序方式: urgency/remaining/deadline，默认 urgency"},
            },
            "output_schema": {"windows": "list"},
        },
        {
            "name": "time_window.clear",
            "description": "将窗口标记为已完成（cleared），停止追踪",
            "parameters": {
                "window_token": {"type": "string", "required": True, "description": "窗口令牌"},
                "reason": {"type": "string", "required": False, "description": "完成原因（如 surgery_completed / tPA_administered）"},
            },
            "output_schema": {"status": "str", "was_expired": "bool", "on_time": "bool"},
        },
        {
            "name": "time_window.record_event",
            "description": "在窗口时间线上追加一个事件记录（如延迟因素触发、MDT 启动）",
            "parameters": {
                "window_token": {"type": "string", "required": True, "description": "窗口令牌"},
                "event_type": {"type": "string", "required": True, "description": "事件类型: delay_factor_triggered / treatment_started / mdt_called / patient_transferred"},
                "description": {"type": "string", "required": False, "description": "事件描述"},
                "timestamp": {"type": "string", "required": False, "description": "ISO 8601，默认当前时间"},
            },
            "output_schema": {"status": "str", "event_type": "str", "timestamp": "str"},
        },
        {
            "name": "time_window.get_sla_stats",
            "description": "查询某科室/某窗口的达标率统计与根因分析",
            "parameters": {
                "department": {"type": "string", "required": False, "description": "科室 ID"},
                "timeline_id": {"type": "string", "required": False, "description": "窗口定义 ID"},
                "date_from": {"type": "string", "required": False, "description": "ISO 8601 起始日期"},
                "date_to": {"type": "string", "required": False, "description": "ISO 8601 截止日期"},
            },
            "output_schema": {
                "compliance_rate": "float",
                "total_windows": "int",
                "completed_on_time": "int",
                "completed_late": "int",
                "delay_root_causes": "dict",
            },
        },
        {
            "name": "time_window.list_timelines",
            "description": "列出所有已注册的时间窗口定义",
            "parameters": {
                "department": {"type": "string", "required": False, "description": "按科室筛选"},
            },
            "output_schema": {"timelines": "list"},
        },
    ],
}
