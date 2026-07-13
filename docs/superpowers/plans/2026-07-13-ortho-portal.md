# 创伤骨科诊疗门户 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 xhaip 创伤骨科新增一个交互式「诊疗功能门户」页面 `/ortho-portal`，以 xhaip 原生模式 (FastAPI 直出 vanilla HTML/JS + fetch 真实后端 API) 呈现 KPI 看板 + 8 AI 诊疗能力卡 + 患者队列 + 11 阶段诊疗流程时间轴。

**Architecture:** 后端先把 `his_adapter.MOCK_PATIENT_DB` 由 2 位扩到 5 位并补齐 `labs/conditions/meds` 结构化字段；再在 `web_server.py` 增加一条 `/ortho-portal` 路由 (与 `/ortho` 完全相同的文件读取模式)；前端为单个自包含 HTML 文件，通过 `POST /api/call` (his_patient) 拉取患者、通过 `POST /api/v1/orthopedic/*` 调用诊疗能力与聚合 KPI。全程真实后端，无前端 mock。

**Tech Stack:** Python 3.10+ / FastAPI / uvicorn；前端 vanilla HTML + CSS (内联) + 原生 JS fetch；测试用 `fastapi.testclient.TestClient` + pytest；lint 用 ruff。

## Global Constraints

- Windows PowerShell 5.1：命令链用 `;` + `if ($?) { }`，不用 `&&`；不用 `-LiteralPath`。
- 前端设计令牌复用 `ui_ortho.html`：深色默认 `--bg:#1c1c1e` / `--card-bg:#2c2c2e` / `--accent:#0a84ff`；浅色 `body.light` 覆盖；字体 `-apple-system,'PingFang SC','Microsoft YaHei'`。
- 前端调用契约：
  - `POST /api/call` body `{agent, tool, params}` → 返回工具原始 JSON。
  - `POST /api/v1/orthopedic/{classify|assess|plan|timing|complications|mdt|pain|rehab|followup}` body 为该工具入参 dict，直接返回模块函数结果。
- `/timing`、`/complications` 的 `labs` 键名引擎兼容大小写别名 (troponin/cTnI、hb/Hb、egfr/eGFR、creatinine/Cr、glucose/Glu、wbc/WBC、crp/CRP、inr)。抗凝逻辑匹配英文小写 med 关键字 (`warfarin`/`clopidogrel`/`rivaroxaban`/`apixaban`/`ticagrelor`)。
- 中文与英文/数字间加空格。
- 不新增第三方依赖；不改动 A2A / registry / loader / agent YAML。
- 测试路径约定：`sys.path` 依次插入 `packages/haip-core`、`packages/haip-hospital`、`packages/haip-hospital/modules`（参照 `tests/test_html_pages.py` 与 `tests/integration/test_orthopedic.py`）。
- 每完成一个 Task 结束时提交一次 git commit。

---

## 文件结构

| 文件 | 责任 | 改动 |
|------|------|------|
| `packages/haip-hospital/modules/orthopedics/his_adapter.py` | Mock HIS/LIS/PACS；患者主数据 | 扩 `MOCK_PATIENT_DB` 到 5 位 + 补字段；`query_patient` 透传 labs/conditions/meds |
| `packages/haip-core/haip/web_server.py` | FastAPI 路由 | +1 路由 `/ortho-portal` |
| `packages/haip-core/haip/ui_ortho_portal.html` | 门户单页 (HTML/CSS/JS) | 新增 |
| `tests/integration/test_ortho_portal.py` | 集成测试 | 新增 |

---

## Task 1: 扩充 his_adapter 患者主数据到 5 位

**Files:**
- Modify: `packages/haip-hospital/modules/orthopedics/his_adapter.py:25-36` (MOCK_PATIENT_DB) 及 `:81-100` (query_patient)
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: 无 (基础数据层)
- Produces:
  - `MOCK_PATIENT_DB: dict[str, dict]` — 键 `P001..P005`，每位含 `name, age, gender, diagnosis, comorbidities, medications, allergies, labs(dict), conditions(list[str]), meds(list[str]), fracture_type(str), procedure(str)`。
  - `query_patient(*, patient_id: str, **kwargs) -> dict` — 返回上述全部字段 + `patient_id, source:"HIS", _mock:True`。
- 患者风险分布 (供 KPI 断言)：P001=urgent(中危)、P002=emergency(无因素)、P003=elective(高危心脏)、P004=emergency、P005=urgent。

- [ ] **Step 1: 新建测试文件并写患者数据的失败测试**

Create `tests/integration/test_ortho_portal.py`:

