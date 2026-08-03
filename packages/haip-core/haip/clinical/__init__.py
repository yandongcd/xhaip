"""Clinical Tools — unified entry point for clinical assessment modules.

Provides:
    - NRS-2002 营养风险筛查
    - MUST 营养不良通用筛查
    - MNA-SF 简易营养评估
    - GLIM 营养不良诊断
    - Drug compatibility checker
    - Clinical indicators (lab reference ranges)
"""

from haip.clinical.drug_compat import CompatibilityResult, check_cation_limits, check_compatibility
from haip.clinical.nutrition import NRS2002Result
from haip.clinical.nutrition import assess as nrs2002_assess

__all__ = [
    "CompatibilityResult",
    "NRS2002Result",
    "check_cation_limits",
    "check_compatibility",
    "nrs2002_assess",
]
