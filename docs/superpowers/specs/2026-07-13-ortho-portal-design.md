# 创伤骨科诊疗门户 — 设计文档

> 日期: 2026-07-13
> 目标: 为 xhaip 创伤骨科 (orthopedic-surgery) 新增一个交互式「诊疗功能门户」HTML 页面，
> 以 xhaip 原生模式集成 (FastAPI 直出 vanilla HTML/JS + fetch 真实后端 API)。

---

## 1. 背景与约束

- xhaip 前端为 **vanilla HTML/CSS/JS**，由 `web_server.py` (FastAPI) 直接返回，无 Node/React/Vite。
- 创伤骨科已有资产：
  - Agent YAML: `packages/haip-hospital/agents/definitions/orthopedic-surgery.yaml` (24 工具 / 11 阶段 / 6 角色)
  - 业务模块: `packages/haip-hospital/modules/orthopedics/*`
  - 真实 REST API: `POST /api/v1/orthopedic/{classify|assess|plan|timing|complications|mdt|pain|rehab|followup}`
  - 现有页面: `/ortho` (15-tab 工作台)、`/process/{name}`、`/workflow/{name}`
- 设计令牌来源: `ui_ortho.html` (Apple SF, 深色默认 + 浅色切换, `--accent:#0a84ff`)。

**关键数据约束**
- `his_adapter.MOCK_PATIENT_DB` 原仅 P001/P002 两位患者，且不含结构化 labs/conditions/meds。
- `/timing`、`/complications` 依赖 `labs`(dict) / `conditions`(list) / `meds`(list) 结构化输入。
- 决策: 将 MOCK_PATIENT_DB 扩到 5 位并补齐这些字段，使看板/队列真实可算。

---

## 2. 目标 (Scope)

实现「1 + 3」：
1. **诊疗全流程能力**：8 大 AI 诊疗能力卡，点击调用真实后端 API 并渲染结果。
2. **科室门户 + KPI 看板**：顶部 KPI 卡条 + 患者队列 + 11 阶段诊疗流程时间轴。

**非目标 (YAGNI)**
- 不做 React/构建工具。
- 不改动 A2A/registry/loader 等核心引擎。
- 不实现真实 HIS/PACS 对接 (维持 Mock, 标注 `_mock:true`)。
- 不做用户鉴权/持久化 (演示态)。

---

## 3. 架构 / 文件改动

| 文件 | 改动 | 说明 |
|------|------|------|
| `packages/haip-core/haip/ui_ortho_portal.html` | **新增** | 门户单页，vanilla HTML/JS，内联 CSS (复用 ui_ortho 设计令牌) |
| `packages/haip-core/haip/web_server.py` | **+1 路由** | `@app.get("/ortho-portal")` 按 `/ortho` 同样模式 `open(...).read()` |
| `packages/haip-hospital/modules/orthopedics/his_adapter.py` | **扩充** | `MOCK_PATIENT_DB` 2→5 位，补 `labs`/`conditions`/`meds`；`query_patient` 返回这些字段 |
| `tests/integration/test_ortho_portal.py` | **新增** | 路由 200 + HTML 关键锚点 + 5 患者 + API 冒烟 |

改动集中、对现有页面零破坏。

---

## 4. 页面结构

### 4.1 顶栏 (Header)
- 标题「🦴 创伤骨科 · 诊疗门户」+ 科室副标 (老年髋部骨折精准治疗智能体)
- 右上：主题切换 (深/浅)、「进入完整工作流」按钮 → 跳 `/workflow/orthopedic-surgery`

### 4.2 KPI 看板条 (5 卡)
页面加载时拉取 5 位患者，批量并发调 `/timing` + `/complications` 聚合：
1. 在院髋部骨折数 (= 患者总数)
2. 待手术 (urgency ∈ {emergency, urgent})
3. 48h 手术窗达标率 (emergency 占比)
4. 高危并发症预警数 (overall_risk == high 计数)
5. 平均术前延迟因素数 (total_factors 均值)

