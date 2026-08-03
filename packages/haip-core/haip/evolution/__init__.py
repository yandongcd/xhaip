"""Agent 进化引擎 — SEAL (Simulacrum-based Evolutionary Agent Learning) 移植.

组件:
  memory_base: 案例库 + 经验库 (SQLite + 向量检索)
  reflect:     失败反思 → 结构化经验
  validate:    验证闸门 (通过率阈值 + 人工审批回滚)
  engine:      进化循环 (评测 → 入库/反思)

与 SEAL 差异 (深挖结论落实):
  - 经验结构化 (trigger/rule/action) 可验证
  - 验证闸门量化 (trials>=3, pass_rate>=0.6) + 审批状态机
  - 复用 xhaip 数字病人 (provenance) 而非 LLM 生成患者
"""

from haip.evolution.engine import evolve_from_eval, run_evolution_cycle
from haip.evolution.memory_base import (
    CaseEntry,
    EvolutionMemory,
    ExperienceEntry,
    get_evolution_memory,
)
from haip.evolution.reflect import reflect_failure
from haip.evolution.validate import (
    approve_experience,
    reject_experience,
    validate_experience,
)

__all__ = [
    "CaseEntry",
    "EvolutionMemory",
    "ExperienceEntry",
    "approve_experience",
    "evolve_from_eval",
    "get_evolution_memory",
    "reflect_failure",
    "reject_experience",
    "run_evolution_cycle",
    "validate_experience",
]
