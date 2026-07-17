# xhaip 商用就绪度评估 — 技术债务与缺失盘点

日期: 2026-07-18
基线: master 20+ commits (UI 契约加固完成后), 测试 1555 passed / 0 failed
定位假设: **私有化部署进医院** (PRD 设定), SaaS 差异单独标注

---

## 第一部分: 技术债务清单

### D1 静默失败文化 — 最高风险
- 证据: 117 个 py 文件中 44 处 `except…pass`、43 处宽泛 `except Exception`; web_server 启动链 (auth seed / TOGAF 校验 / A2A secrets) 全部吞错
- 后果: 2026-07-17 六连 bug 中 4 个 (B1/B4/B5/B6) 的温床 — 组件坏了但系统"看起来正常"
- 治理: 启动链降级 `logger.warning` (部分已做); 业务链禁止裸 pass; ruff 渐进启用 `S110` + `BLE001`

### D2 每次 A2A 调用重建权限引擎 — 性能 + 正确性双债
- 证据: `a2a/__init__.py:110` 每次调用构造 `PermissionManager(":memory:")` + `seed_defaults()`
- 后果: 高频路径无谓开销; **审计日志写入即弃的内存库, 实际全部丢失** — 与 "PROD-READY 权限+审计" 声明矛盾, 医疗场景审计是法定要求
- 治理: 模块级单例 + SQLite/PostgreSQL 落盘 (B4 "组件未接线" 同族第 5 例)

### D3 五套 UI 渲染器并存
- 证据: `ui_workflow / ui_process(+css/js) / ui_render / ui_pharmacy / ui_ortho*.html` — 同一"患者列表+工具执行"范式 5 种实现
- 现状缓解: 契约测试 C1-C7 兜底 + 共享 `haip.patients` 加载器
- 治理: 收敛为一个 YAML 驱动渲染器 (ui.roles/stages 已在 YAML 定义)

### D4 文档与现实漂移
- 证据: AGENTS.md 曾称 50 BP / 314 规则, 实际 BP 19; 根 `knowledge/` (guidelines 13) 与 `haip-hospital/knowledge/` (guidelines 70) 双库并存; togaf 测试断言按旧数据写死 (已修 3 处)
- 治理: 指标类文档生成式化 (脚本统计 + CI drift 校验); 知识库合并单目录

### D5 单体大文件
- 证据: web_server.py 743 行 / cli.py 724 / audit.py 677 / ui_process.py 517
- 治理: web_server 拆 APIRouter (auth / agents / ortho-v1 / pages)

### D6 数据层
- 证据: patients.json 4.5MB 单文件, 每次渲染全量解析; CaseManager 与 haip.patients 双入口
- 治理: 短期 mtime 缓存; 中期迁 SQLite (knowledge store 有先例)

### D7 测试防线余量
- mypy 门禁只覆盖 `haip/`; C2 契约不识别箭头函数; 集成测试自建 ToolDef 绕过 YAML 的模式仍存在 (B6 根源模式)

### 债务演进三阶段
1. **近期 (1-2 周)**: D2 权限单例+审计落盘; ruff S110/BLE001; 文档生成脚本 + CI drift 校验
2. **中期 (1-2 月)**: UI 渲染器统一; web_server 拆分; patients 迁 SQLite; knowledge 双库合一; Guard T2 院内资产入库 + LLM 自纠默认化
3. **远期**: A2A 可插拔 transport (MCP 雏形已有); 会话/审计/指标进 PostgreSQL (k8s manifests 已备); 借鉴 ADK「Agent 即 Node」图执行引擎替代 TaskDAG

---

## 第二部分: 商用缺失盘点

### P0 — 准入门槛 (缺一进不了医院)

