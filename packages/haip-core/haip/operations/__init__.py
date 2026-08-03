"""xhaip 运维模块 — 16 个运维能力。

模块:
  audit_release.py  — AuditEngine / ReleaseManager / ExecutionJournal
  arch_guide.py     — ArchitectureManager / GuidelinesManager / validate_agents / validate_modules
  sync_checks.py    — SkillSync / system_checks / benchmark_a2a / format_output
  skill_sync.py     — skill sync (ownership registry, dry-run, apply, validate, init)
  coord_build.py    — Agent hierarchy / coordinate_agents / AgentMemory / PermissionManager / scaffold_agent
"""

from haip.operations.arch_guide import (  # noqa: F401
    ArchitectureManager,
    GuidelinesManager,
    validate_agents,
    validate_modules,
)
from haip.operations.audit_release import (  # noqa: F401
    AuditEngine,
    ExecutionJournal,
    ReleaseManager,
)
from haip.operations.coord_build import (  # noqa: F401
    AgentMemory,
    PermissionManager,
    coordinate_agents,
    get_agent_tree,
    get_dependency_graph,
    scaffold_agent,
)
from haip.operations.skill_sync import (  # noqa: F401
    PROJECT_ROOT,
    SKILL_OWNERSHIP,
    SKILLS_RUNTIME_DIR,
    auto_discover_skills,
    init_from_runtime,
    list_skills,
)
from haip.operations.skill_sync import (  # noqa: F401
    sync as sync_skills,
)
from haip.operations.skill_sync import (  # noqa: F401
    validate as validate_skills,
)
from haip.operations.sync_checks import (  # noqa: F401
    SkillSync,
    benchmark_a2a,
    format_output,
    system_checks,
)