```python
"""创伤骨科诊疗门户 (/ortho-portal) 集成测试."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital" / "modules"))

from fastapi.testclient import TestClient  # noqa: E402
from haip.agent import load_from_dir  # noqa: E402

load_from_dir(str(ROOT / "packages" / "haip-hospital" / "agents" / "definitions"))
from haip.web_server import app  # noqa: E402

client = TestClient(app)

REQUIRED_PATIENTS = ["P001", "P002", "P003", "P004", "P005"]


class TestPatientData:
    def test_five_patients_exist(self):
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        for pid in REQUIRED_PATIENTS:
            assert pid in MOCK_PATIENT_DB, f"缺少患者 {pid}"

    def test_each_patient_has_structured_fields(self):
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        for pid in REQUIRED_PATIENTS:
            p = MOCK_PATIENT_DB[pid]
            assert p.get("labs"), f"{pid} 缺 labs"
            assert isinstance(p["labs"], dict) and len(p["labs"]) >= 5
            assert isinstance(p.get("conditions"), list)
            assert isinstance(p.get("meds"), list)
            assert p.get("fracture_type"), f"{pid} 缺 fracture_type"

    def test_query_patient_passes_structured_fields(self):
        from orthopedics.his_adapter import query_patient
        r = query_patient(patient_id="P003")
        assert r["patient_id"] == "P003"
        assert "labs" in r and "conditions" in r and "meds" in r
        assert r["_mock"] is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPatientData -q`
Expected: FAIL（P003 缺失 / labs 键不存在）。

- [ ] **Step 3: 替换 MOCK_PATIENT_DB 为 5 位并补齐字段**

将 `his_adapter.py` 中 `MOCK_PATIENT_DB = { ... P001, P002 ... }` 整块替换为：

```python
MOCK_PATIENT_DB = {
    "P001": {
        "name": "张**", "age": 78, "gender": "女",
        "diagnosis": "右股骨颈骨折 Garden III",
        "comorbidities": ["高血压", "2型糖尿病"],
        "medications": ["硝苯地平 30mg qd", "二甲双胍 500mg bid"],
        "allergies": ["青霉素"],
        "labs": {"cTnI": 0.02, "Hb": 95, "Cr": 110, "Glu": 9.5,
                 "WBC": 8.5, "CRP": 40, "INR": 1.1, "egfr": 65},
        "conditions": ["高血压", "糖尿病"],
        "meds": ["nifedipine", "metformin"],
        "fracture_type": "股骨颈骨折", "procedure": "THA (全髋关节置换)",
    },
    "P002": {
        "name": "李**", "age": 82, "gender": "男",
        "diagnosis": "左股骨转子间骨折 Evans ID",
        "comorbidities": ["房颤", "高血压"],
        "medications": ["华法林 3mg qd", "氨氯地平 5mg qd"],
        "allergies": [],
        "labs": {"cTnI": 0.01, "Hb": 138, "Cr": 90, "Glu": 5.4,
                 "WBC": 6.5, "CRP": 6, "INR": 1.1, "egfr": 82},
        "conditions": ["高血压"],
        "meds": ["amlodipine"],
        "fracture_type": "转子间骨折", "procedure": "PFNA (股骨近端防旋髓内钉)",
    },
    "P003": {
        "name": "王**", "age": 80, "gender": "男",
        "diagnosis": "右股骨颈骨折 Garden IV",
        "comorbidities": ["冠心病", "陈旧心梗", "高血压"],
        "medications": ["阿司匹林 100mg qd", "美托洛尔 25mg bid"],
        "allergies": [],
        "labs": {"cTnI": 0.08, "Hb": 105, "Cr": 120, "Glu": 6.8,
                 "WBC": 9.0, "CRP": 30, "INR": 1.2, "egfr": 55},
        "conditions": ["冠心病", "心梗史", "高血压"],
        "meds": ["aspirin", "metoprolol"],
        "fracture_type": "股骨颈骨折", "procedure": "THA (全髋关节置换)",
    },
    "P004": {
        "name": "赵**", "age": 68, "gender": "女",
        "diagnosis": "左股骨转子间骨折 Evans IIA",
        "comorbidities": ["骨质疏松"],
        "medications": ["阿仑膦酸钠 70mg qw"],
        "allergies": [],
        "labs": {"cTnI": 0.01, "Hb": 128, "Cr": 78, "Glu": 5.1,
                 "WBC": 7.0, "CRP": 8, "INR": 1.0, "egfr": 90},
        "conditions": ["骨质疏松"],
        "meds": ["alendronate"],
        "fracture_type": "转子间骨折", "procedure": "PFNA (股骨近端防旋髓内钉)",
    },
    "P005": {
        "name": "陈**", "age": 85, "gender": "女",
        "diagnosis": "右股骨颈骨折 Garden III 合并贫血",
        "comorbidities": ["慢性肾病", "贫血", "痴呆"],
        "medications": ["氯吡格雷 75mg qd"],
        "allergies": ["磺胺"],
        "labs": {"cTnI": 0.03, "Hb": 88, "Cr": 150, "Glu": 6.2,
                 "WBC": 8.0, "CRP": 50, "INR": 1.3, "egfr": 45},
        "conditions": ["慢性肾病", "贫血", "痴呆", "冠心病"],
        "meds": ["clopidogrel"],
        "fracture_type": "股骨颈骨折", "procedure": "THA (全髋关节置换)",
    },
}
```