### 4.3 AI 诊疗能力卡 (8 张)
对应能力 → API：
| 卡片 | API | 主要入参 |
|------|-----|---------|
| 骨折分型 | `/classify` | patient_id, xray_findings |
| 术前评估 | `/assess` | patient_id |
| MDT 会诊 | `/mdt` | patient_id, 各科 eval |
| T2 手术时机 | `/timing` | patient_id, labs, conditions, meds, ecg_findings |
| 并发症预测 | `/complications` | patient_id, age, labs, conditions |
| 手术方案 | `/plan` | patient_id, fracture_type, age |
| 术后康复 | `/rehab` | patient_id, procedure |
| 随访计划 | `/followup` | patient_id, procedure |

交互：选中患者后点击卡片 → 用该患者数据组织入参 → fetch → 右侧结果面板结构化渲染 (风险徽章 high/medium/low 配色)。

### 4.4 患者队列 (左侧)
- 来源：`POST /api/call` (agent=orthopedic-surgery, tool=his_patient) 逐个拉取 P001..P005，或直接一个轻量 `/api/call` 循环。
- 卡片展示：姓名/年龄/性别/诊断 + urgency 徽章。
- 点击选中 → 高亮 + 驱动能力卡与右侧面板。

### 4.5 诊疗流程时间轴 (11 阶段)
- 静态渲染 YAML `stages` (triage→...→quality)，展示 order/label/desc/role。
- 「进入完整工作流」按钮跳 `/workflow/orthopedic-surgery`。

---

## 5. 数据流

```
浏览器 (ui_ortho_portal.html)
  │  加载: fetch POST /api/call {agent:orthopedic-surgery, tool:his_patient, params:{patient_id}} ×5
  │  聚合: fetch POST /api/v1/orthopedic/timing|complications ×5  → KPI
  │  交互: 点击能力卡 → fetch POST /api/v1/orthopedic/{cap} → 右侧面板渲染
  ▼
web_server.py 路由
  ▼
modules/orthopedics/*  (真实 T2 引擎 / 并发症预测器 / 分型 / 方案)
  ▼
JSON → 前端渲染
```

全部真实后端，无前端 mock 数据。

---

## 6. his_adapter 扩充 (5 患者)

保留 P001/P002，新增 P003/P004/P005。每位补充：
- `labs`: {cTnI, Hb, Cr, Glu, WBC, CRP, INR, egfr} (与 timing/complications 键名兼容, 引擎已支持大小写别名)
- `conditions`: 中文合并症列表 (冠心病/糖尿病/卒中等，驱动 timing/complications 分级)
- `meds`: 用药列表 (warfarin/clopidogrel 等英文键触发抗凝逻辑，展示保留中文名)

覆盖不同 urgency：至少 1 例 emergency (无延迟因素)、1 例 urgent (中危)、1 例 elective (高危心脏)。

---

## 7. 错误处理

- fetch 失败 → 卡片显示「后端未连接 / 稍后重试」，不崩页。
- 患者不存在 → 队列跳过，KPI 基于成功项计算。
- API 返回 error 字段 → 结果面板红色提示。
- 页面在无后端时仍可打开 (骨架 + 占位)，KPI 显示「—」。

---

## 8. 测试策略

`tests/integration/test_ortho_portal.py` (TestClient)：
1. `GET /ortho-portal` → 200 且含关键锚点 (标题 / KPI 容器 id / 能力卡 id / 阶段时间轴)。
2. `his_adapter.MOCK_PATIENT_DB` 含 5 患者且每位有 labs/conditions/meds 非空。
3. `POST /api/v1/orthopedic/timing`、`/complications` 对新患者返回预期 urgency/overall_risk (至少断言 emergency & elective 各一)。
4. 现有 `/ortho`、`/api/v1/orthopedic/*` 回归不受影响。

质量门禁：`ruff check packages/ tests/`；`pytest tests/integration/test_ortho_portal.py -q`。
手动：`python -m uvicorn haip.web_server:app --port 8765` → 访问 `/ortho-portal`。

---

## 9. 验收标准

- [ ] `/ortho-portal` 返回 200，页面呈现 KPI + 8 能力卡 + 患者队列 + 11 阶段时间轴。
- [ ] 选中患者后点击能力卡，右侧面板渲染真实 API 结果。
- [ ] KPI 由真实 API 聚合，非硬编码。
- [ ] 深/浅主题切换正常，视觉与 xhaip 一致。
- [ ] 新增测试通过，`/ortho` 等既有路由回归通过。
- [ ] `ruff check` 通过。
