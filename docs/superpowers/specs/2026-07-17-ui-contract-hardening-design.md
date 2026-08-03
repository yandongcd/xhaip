# UI 契约加固与共性缺陷治理 — 设计文档

日期: 2026-07-17
状态: 已批准
来源: /workflow 页面三连 bug 复盘 (B1 患者数据空 / B2 JS id 缺失崩溃 / B3 变量遮蔽 AGENT 污染)

## 背景

2026-07-17 session 在 `/workflow/orthopedic-surgery` 页面连续发现 3 个缺陷:

| Bug | 现象 | 根因 | 根因类别 |
|-----|------|------|---------|
| B1 | 数字病人列表为空 | `ui_workflow._load_patients` 只接受 list 格式, patients.json 实为 `{"total","patients"}` dict | 患者加载逻辑重复 4+ 处, 格式假设各异, 静默回退 `[]` |
| B2 | 选患者后参数不更新 | JS 引用 `hp-badge`/`rb-current-stage`, DOM 中不存在 → TypeError 中断 | f-string 拼 HTML+JS 无契约校验 |
| B3 | 所有工具调用报 `Unknown agent: 护士长` | 循环变量 `name` 遮蔽函数参数 `name` | 300+ 行渲染大函数作用域污染 |
| B4 | Guard 引文恒 `verified:false` (NICE NG37 在库仍未验证) | `/api/guard` 裸构造 `GuardVerifier()`, CitationEngine 从未索引指南目录 | 组件支持注入但调用点未接线; 测试只有结构断言 |

### 测试未拦截的原因

1. `/workflow/*` 路由零测试覆盖
2. 既有测试只做结构断言 (标签存在), 无语义断言 (数据非空、AGENT 正确)
3. 恒真断言 (test_p4.py `assert len(cm.cases) >= 0`)
4. 静默失败设计 (`_load_patients` 异常返回 `[]` 无告警)
5. 测试间隐式依赖 (`HAIP_TEST_MODE` 靠其他测试文件先设置)

## 设计 (方案 A + 补充)

### 1. 共享患者加载器

- 新建 `packages/haip-core/haip/patients.py`:
  `load_patients(agent_name: str, limit: int = 8) -> list[dict]`
  - 统一处理 dict (`data["patients"]`) / list 两种格式
  - 按 `compatible_agents` 过滤, 无匹配时回退全量前 N
  - 文件缺失/解析失败时 `logger.warning`, 返回 `[]`
- `ui_workflow._load_patients` 与 `ui_process._load_patients` 改为薄封装:
  - ui_process 保留 `_normalize_patients` / `_fallback_patients` 行为不变

### 2. 全站 UI 契约测试

新建 `tests/test_ui_contracts.py`, 参数化覆盖所有 HTML 路由
(`/`, `/workflow/*`, `/process/*`, `/agent/*`, `/ortho`, `/ortho-portal`, `/pharmacy`, `/stream-demo`, `/dashboard`):

| 契约 | 校验内容 | 拦截缺陷类 |
|------|---------|-----------|
| C1 | `getElementById('x')` 静态 id 必须存在于 DOM | B2 |
| C2 | `onclick="fn()"` 引用函数必须有 `function fn` 定义 | B2 |
| C3 | 嵌入 `PATIENTS` 的页面数据非空且含 `patient_id` | B1 |
| C4 | 嵌入 `AGENT` 的页面其值 == 路由 agent 名 | B3 |
| C5 | 页面 `fetch('/api/xxx')` 路径必须在 `app.routes` 注册 | 前后端漂移 |
| C6 | workflow.py `STAGES[].tool` 必须存在于 agent YAML tools | Unknown tool |
| C7 | `querySelector('#xxx')` 静态 id 引用同 C1 | B2 |

### 3. Lint 强化

- pyproject.toml ruff 启用 `PLR1704` (redefined-argument-from-local)
- 实施时先在 B3 修复前代码上验证该规则确实报错

### 4. 渲染函数拆分 (仅 ui_workflow.py)

- `render_workflow_ui` 内联循环拆为 `_build_role_pills(roles)` /
  `_build_stage_nav(stages)` / `_build_stage_panels(stages)`
- 主函数只做组装, 函数参数不再暴露于循环作用域

### 5. 测试基础设施

- 新建 `tests/conftest.py`: 统一 `HAIP_TEST_MODE=true` + 共享 TestClient fixture
- 全仓扫描并清理恒真断言 (`assert len(...) >= 0` 等模式)

### 6. 静默失败治理 (最小范围)

- `CaseManager.load` 的 `except Exception: pass` → `logger.warning`
- 共享加载器统一 warning 出口

### 7. 文档沉淀

- AGENTS.md 增补:
  - 新增 UI 页面必须通过 `tests/test_ui_contracts.py`
  - 渲染函数禁止在循环中复用参数名 (PLR1704 强制)

## 不做的事 (YAGNI)

- 不引入 Jinja2 等模板引擎 (方案 B, 改动面大)
- 不重构 a2a/其他模块的 try/except (超出本次范围)
- 不改 ui_render.py / ui_ortho*.html 等页面的实现 (契约测试兜底即可)

## 验证标准

1. 契约测试先证明有效: 临时注入 B2/B3 类错误, 测试必须变红
2. `pytest tests/ packages/haip-core/tests/` 全量通过
3. `ruff check` (含 PLR1704) + `mypy packages/haip-core/haip/` 0 错误
4. 手工冒烟: `/workflow/orthopedic-surgery` 选患者 → 参数联动 → 执行工具 → status ok