（说明：P002 无高危、无 warfarin-with-INR>1.5 触发 → emergency；P004 无因素 → emergency；P001 hb<100+无心脏病 不触发、glucose 9.5 不触发、egfr 65 不触发…实际 P001 无中危因素亦为 emergency——见 Step 6 修正。）

- [ ] **Step 4: `query_patient` 透传新字段（已自动透传，确认无需改动）**

`query_patient` 现有实现 `return {**patient, "patient_id": ..., "source": "HIS", "_mock": True, ...}` 已经透传 `**patient` 全部字段，无需改代码。仅确认返回含 `labs/conditions/meds`。

- [ ] **Step 5: 运行测试确认数据结构通过**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPatientData -q`
Expected: PASS（3 项）。

- [ ] **Step 6: 补充 urgency 分布断言并校准数据**

在 `test_ortho_portal.py` 追加：

```python
class TestUrgencyDistribution:
    """校验患者数据能覆盖不同手术时机分级 (真实引擎计算)."""

    def _timing(self, pid):
        from orthopedics import evaluate_timing
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        p = MOCK_PATIENT_DB[pid]
        return evaluate_timing(patient_id=pid, labs=p["labs"],
                               conditions=p["conditions"], meds=p["meds"],
                               ecg_findings="")["urgency"]

    def test_has_elective_high_risk(self):
        assert self._timing("P003") == "elective"  # cTnI 0.08 > 0.04

    def test_has_emergency_case(self):
        urgencies = {self._timing(p) for p in REQUIRED_PATIENTS}
        assert "emergency" in urgencies

    def test_complications_high_risk_exists(self):
        from orthopedics import predict_complications
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        overalls = []
        for pid in REQUIRED_PATIENTS:
            p = MOCK_PATIENT_DB[pid]
            r = predict_complications(patient_id=pid, age=p["age"],
                                      labs=p["labs"], conditions=p["conditions"])
            overalls.append(r["overall_risk"])
        assert "high" in overalls  # P005 高龄+痴呆+CKD
```

Run: `python -m pytest tests/integration/test_ortho_portal.py -q`
Expected: PASS。若某断言失败，微调对应患者 labs/conditions（如 P003 cTnI 提到 0.08 已 >0.04 触发 elective；P005 age 85 + 痴呆 → fall high）。

- [ ] **Step 7: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-hospital/modules/orthopedics/his_adapter.py tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 扩充 his_adapter 患者到 5 位并补齐 labs/conditions/meds"
```

---

## Task 2: 新增 /ortho-portal 路由

**Files:**
- Modify: `packages/haip-core/haip/web_server.py` (在 `/ortho` 路由 `:580-584` 之后插入)
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: `Path`, `HTMLResponse`（文件顶部已 import；`/ortho` 路由已使用同款）。
- Produces: `GET /ortho-portal` → 200 text/html，读取 `ui_ortho_portal.html`。

- [ ] **Step 1: 写路由 200 的失败测试**

在 `test_ortho_portal.py` 追加：

```python
class TestPortalRoute:
    def test_route_returns_200(self):
        r = client.get("/ortho-portal")
        assert r.status_code == 200

    def test_route_is_html(self):
        r = client.get("/ortho-portal")
        body = r.text.lower()
        for tag in ["<!doctype", "<html", "<head", "<body", "<title"]:
            assert tag in body, f"缺 {tag}"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalRoute -q`
Expected: FAIL（404，路由未定义 / 文件不存在）。

- [ ] **Step 3: 添加路由**

在 `web_server.py` `ortho_ui()` 函数之后（`/pharmacy` 之前）插入：

```python
@app.get("/ortho-portal", response_class=HTMLResponse)
def ortho_portal_ui():
    """创伤骨科诊疗门户 — KPI 看板 + AI 诊疗能力卡 + 患者队列 + 流程时间轴。"""
    with open(Path(__file__).parent / "ui_ortho_portal.html", encoding="utf-8") as f:
        return f.read()
```

- [ ] **Step 4: 建占位 HTML 使路由可返回**

Create `packages/haip-core/haip/ui_ortho_portal.html`（最小骨架，Task 3 填充）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xhaip — 创伤骨科诊疗门户</title>
</head>
<body>
<div id="app">创伤骨科诊疗门户 加载中…</div>
</body>
</html>
```

- [ ] **Step 5: 运行确认通过**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalRoute -q`
Expected: PASS（2 项）。

- [ ] **Step 6: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-core/haip/web_server.py packages/haip-core/haip/ui_ortho_portal.html tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 新增 /ortho-portal 路由 + HTML 骨架"
```

---

## Task 3: 构建门户 HTML — 布局与设计令牌

**Files:**
- Modify: `packages/haip-core/haip/ui_ortho_portal.html` (整体填充)
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: `/ortho-portal` 路由 (Task 2)。
- Produces: HTML 含以下稳定锚点 id/class，供测试与后续 JS 使用：
  - `#kpi-bar`（KPI 容器）、`#patient-list`（患者队列）、`#capability-grid`（能力卡网格）、`#result-panel`（右侧结果面板）、`#stage-timeline`（11 阶段时间轴）、`#theme-toggle`（主题切换按钮）。

