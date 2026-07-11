"""xhaip 运维模块 — 16 个运维能力。

模块:
  audit_release.py  — AuditEngine / ReleaseManager / ExecutionJournal
  arch_guide.py     — ArchitectureManager / GuidelinesManager / validate_agents / validate_modules
  sync_checks.py    — SkillSync / system_checks / benchmark_a2a / format_output
  skill_sync.py     — skill sync (ownership registry, dry-run, apply, validate, init)
  coord_build.py    — Agent hierarchy / coordinate_agents / AgentMemory / PermissionManager / scaffold_agent
"""

from haip.operations.audit_release import AuditEngine, ReleaseManager, ExecutionJournal  # noqa: F401
from haip.operations.arch_guide import (  # noqa: F401
    ArchitectureManager, GuidelinesManager, validate_agents, validate_modules,
)
from haip.operations.sync_checks import SkillSync, system_checks, benchmark_a2a, format_output  # noqa: F401
from haip.operations.skill_sync import (  # noqa: F401
    SKILL_OWNERSHIP, SKILLS_RUNTIME_DIR, PROJECT_ROOT,
    sync as sync_skills, validate as validate_skills,
    init_from_runtime, list_skills, auto_discover_skills,
)
from haip.operations.coord_build import (  # noqa: F401
    get_agent_tree, get_dependency_graph, coordinate_agents,
    AgentMemory, PermissionManager, scaffold_agent,
)
