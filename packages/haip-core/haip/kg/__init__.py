"""医学知识图谱 — 指南/规则/BP/科室/诊断 实体与关系抽取+查询.

基于 xhaip 现有 YAML 资产自动构建 (100 指南 + 267 规则 + 19 BP + 10659 患者),
参照 TOGAF ABB 元模型 (10 实体/13 关系) + PrimeKG 溯源设计.
"""

from haip.kg.extract import extract_all
from haip.kg.query import by_diagnosis, find_conflicts, stats, trace_evidence
from haip.kg.relations import build_all_relations
from haip.kg.store import KGStore, get_kg_store

__all__ = [
    "KGStore",
    "build_all_relations",
    "by_diagnosis",
    "extract_all",
    "find_conflicts",
    "get_kg_store",
    "stats",
    "trace_evidence",
]
