# xhaip 全量代码检视报告（深度版）

- 日期: 2026-08-03
- 方法: 知识图谱分析 + 3 路并行源码深度审查（引擎核心 / 临床模块 / 脚本部署），关键论断经运行验证
- 图谱: 9380 节点 / 70k+ 边，HEAD 匹配
- 总体风险: **高** — 发现 15 Critical / 33 Important

---

## A. 引擎核心 (packages/haip-core) — 4 Critical / 11 Important

### Critical
- **C1 A2A 权限校验零接线** — `a2a/__init__.py:109` `if perm_ctx is not None:` 全库无调用方传参；`web_server.py:654`/`a2a_call` 均不带；`:126-127` ImportError 时静默放行。任何可达 `/api/call` 的请求可调任意 Agent 任意工具，permission/rbac 形同虚设
- **C2 默认部署 fail-open** — `auth/middleware.py:88-95` 非生产模式无头请求注入 admin 角色 DEV_USER；`auth/jwt.py:20` 开发 JWT 密钥公开已知可伪造任意角色；`web_server.py:136` 默认口令 `Admin@123456`；12 个演示账号统一 `Demo@123456`
- **C3 License 可伪造且零强制** — `licensing/__init__.py:68` 公钥是 sha256 常量而非 RSA；`is_feature_enabled`/`get_limits` 全库无调用方
- **C4 Guard 门控流式路径缺失** — `call_with_loop_async`(:565) guard 结果不阻断；`stream_events`(:580-614) 完全不跑 guard；前端实际使用的 `/api/sse`、`/api/stream` 绕过临床安全门控

### Important（节选）
- **I3 会话 IDOR** — `web_server.py:762/779/787` user_id 取自客户端参数；dev 模式所有匿名用户共享 `session_id="default"` 上下文（患者数据交叉污染）
- **I4 中间件顺序错** — RateLimit→Audit→Auth 执行顺序导致审计 user_id 恒 None、限流退化 IP 维度
- **I7 `/api/config/llm` 无鉴权** — 任意用户可覆盖 DeepSeek API key（患者数据可外泄给攻击者）
- **I9 MDT 超时形同虚设** — `future.result(timeout)` 超时线程仍运行 + shutdown(wait=True) 无限阻塞；零有效意见也算 COMPLETED
- **I11 登出无效** — access token（无 jti）交给 revoke_refresh_token → 什么也不吊销；refresh 不轮换且不查 is_active
- I1 LLM 错误文本当医疗回复返回；I2 DeepSeek 重试风暴无熔断（LLMGateway 无调用方）；I5 A2D 策略 fail-open 字段未执行；I6 患者数据无授权暴露；I8 max_steps 无上限 + SSE 500；I10 meta-harness GET 触发全量重活 + 全局 monkeypatch 竞态

---

## B. 临床模块 (packages/haip-hospital) — 5 Critical / 12 Important

### Critical（均经执行复现）
- **C1 emergency_triage 分诊失真** — `emergency_triage/__init__.py:222` 只查 key 存在不比较数值：任何带 SpO2 的患者全被分诊为 I 级（濒危）
- **C2 分诊括号标准永不命中** — `:25-51` split 整串匹配，"急性心肌梗死(ST段抬高+胸痛+大汗)"等 5 条标准全部失效 → 下分诊漏诊
- **C3 cardio_risk 高血压分级全错** — `cardio_risk/__init__.py:60-87` 分支顺序+守卫错误：145/80 判"正常高值"（应 1 级 ISH）、160/90 判 1 级（应 2 级）
- **C4 肌酐单位错乱** — `drug_agent:151` 把 μmol/L 肌酐当 CrCl（缺失反触发最强干预）；`inf_agent:495-510` mg/dL 阈值判 μmol/L 数据 → **10647 名患者全部假阳性"急性肾损伤"**；`bladder_cancer:168` 同病
- **C5 sepsis_early_warning 数据源错位** — 读 lab_results 的 RR/SBP/GCS，真实数据在 vital_signs 大写键；qSOFA 恒 0；且 agent 仅存 `.deprecated` 定义（孤儿模块）

### Important（节选）
- **I3 13 个规则 YAML 语法错误被静默丢弃** — `rule_engine.py:107-108` `except Exception: continue` 吞异常；nephrology/breast/endocrinology 等 11 科室规则 + guideline_sources/registry.yaml 全部不可解析，科室规则静默归零
- I1 4 处 agent 端口冲突（8841/8820/8840/8843）
- I4 pulmonary_function 混合性通气障碍分支不可达（死代码）
- I5 pacer 血清淀粉酶冒充引流液 + 编造 NSQIP 风险 + `morbitity_risk` 拼写错误
- I6 hypertension_screening 中文病名 key 与 "PA"/"原醛" 匹配永不触发
- I7 vte_management Caprini 分层偏移 1 档（1 分患者被剥夺机械预防）
- I8 pc_aki eGFR 男性系数未用 + 不读患者肌酐
- I9 oncology_cycle 三端输出契约断裂（周期恒显示 D21）
- I11 patients_v2.json 10 名患者全部无 provenance，与 v1 零重叠
- I12 检验 key 大小写漂移（WBC vs wbc、TBil vs bilirubin、hsTnI 全为 0.0 假值）

---

## C. 脚本/部署/配置 — 6 Critical / 10 Important