| 缺失 | 现状 | 说明 |
|------|------|------|
| 医疗器械边界判定 | 无 | 手术时机/用药建议属 CDSS, 可能触及 NMPA 二/三类; 需法规判定 + 定位收敛为"辅助+医生复核" |
| 等保 2.0 三级 + 算法备案 | 无 | 医院采购硬性要求; 生成式 AI 服务备案/深度合成规定适用 |
| 真实 HIS/EMR/LIS/PACS 对接 | 全 MOCK | HL7 v2 / FHIR 仅雏形; 需与卫宁/东软/东华等厂商完成集成认证 — 医疗 ToB 最大隐性工作量 |
| 生产数据库与审计闭环 | JSON/SQLite/内存 | D2 的商用后果; PostgreSQL 落地 (k8s 已备, 代码未接) |
| 医生签核工作流 | 仅 `requires_human_review` 标志 | 需"复核→CA 签名→留痕"闭环, 责任链才成立 |
| 信创适配 | 未验证 | 麒麟/欧拉 + 达梦/金仓; LLM 已是国产方向, 此条相对占优 |

### P1 — 可交付性

- 离线交付链: licensing 雏形 → 离线安装包 → 升级回滚 → 巡检
- 高可用: 单进程无 LB/HA; Guard LLM 层未默认
- 可观测性: 缺 Prometheus / A2A tracing / 告警; LLM 网关缺熔断降级与 token 成本核算
- 统一身份: 医院 AD/CA/SSO; JWT secret 强制化
- 管理后台 UI: 用户/角色/审计/配额仅有 API
- 文档体系: 缺实施手册/管理员手册/临床 SOP/培训材料

### P2 — 临床可信度

- 临床验证: Guard 置信度阈值无临床数据支撑, 需回顾性评估建立错误率基线
- 红线知识库: 17 条处方规则 → 需对接国家药品目录级药物库
- 指南生命周期治理: `analyze_impact` 雏形 → 运营流程 + 责任人机制
- 模型运营: 临床问答回归基准集 / 上线评测 / 漂移监控
- 不良事件: 上报、根因、召回通路

### P3 — 商业化机制

- 多租户/计费 (tenants 雏形; SaaS 形态下升为 P0)
- 资质: ISO27001 / 软件企业认定 / 案例背书 — 三甲试点是第一张多米诺牌
- SLA 与支持体系

### 关键洞察

1. **雏形密度高、闭环率低**: licensing/tenants/fhir/hl7/permission/k8s/rate_limit 均存在但无一走完闭环 — 商用路径是挑 3-4 个雏形打穿, 不是补新模块
2. **最短商用路径**: 定位"科室级辅助工具 (医生复核制)" 绕开器械证长周期 → 等保 + 审计闭环 + 单一 HIS 厂商对接 + 骨科试点 (资产最厚)
3. 契约测试 + Guard 引文体系是差异化卖点: **可审计的 AI 输出**

---

## 第三部分: P0 攻坚 90 天排期

| 阶段 | 周 | 事项 | 出口标准 |
|------|-----|------|---------|
| **M1 地基** | 1-2 | D2 权限单例 + 审计落 PostgreSQL; JWT/口令强制 env | 审计记录可查可导出; 安全基线自检通过 |
| | 3-4 | patients/会话/审计统一 PostgreSQL; 备份恢复脚本 | 重启不丢数据; RPO≤1h 演练通过 |
| **M2 合规** | 5-6 | 器械边界法规判定 (外部顾问); 产品定位文案收敛"辅助+复核" | 判定意见书; 全部输出带复核提示 |
| | 7-8 | 等保差距评估 + 整改清单启动; 算法备案材料 | 差距报告; 备案提交 |
| **M3 集成** | 9-10 | 医生签核工作流 (复核→签名→留痕) MVP | 高危输出必经签核; 审计可追溯到人 |
| | 11-12 | 选定 1 家 HIS 厂商完成真实对接 (患者/检验只读) | MOCK 适配器可切换真实通道; 端到端演示 |
| **M4 试点** | 13 | 骨科试点科室部署 (离线包 + 巡检脚本) | 内网跑通用户全路径; 试点协议签署 |

> 并行线: 信创适配验证 (麒麟+金仓 smoke) 放 M2-M3 间隙; 文档体系随各里程碑出口物沉淀。

---

*来源: 2026-07-17/18 会话实测 (6 bug 修复 + 契约测试建设 + 硬编码审计 + 全分支审查) 与代码库量化扫描。*
