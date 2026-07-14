"""Clinical Tools — unified entry point for clinical assessment modules.

Provides:
    - NRS-2002 营养风险筛查
    - MUST 营养不良通用筛查
    - MNA-SF 简易营养评估
    - GLIM 营养不良诊断
    - Drug compatibility checker
    - Clinical indicators (lab reference ranges)
"""

from haip.clinical.nutrition import assess as nrs2002_assess, NRS2002Result
from haip.clinical.drug_compat import check_compatibility, check_cation_limits, CompatibilityResult

__all__ = [
    "nrs2002_assess",
    "NRS2002Result",
    "check_compatibility",
    "check_cation_limits",
    "CompatibilityResult",
]
