"""医学 Agent 评测框架 (haip.eval) — CP-Env 三维度 + Auto-MOOVE judge 协议.

场景: 数字病人 × 任务模板 (tasks/*.yaml) → 工具链执行 → 检查点评分 → 报告.
"""

from haip.eval.checkpoints import evaluate_checkpoint, evaluate_stage_checkpoints
from haip.eval.runner import EvalRunner, run_all
from haip.eval.scenario import (
    EvalScenario,
    build_scenarios,
    evaluate_scenario_stages,
    list_tasks,
    load_patients_for_task,
    load_task,
)
from haip.eval.scorer import EvalScore, score_scenario_rules

__all__ = [
    "EvalScenario",
    "EvalScore",
    "EvalRunner",
    "build_scenarios",
    "evaluate_checkpoint",
    "evaluate_stage_checkpoints",
    "evaluate_scenario_stages",
    "list_tasks",
    "load_task",
    "load_patients_for_task",
    "run_all",
    "score_scenario_rules",
]
