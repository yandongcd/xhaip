# Changelog

All notable changes to xhaip (HAIP v1.0).

## [1.0.0] — 2026-07-10

### Features
- **xhaip v1.0**: 48 agents, 39 departments, TOGAF 10 governance, KnowledgeAgent reasoning, 384 patients (ecddb7e)
- **Phase 2 surgical rules**: 9 departments x 3 rule types, 33/33 ABB passed (edd00c7)
- **Phase 3-5 clinical rules**: 38 departments, 111 rule groups, 314 rules, 111/111 ABB passed (0b8ae10)
- **31 handlers upgraded to RuleEngine** + 216 patients with specialty fields (4a3c939)
- **Clinical RuleEngine**: YAML-driven diagnosis/risk/treatment rules for 3 departments (40598fb)

### Fixes
- **Config files + .dockerignore + healthcheck consistency** (b3b6223)
- **TOGAF ABB traceability**: data_entities catalog, shared surgical rules, ABB validation engine (314b9d4)
- **Process page JS resolution** (f-string to format) + HTML test suite, 10 endpoints (16c1cf9)
- **TOGAF governance 82%→100%**: entity set expanded, step names accepted (ced1757)
- **TOGAF governance 62%→82%**: BP placeholders eliminated, guidelines reporting fixed (001f46b)
- **EA templates wired to builder data**: no more placeholder HTML (493fc57)
- **TOGAF principles enforcement** (CHK-006) + BP placeholder replacement (d7a7009)
- **TOGAF core**: governance BP loading, builder multi-dept, agent registration gate (8ca4540)

### Refactor
- **Delete dead code** (348 lines) + README accuracy + HTML tests → TestClient, 47 tests (dfb6597)

### Test
- **TOGAF test suite**: 25 tests covering 7 modules, was 0 tests (f8c16ea)

### Chore
- **Cleanup**: .gitignore, remove `__pycache__`, remove duplicate Chinese module dirs (0c5e80a)
