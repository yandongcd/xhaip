# Task Plan: 落账批次 — 未提交成果补齐+修剪+分批提交

## Goal
将工作区 ~120 个未提交文件落账: 补齐半成品 (auth 持久化/patients 缓存), 修 D1 残留,
剔除未实现依赖的测试, 清死代码, 全量绿后分批提交。

## Phases

### Phase 1: patients 缓存 (D6 短期)
- [ ] haip/patients.py: mtime+size 失效缓存 + threading.Lock + clear_cache()
- [ ] test_patients_cache.py 6 用例绿

### Phase 2: auth SQLite 持久化 (D2 同族)
- [ ] AuthService(backend=, db_path=) — memory/sqlite 双后端
- [ ] close() / reset_auth_service()
- [ ] seed_demo_identities() 幂等 12 身份 (HAIP_ENV=production 无 flag 时 0)
- [ ] HAIP_TEST_MODE=true 默认 :memory:
- [ ] test_auth_persistence.py 9 + test_role_home seed 1 + test_production_profile 2 绿

### Phase 3: D1 残留
- [ ] auth/__init__.py:265,295 except Exception: pass → 窄化/加日志
- [ ] web_server.py:116-120 seed try/except 简化 (合入后不再需要 AttributeError 兜底)
- [ ] test_no_silent_except 绿

### Phase 4: 修剪
- [ ] 删 tests/test_scorers_rounds.py (批次 C 功能未实现, 顺延)
- [ ] cardiology 等死代码清理 (裸 [] / 裸 f-string)
- [ ] CHANGELOG mojibake 修复

### Phase 5: 仓库卫生
- [ ] git rm --cached **/*.pyc; .gitignore 补 __pycache__/ data/*.db
- [ ] data/auth.db 等不入库

### Phase 6: 验证
- [ ] pytest packages/haip-core/tests tests -q 全绿
- [ ] ruff check . = 0; mypy haip/ = 0
- [ ] python scripts/validate_patients.py 0 FAIL

### Phase 7: 分批提交
- [ ] c1 chore: 仓库卫生 (.pyc/.gitignore/db)
- [ ] c2 feat: R 第一轮 5 agent + RBAC 11 + /home 分流 (含测试)
- [ ] c3 feat: auth SQLite 持久化 + patients 缓存 + 生产 Profile + 备份脚本
- [ ] c4 fix: D1 静默异常治理 + 门禁测试
- [ ] c5 chore: ruff 全仓清零 + 死代码清理 + CI 扩域
- [ ] c6 docs: 台账/CHANGELOG/AGENTS/报告
