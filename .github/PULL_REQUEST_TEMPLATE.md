## PR Checklist

请确认以下各项已完成（未完成项请在描述中说明原因）：

### 变更类型
- [ ] 新增 Agent（含 YAML definition + handler 模块）
- [ ] 修改引擎代码（packages/haip-core/）
- [ ] 修改知识资产（guidelines/rules/business_processes）
- [ ] 修复 Bug
- [ ] 文档更新

### 代码规范
- [ ] YAML Agent 定义通过 schema 校验
- [ ] Handler 模块无直接 import 其他 Agent 模块（使用 A2A Dispatcher）
- [ ] 无硬编码路径（使用 config 路径解析）
- [ ] 无 `packages/` 目录下的运行时数据

### Agent 注册（如适用）
- [ ] `agents/definitions/xxx.yaml` — 完整的 Agent 定义
- [ ] `modules/xxx/` — Handler 模块已实现
- [ ] A2A 路由 — 通过 YAML `handler` 字段自动生成（无需手动注册）

### 验证
- [ ] `xhaip list` 新 Agent 可见
- [ ] `python -m pytest packages/haip-core/tests/ -q` 全部通过
- [ ] `python -m pytest tests/integration/ -v` 全部通过
- [ ] `ruff check packages/ tests/` 0 errors
- [ ] 覆盖率 ≥ 70%（haip-core）

### 描述
<!-- 简要描述此 PR 的变更内容和原因 -->