- [ ] **Step 1: 写布局锚点存在性的失败测试**

在 `test_ortho_portal.py` 追加：

```python
class TestPortalLayout:
    def _body(self):
        return client.get("/ortho-portal").text

    def test_has_layout_anchors(self):
        body = self._body()
        for anchor in ["kpi-bar", "patient-list", "capability-grid",
                       "result-panel", "stage-timeline", "theme-toggle"]:
            assert anchor in body, f"缺锚点 {anchor}"

    def test_has_title_and_tokens(self):
        body = self._body()
        assert "创伤骨科" in body
        assert "--accent" in body  # 复用 ui_ortho 设计令牌
        assert "body.light" in body  # 浅色模式
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalLayout -q`
Expected: FAIL（骨架无这些锚点）。

- [ ] **Step 3: 写完整 HTML 布局（含 CSS 令牌 + 静态结构）**

将 `ui_ortho_portal.html` 全文替换为下述内容（CSS 复用 ui_ortho 令牌；JS 逻辑在 Task 4/5 填充，本步先放静态骨架与空 `<script>` 占位）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xhaip — 创伤骨科诊疗门户</title>
<style>
:root{--bg:#1c1c1e;--card-bg:#2c2c2e;--text:#f5f5f7;--text-secondary:#a1a1a6;--accent:#0a84ff;--danger:#ff453a;--warning:#ff9f0a;--success:#30d158;--border:#38383a;--bg-gradient:radial-gradient(ellipse at 50% 0%,var(--card-bg) 0%,var(--bg) 60%)}
body.light{--bg:#f2f2f7;--card-bg:#ffffff;--text:#1c1c1e;--text-secondary:#6e6e73;--accent:#007aff;--danger:#ff3b30;--warning:#ff9500;--success:#34c759;--border:#e5e5ea;--bg-gradient:radial-gradient(ellipse at 50% 0%,#ffffff 0%,#f2f2f7 60%)}
*{margin:0;padding:0;box-sizing:border-box}
::selection{background:var(--accent);color:#fff}
body{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','PingFang SC','Microsoft YaHei',sans-serif;-webkit-font-smoothing:antialiased;background:var(--bg-gradient);color:var(--text);height:100vh;overflow:hidden;display:flex;flex-direction:column;letter-spacing:-.01em}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.header{height:52px;flex-shrink:0;padding:0 20px;background:var(--card-bg);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px)}
.header h1{font-size:16px;font-weight:600}
.header .sub{font-size:11px;color:var(--text-secondary)}
.header .spacer{margin-left:auto}
.btn{padding:6px 14px;border:1px solid var(--border);border-radius:8px;font-size:12px;cursor:pointer;background:transparent;color:var(--text);font-family:inherit;transition:all .12s}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn-primary{background:var(--accent);color:#fff;border-color:var(--accent)}
#kpi-bar{flex-shrink:0;display:grid;grid-template-columns:repeat(5,1fr);gap:12px;padding:14px 20px}
.kpi{background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:12px 16px}
.kpi .val{font-size:24px;font-weight:700}
.kpi .label{font-size:11px;color:var(--text-secondary);margin-top:2px}
.body-grid{flex:1;display:flex;overflow:hidden}
#patient-list{width:240px;flex-shrink:0;background:var(--card-bg);border-right:1px solid var(--border);overflow-y:auto;padding:8px}
.p-card{padding:10px 12px;border-radius:10px;cursor:pointer;transition:all .12s;border:1px solid transparent}
.p-card:hover{background:var(--bg)}
.p-card.active{background:rgba(10,132,255,.12);border-color:var(--accent)}
.p-card .p-name{font-size:13px;font-weight:600}
.p-card .p-meta{font-size:11px;color:var(--text-secondary);margin-top:2px}
.center{flex:1;overflow-y:auto;padding:16px 20px}
#capability-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.cap{background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:14px;cursor:pointer;transition:all .15s}
.cap:hover{border-color:var(--accent);transform:translateY(-2px)}
.cap .cap-ico{font-size:20px}
.cap .cap-title{font-size:13px;font-weight:600;margin-top:6px}
.cap .cap-desc{font-size:11px;color:var(--text-secondary);margin-top:3px}
#stage-timeline{margin-top:20px;background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:14px}
#stage-timeline h3{font-size:13px;color:var(--accent);margin-bottom:10px}
.stage-row{display:flex;gap:10px;align-items:flex-start;padding:6px 0;font-size:12px}
.stage-row .num{width:20px;height:20px;border-radius:50%;background:var(--accent);color:#fff;font-size:11px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.stage-row .st-desc{color:var(--text-secondary);font-size:11px}
#result-panel{width:360px;flex-shrink:0;background:var(--card-bg);border-left:1px solid var(--border);overflow-y:auto;padding:16px}
#result-panel h3{font-size:13px;color:var(--accent);margin-bottom:10px}
.result-box{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:12px;font-family:'SF Mono',Consolas,monospace;font-size:11px;line-height:1.5;white-space:pre-wrap;word-break:break-word}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
.badge.high{background:rgba(255,69,58,.15);color:var(--danger)}
.badge.moderate,.badge.medium,.badge.urgent{background:rgba(255,159,10,.15);color:var(--warning)}
.badge.low,.badge.emergency{background:rgba(48,209,88,.15);color:var(--success)}
.muted{color:var(--text-secondary);font-size:12px}
</style>
</head>
<body>
<div class="header">
  <h1>🦴 创伤骨科 · 诊疗门户</h1>
  <span class="sub">老年髋部骨折精准治疗智能体</span>
  <div class="spacer"></div>
  <button class="btn" id="theme-toggle">☀ 浅色</button>
  <button class="btn btn-primary" onclick="location.href='/workflow/orthopedic-surgery'">进入完整工作流 →</button>
</div>

<div id="kpi-bar"><div class="kpi"><div class="val" id="kpi-total">—</div><div class="label">在院髋部骨折</div></div>
<div class="kpi"><div class="val" id="kpi-pending">—</div><div class="label">待手术</div></div>
<div class="kpi"><div class="val" id="kpi-48h">—</div><div class="label">48h 手术窗达标率</div></div>
<div class="kpi"><div class="val" id="kpi-highrisk">—</div><div class="label">高危并发症预警</div></div>
<div class="kpi"><div class="val" id="kpi-avgfactor">—</div><div class="label">平均延迟因素数</div></div></div>

<div class="body-grid">
  <div id="patient-list"><div class="muted" style="padding:8px">加载患者…</div></div>
  <div class="center">
    <div id="capability-grid"></div>
    <div id="stage-timeline"><h3>诊疗全流程 · 11 阶段</h3><div id="stage-rows"></div></div>
  </div>
  <div id="result-panel"><h3>结果面板</h3><div class="muted" id="result-empty">← 选择患者后点击上方能力卡查看 AI 诊疗结果</div><div id="result-content"></div></div>
</div>

<script>
/* Task 4/5 填充 JS */
</script>
</body>
</html>
```

- [ ] **Step 4: 运行确认布局测试通过**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalLayout -q`
Expected: PASS（2 项）。

- [ ] **Step 5: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-core/haip/ui_ortho_portal.html tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 门户 HTML 布局 + 设计令牌"
```

---

## Task 4: 门户 JS — 患者队列 + 能力卡 + 阶段时间轴渲染

**Files:**
- Modify: `packages/haip-core/haip/ui_ortho_portal.html` (`<script>` 段)
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: 布局锚点 (Task 3)；`POST /api/call` (his_patient) 拉患者。
- Produces: 前端全局对象/常量（供 Task 5 使用）：
  - `const PATIENT_IDS = ["P001","P002","P003","P004","P005"]`
  - `const CAPS = [...]`（8 项，字段 `{id,ico,title,desc,api}`，api ∈ classify/assess/mdt/timing/complications/plan/rehab/followup）
  - `const STAGES = [...]`（11 项 `{order,label,desc}`，与 YAML 对应）
  - `let selectedPid = null`
  - `function renderPatients(list)` / `function renderCaps()` / `function renderStages()` / `async function loadPatients()`

- [ ] **Step 1: 写「能力卡与阶段静态内容」测试**

在 `test_ortho_portal.py` 追加：

```python
class TestPortalContent:
    def _body(self):
        return client.get("/ortho-portal").text

    def test_has_eight_capabilities(self):
        body = self._body()
        for api in ["classify", "assess", "mdt", "timing",
                    "complications", "plan", "rehab", "followup"]:
            assert api in body, f"缺能力 API {api}"

    def test_has_eleven_stages_labels(self):
        body = self._body()
        for label in ["急诊分诊", "骨折分型", "术前评估", "MDT 会诊",
                      "手术时机", "并发症预测", "手术方案", "围术期护理",
                      "术后康复", "随访计划", "质控审计"]:
            assert label in body, f"缺阶段 {label}"

    def test_has_patient_ids_and_loader(self):
        body = self._body()
        assert "P001" in body and "P005" in body
        assert "/api/call" in body
        assert "his_patient" in body
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalContent -q`
Expected: FAIL（script 为空）。

- [ ] **Step 3: 填充 JS（常量 + 渲染 + 患者加载）**

将 `ui_ortho_portal.html` 中 `<script>/* Task 4/5 填充 JS */</script>` 替换为：

```html
<script>
const PATIENT_IDS = ["P001","P002","P003","P004","P005"];
const CAPS = [
  {id:"classify", ico:"🦴", title:"骨折分型", desc:"Garden/Evans/AO", api:"classify"},
  {id:"assess", ico:"📋", title:"术前评估", desc:"合并症/药物/营养", api:"assess"},
  {id:"mdt", ico:"🔄", title:"MDT 会诊", desc:"多学科聚合纪要", api:"mdt"},
  {id:"timing", ico:"⏱️", title:"T2 手术时机", desc:"8 因素分级决策", api:"timing"},
  {id:"complications", ico:"🩺", title:"并发症预测", desc:"DVT/感染/心脏/跌倒", api:"complications"},
  {id:"plan", ico:"🔪", title:"手术方案", desc:"THA/HA/PFNA/DHS", api:"plan"},
  {id:"rehab", ico:"🏃", title:"术后康复", desc:"4 阶段 + Harris", api:"rehab"},
  {id:"followup", ico:"📅", title:"随访计划", desc:"1/3/6/12 月", api:"followup"},
];
const STAGES = [
  {order:1, label:"急诊分诊", desc:"11 项检查清单, 绿色通道判定"},
  {order:2, label:"骨折分型", desc:"Garden/Evans/AO 分型评估"},
  {order:3, label:"术前评估", desc:"合并症/药物/营养/认知 + 14 项完备性"},
  {order:4, label:"MDT 会诊", desc:"聚合心内+麻醉+骨科+疼痛 → 纪要"},
  {order:5, label:"手术时机", desc:"T2 8 因素层次决策"},
  {order:6, label:"并发症预测", desc:"DVT/感染/心脏/跌倒-谵妄 4 维"},
  {order:7, label:"手术方案", desc:"THA/HA/PFNA/DHS 推荐"},
  {order:8, label:"围术期护理", desc:"4 阶段 25 项护理计划"},
  {order:9, label:"术后康复", desc:"4 阶段康复 + Harris 评分"},
  {order:10, label:"随访计划", desc:"1/3/6/12 月 + 红旗症状 + 骨质疏松"},
  {order:11, label:"质控审计", desc:"6 阶段 18 检查点合规评分"},
];
let selectedPid = null;
let patients = {};

function renderStages(){
  document.getElementById("stage-rows").innerHTML = STAGES.map(s =>
    `<div class="stage-row"><div class="num">${s.order}</div><div><div>${s.label}</div><div class="st-desc">${s.desc}</div></div></div>`
  ).join("");
}

function renderCaps(){
  document.getElementById("capability-grid").innerHTML = CAPS.map(c =>
    `<div class="cap" data-api="${c.api}" onclick="runCapability('${c.api}')"><div class="cap-ico">${c.ico}</div><div class="cap-title">${c.title}</div><div class="cap-desc">${c.desc}</div></div>`
  ).join("");
}

function renderPatients(){
  const el = document.getElementById("patient-list");
  const ids = Object.keys(patients);
  if(!ids.length){ el.innerHTML = '<div class="muted" style="padding:8px">后端未连接 / 无患者</div>'; return; }
  el.innerHTML = ids.map(pid => {
    const p = patients[pid];
    const active = pid === selectedPid ? "active" : "";
    return `<div class="p-card ${active}" onclick="selectPatient('${pid}')"><div class="p-name">${p.name||pid}</div><div class="p-meta">${p.age||"?"}岁 · ${p.gender||""} · ${pid}</div><div class="p-meta">${p.diagnosis||""}</div></div>`;
  }).join("");
}

function selectPatient(pid){
  selectedPid = pid;
  renderPatients();
  document.getElementById("result-empty").style.display = "none";
  document.getElementById("result-content").innerHTML = `<div class="muted">已选择 ${patients[pid].name||pid}，点击能力卡执行 AI 诊疗</div>`;
}

async function apiCall(path, body){
  const r = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  if(!r.ok) throw new Error("HTTP "+r.status);
  return r.json();
}

async function loadPatients(){
  for(const pid of PATIENT_IDS){
    try{
      const d = await apiCall("/api/call", {agent:"orthopedic-surgery", tool:"his_patient", params:{patient_id:pid}});
      if(!d.error) patients[pid] = d;
    }catch(e){ /* 跳过失败项 */ }
  }
  renderPatients();
  computeKpi();  // Task 5 定义
}

// 主题切换
document.getElementById("theme-toggle").addEventListener("click", () => {
  document.body.classList.toggle("light");
  document.getElementById("theme-toggle").textContent = document.body.classList.contains("light") ? "🌙 深色" : "☀ 浅色";
});

// 初始化
renderStages();
renderCaps();
function computeKpi(){}      // Task 5 覆盖实现
function runCapability(){}   // Task 5 覆盖实现
loadPatients();
</script>
```

- [ ] **Step 4: 运行确认内容测试通过**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalContent -q`
Expected: PASS（3 项）。

- [ ] **Step 5: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-core/haip/ui_ortho_portal.html tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 门户 JS 患者队列/能力卡/阶段渲染"
```

---

## Task 5: 门户 JS — KPI 聚合 + 能力卡执行渲染

**Files:**
- Modify: `packages/haip-core/haip/ui_ortho_portal.html` (`<script>` 段的 `computeKpi` / `runCapability` 占位实现)
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: Task 4 的 `patients`、`selectedPid`、`apiCall`、`CAPS`；后端 `POST /api/v1/orthopedic/{timing,complications,classify,assess,plan,mdt,rehab,followup}`。
- Produces: 实际实现 `async function computeKpi()`（写入 5 个 `#kpi-*`）与 `async function runCapability(api)`（把结果渲染进 `#result-content`，含 urgency/overall_risk 徽章）。
- 入参组织规则：
  - timing: `{patient_id, labs, conditions, meds, ecg_findings:""}`
  - complications: `{patient_id, age, labs, conditions}`
  - classify: `{patient_id, xray_findings:{location:fracture_type, type:""}}`
  - assess: `{patient_id}`
  - plan: `{patient_id, fracture_type, age}`
  - mdt: `{patient_id, chief_complaint:diagnosis}`
  - rehab: `{patient_id, procedure}`
  - followup: `{patient_id, procedure}`

- [ ] **Step 1: 写 KPI/能力执行的锚点与函数存在性测试**

在 `test_ortho_portal.py` 追加：

```python
class TestPortalKpiAndRun:
    def _body(self):
        return client.get("/ortho-portal").text

    def test_kpi_uses_v1_api(self):
        body = self._body()
        assert "/api/v1/orthopedic/timing" in body
        assert "/api/v1/orthopedic/complications" in body

    def test_run_capability_dispatch(self):
        body = self._body()
        for api in ["classify","assess","mdt","timing",
                    "complications","plan","rehab","followup"]:
            assert "/api/v1/orthopedic/" + api in body

    def test_kpi_targets_present(self):
        body = self._body()
        for kid in ["kpi-total","kpi-pending","kpi-48h",
                    "kpi-highrisk","kpi-avgfactor"]:
            assert kid in body
```

（同时验证后端能力真实可算——集成冒烟）

```python
class TestV1ApiSmoke:
    def _p(self, pid):
        from orthopedics.his_adapter import MOCK_PATIENT_DB
        return MOCK_PATIENT_DB[pid]

    def test_timing_api(self):
        p = self._p("P003")
        r = client.post("/api/v1/orthopedic/timing",
                        json={"patient_id":"P003","labs":p["labs"],
                              "conditions":p["conditions"],"meds":p["meds"],
                              "ecg_findings":""})
        assert r.status_code == 200
        assert r.json()["urgency"] == "elective"

    def test_complications_api(self):
        p = self._p("P005")
        r = client.post("/api/v1/orthopedic/complications",
                        json={"patient_id":"P005","age":p["age"],
                              "labs":p["labs"],"conditions":p["conditions"]})
        assert r.status_code == 200
        assert r.json()["overall_risk"] in ("low","moderate","high")

    def test_plan_api(self):
        r = client.post("/api/v1/orthopedic/plan",
                        json={"patient_id":"P001","fracture_type":"股骨颈骨折","age":78})
        assert r.status_code == 200
        assert "procedure" in r.json()
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalKpiAndRun tests/integration/test_ortho_portal.py::TestV1ApiSmoke -q`
Expected: `TestPortalKpiAndRun` FAIL（占位空函数不含 v1 路径）；`TestV1ApiSmoke` 应已 PASS（后端就绪）。

- [ ] **Step 3: 用真实实现替换 `computeKpi` / `runCapability` 占位**

将 Task 4 中的这两行占位：

```javascript
function computeKpi(){}      // Task 5 覆盖实现
function runCapability(){}   // Task 5 覆盖实现
```

替换为：

```javascript
async function computeKpi(){
  const ids = Object.keys(patients);
  if(!ids.length){ return; }
  let pending=0, emergency=0, highrisk=0, factorSum=0, n=0;
  for(const pid of ids){
    const p = patients[pid];
    try{
      const t = await apiCall("/api/v1/orthopedic/timing",
        {patient_id:pid, labs:p.labs||{}, conditions:p.conditions||[], meds:p.meds||[], ecg_findings:""});
      if(t.urgency==="emergency") emergency++;
      if(t.urgency==="emergency"||t.urgency==="urgent") pending++;
      factorSum += (t.total_factors||0);
      const c = await apiCall("/api/v1/orthopedic/complications",
        {patient_id:pid, age:p.age||0, labs:p.labs||{}, conditions:p.conditions||[]});
      if(c.overall_risk==="high") highrisk++;
      n++;
    }catch(e){ /* 跳过 */ }
  }
  document.getElementById("kpi-total").textContent = ids.length;
  document.getElementById("kpi-pending").textContent = pending;
  document.getElementById("kpi-48h").textContent = n ? Math.round(emergency/n*100)+"%" : "—";
  document.getElementById("kpi-highrisk").textContent = highrisk;
  document.getElementById("kpi-avgfactor").textContent = n ? (factorSum/n).toFixed(1) : "—";
}

function badge(v){
  const cls = {high:"high",moderate:"moderate",low:"low",emergency:"emergency",urgent:"urgent",elective:"high"}[v] || "moderate";
  return `<span class="badge ${cls}">${v}</span>`;
}

function buildParams(api, p){
  const pid = selectedPid;
  switch(api){
    case "timing": return {patient_id:pid, labs:p.labs||{}, conditions:p.conditions||[], meds:p.meds||[], ecg_findings:""};
    case "complications": return {patient_id:pid, age:p.age||0, labs:p.labs||{}, conditions:p.conditions||[]};
    case "classify": return {patient_id:pid, xray_findings:{location:p.fracture_type||"", type:""}};
    case "assess": return {patient_id:pid};
    case "plan": return {patient_id:pid, fracture_type:p.fracture_type||"", age:p.age||0};
    case "mdt": return {patient_id:pid, chief_complaint:p.diagnosis||""};
    case "rehab": return {patient_id:pid, procedure:p.procedure||""};
    case "followup": return {patient_id:pid, procedure:p.procedure||""};
    default: return {patient_id:pid};
  }
}

async function runCapability(api){
  const content = document.getElementById("result-content");
  document.getElementById("result-empty").style.display = "none";
  if(!selectedPid){ content.innerHTML = '<div class="muted">请先在左侧选择患者</div>'; return; }
  const p = patients[selectedPid];
  content.innerHTML = '<div class="muted">调用中…</div>';
  try{
    const d = await apiCall("/api/v1/orthopedic/"+api, buildParams(api, p));
    let head = "";
    if(d.urgency) head += "手术时机: " + badge(d.urgency) + " · SLA " + (d.sla||"") + "<br>";
    if(d.overall_risk) head += "综合风险: " + badge(d.overall_risk) + "<br>";
    if(d.error) head += '<span class="badge high">错误</span> ' + d.error + "<br>";
    content.innerHTML = `<div style="margin-bottom:8px">${head}</div><div class="result-box">${JSON.stringify(d,null,2)}</div>`;
  }catch(e){
    content.innerHTML = '<div class="result-box"><span class="badge high">后端未连接</span> ' + e.message + '</div>';
  }
}
```

- [ ] **Step 4: 运行确认全部通过**

Run: `python -m pytest tests/integration/test_ortho_portal.py -q`
Expected: PASS（全部类）。

- [ ] **Step 5: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-core/haip/ui_ortho_portal.html tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 门户 KPI 聚合 + 能力卡真实 API 执行"
```

---

## Task 6: 回归 + Lint + 手动验收

**Files:**
- Test: 全量集成测试 + ruff

**Interfaces:**
- Consumes: Task 1-5 全部产物。
- Produces: 无（验证任务）。

- [ ] **Step 1: 运行创伤骨科相关全量测试确认回归通过**

Run: `python -m pytest tests/integration/test_ortho_portal.py tests/integration/test_orthopedic.py tests/test_html_pages.py -q`
Expected: PASS（含既有 `/ortho`、`/process`、`/workflow` 页面回归不受影响）。

- [ ] **Step 2: Lint**

Run: `ruff check packages/haip-hospital/modules/orthopedics/his_adapter.py tests/integration/test_ortho_portal.py`
Expected: `All checks passed!`（如有报错按提示修正，例如未使用 import）。

- [ ] **Step 3: 手动验收（人工）**

Run: `python -m uvicorn haip.web_server:app --port 8765`（workdir=`D:\FC\xhaip`，先 `set PYTHONPATH=packages/haip-core;packages/haip-hospital`）
浏览器访问 `http://127.0.0.1:8765/ortho-portal`，确认：
- KPI 5 卡显示真实数字（非「—」）。
- 左侧 5 位患者可点击选中。
- 点击 8 张能力卡，右侧面板渲染 API 结果与徽章。
- 深/浅主题切换正常。
- 「进入完整工作流」跳转 `/workflow/orthopedic-surgery`。

- [ ] **Step 4: 最终提交（若 lint 有修正）**

```powershell
git -C D:\FC\xhaip add -A
git -C D:\FC\xhaip commit -m "chore(ortho): 门户回归修正 + lint"
```

---

## Self-Review 记录

- **Spec 覆盖**：KPI 看板→Task5；8 能力卡→Task4/5；患者队列(5 位, his_adapter)→Task1/4；11 阶段时间轴→Task4；/ortho-portal 路由→Task2；设计令牌→Task3；测试→贯穿；回归+lint→Task6。全覆盖。
- **占位扫描**：无 TBD；每个代码步给出完整代码与命令。
- **类型一致性**：`computeKpi`/`runCapability` 在 Task4 声明占位、Task5 覆盖实现，签名一致；`apiCall/patients/selectedPid/CAPS/STAGES/PATIENT_IDS` 命名前后一致；后端 `query_patient` 透传字段名 (`labs/conditions/meds/fracture_type/procedure`) 与前端 `buildParams` 读取一致。