### Critical
- **C1 Dockerfile:19 构建必失败** — `from haip.agent import load_from_dir` 后 `haip.agent.list_all()` NameError（docker/Dockerfile.agent 已修，根 Dockerfile 未同步）
- **C2 CI validate 必红** — `scripts/validate_agents.py:15` SCHEMA_PATH 指向不存在的 `scripts/agent-schema.json`（实际在 packages/haip-hospital/agents/）
- **C3 CI validate_config 必红** — 6 个 agent 缺 learning.enabled；且 AGENTS.md 新 Agent 流程未提 learning → 官方流程被 CI 阻断
- **C4 默认口令入库 + CI 扫描盲区** — `deploy/k8s/base/secret.yaml` 含 `Admin@123456`/`xhaip-pass`；ci.yml:43 `--disable-plugin KeywordDetector` + grep 模式 `password.*=` 不匹配 YAML 冒号格式
- **C5 xhaip_memory.db (110MB) 已进 git 历史** — `scripts/harness_loop.py:310` 无人值守 `git add -A` 把运行时库推进 master（不可逆，需重写历史）
- **C6 harness_loop 破坏性组合** — `git add -A`+push master 无门禁；yaml.dump 重写销毁 agent YAML 全部注释；候选者无评估直接 accepted

### Important（节选）
- I1 k8s kustomization vs deployment 互相矛盾（ConfigMap 超 1MiB 上限、secretGenerator 与 base/secret 同名冲突）
- I2 migrate_patients 源缺失静默降级 + 非原子覆写 27MB 文件
- I7 branch-protection.ps1 保护不存在的 `main` 分支 + `<<<` PowerShell 语法错误 + 硬编码用户名
- I5 standards 索引大量假 URL（pubmed 裸首页、nhc.gov.cn 首页）
- I6 WHO 下载用 ISBN 拼 IRIS URL 必然 404

---

## D. 正面项

- 80 个 agent YAML 的 432 个 handler 引用全部真实可解析
- 无整模块复制粘贴（相似度 0.06-0.44）；无超长函数（>150 行）
- ruff 全绿、无 TODO/裸 except；validate_patients 数据校验保持绿色
- 上轮 3 项高优测试已补齐（A2A HMAC/singleton/MDT），MDT DEADLOCKED bug 已修复

## E. 优先修复路线图

| 批次 | 内容 | 风险 |
|------|------|------|
| P0-1 | CI 两条必红（C2/C3）、Dockerfile（C1）、xhaip_memory.db 出库（C5/C6 停用自动 push） | 构建/CI 即刻失效 |
| P0-2 | 临床 C1-C5（分诊/分级/肌酐单位/脓毒症数据源） | 直接产生错误临床结论 |
| P0-3 | 引擎 C1-C4（权限接线、默认 fail-open、license、流式 guard） | 全站安全 |
| P1 | I3 规则 YAML 修复 + rule_engine 可见性、中间件顺序、会话 IDOR、端口冲突 | 功能/数据正确性 |
| P2 | 其余 Important/Minor | 质量债 |

---

## �޸����� (2026-08-03)

### P0-1 ? ��� (1719d3e + a7db751, ��� Approved)
- CI validate_agents ת�� (80/80 OK, schema ö�ٶ��� + 6 YAML �� port)
- CI validate_config ת�� (learning �� warning)
- Dockerfile RUN NameError �޸�
- xhaip_memory.db (110MB) �Ƴ� git ����
- harness_loop ֹͣ�Զ� push, git add -A ����ʽ·��
- Minor deferred: harness_loop:315 ret2 δ���; a7db751 commit msg ���ֿ��

### P0-2 �ٴ���ȷ�� �� ������
- P0-2 �ٴ���ȷ�� - complete (4970151 + c59f88f, review Approved)
  - C1-C5 �޸� + inf_agent AKI �� KDIGO ��Ա�׼ (7826->0 ������); 78 ����ͨ��
  - Important ����: inf_agent ��ǩ��������; ���濱���Ѳ�
- P0-3 ���氲ȫ - complete (47faa62 + 40e5eab, review Approved)
  - C1 A2A Ȩ��ǿ�ƽ��� (fail-closed, ImportError->DENY, ������->PERMISSION_REQUIRED)
  - C2 �������¼�� loopback + JWT ���ʵ����Կ (�ɹ������� token ʧЧ)
  - C4 ��ʽ Guard �ſ� (guard_blocked �¼� + �ظ�����, ǰ���Ѽ���)
  - ����: meta_harness �ڲ����� + MCP ��ѡ --token ��Ȩ
  - C3 License α��/��ǿ�� - ����ƾ��� (RSA ��Կ���� + ǿ�Ƶ�)
- P0 ʣ��: C3 License (����ƾ���)
- C3 License - complete (32832dd + be011f7, review Approved)
  - �� RSA RS256 (PyJWT, ��������), ȱʧ��Կ fail-closed, �޺���
  - ǿ��: �����Ž�(�������/�����澯) + max_agents(ע������) + max_users(��¼����)
  - ����: ���� license fail-closed; _json NameError (9bb0463)
- P0 ȫ����ɡ�ʣ�� P1: ���� YAML 13 �ļ����м��˳�򡢻Ự IDOR���˿ڳ�ͻ���¶�ģ��
- P1-A - complete (5a0c9fc/602307e, review Approved)
  - 13 ���� YAML �޸� (���屣ȫ��֤: ���� ID ����ǰ��һ��) + rule_engine �ɼ���
  - �˿ڳ�ͻ���� (4 ���ط���) + 2 �¶� agent ���� (handler ������֤) + 4 ģ�� key Ư���ݴ�
- P1-B - complete (245f870, review Approved)
  - �м��˳������ (���/�����õ� user) + �Ự (user_id, session_id) ���������� (IDOR �ر�)
- ʣ��: P1-6 �ļ���� (web_server 1347L/meta_harness 1265L) - ���ع�������
- Minor ��¼: _pick 4x ���ƴ��鹫������; orthopedics key Ư��; delete_session δ user ������; �����ύ���� test_http 9 ʧ�� (pharmacy ���߸���) + 5 ruff ����
