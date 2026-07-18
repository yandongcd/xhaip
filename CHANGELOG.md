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

## [Unreleased] — v1.2.x

### Features
- **第一轮 R 消减**: 新增 5 agent (spine-surgery, joint-surgery, lab-critical-value, nurse-general, dietitian, 3656 行), RBAC 6→11, /home 分流
- **Auth SQLite 持久化**: AuthService 双后端 (memory/sqlite), HAIP_AUTH_DB 落盘, close()/reset_auth_service(), 用户/角色/激活状态跨实例持久
- **seed_demo_identities()**: 12 门户身份幂等种子账户 (HAIP_ENV=production 需 HAIP_SEED_DEMO_USERS 显式开启)
- **生产安全 Profile**: HAIP_ENV=production → CORS 收敛/rate_limit 默认开/demo 种子门控/安全基线严格模式
- **D6 患者数据缓存**: load_patients() 增加 mtime+size 失效的线程安全缓存 (threading.Lock), clear_cache() 供测试
- **备份脚本**: scripts/backup_db.py — 收集 xhaip.db + data/*.db + patients.json → releases/backups/<UTC>/manifest.json, --retain/--list/--dry-run

### Quality
- **D1 定点治理**: a2a/auth/web_server 裸吞异常清零 + tests/test_no_silent_except.py 门禁
- **D4 文档漂移门禁**: tests/test_doc_drift.py 校验 AGENTS.md 中 YAML Agent 数 / BP 指南规则组数 / 病人数与源码实数一致 (CI 阻断)
- **存量 ruff 清零**: 修复旧文件 lint 违规 (F841/F541/E741/E401/F811) 并清除 F841 机械修复遗留的 71 行死表达式 (16 文件)
- **仓库卫生**: 31 个被跟踪 .pyc 出库, .gitignore 补 data/*.db

### Changed
- AGENTS.md 数字更新: 48→58 YAML, 50/36/38 BP/指南/规则组→19/70/21, 384→498 病人
- CI ruff 检查范围扩大至全仓 (`ruff check .`)

### Debt (遗留)
- 模块 Directory→Package 标准化 (haip-hospital/modules/)
- Agent YAML schema 版本化 + 校验门禁
- 批次 C 评分器 (TBSA/Parkland/PHQ-9/GAD-7/Barthel/ward_rounds) 顺延至近期第二批 (R11/R12)
