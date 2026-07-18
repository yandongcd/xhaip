### Task 5: AGENTS.md 增补 + 全量验证

**Files:**
- Modify: `AGENTS.md` (质量门禁章节)

**Interfaces:**
- Consumes: Task 1-4 全部产物

- [ ] **Step 1: AGENTS.md 质量门禁章节增补**

在 "## 质量门禁" 代码块后追加:

```markdown
### UI 页面契约 (2026-07-17 起强制)

- 新增/修改 HTML 页面必须通过 `pytest tests/test_ui_contracts.py` (C1-C7: DOM id / onclick / PATIENTS / AGENT / fetch 路由 / workflow tool 契约)
- 数字病人加载必须走 `haip.patients.load_patients()`, 禁止各 UI 自行解析 patients.json
- 渲染函数禁止在循环中复用函数参数名 (ruff PLR1704 强制)
```

- [ ] **Step 2: 全量回归**

Run: `python -m pytest packages/haip-core/tests/ tests/ -q`
Expected: 全部 passed (含 integration; TestDemoPage 6 项既有失败与本次无关, 记录不阻断)

Run: `python -m ruff check packages/haip-core/ tests/; python -m mypy packages/haip-core/haip/`
Expected: 0 errors

- [ ] **Step 3: 手工冒烟**

重启 8769 服务, 浏览器验证 `/workflow/orthopedic-surgery`: 选患者 → 参数联动 → 执行 checklist → status ok。

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs: AGENTS.md 增补 UI 契约门禁"
```


---

## Global Constraints

- ruff line-length=100, `ignore=["E402"]` 保持不变, 新增 `extend-select=["PLR1704"]`
- mypy strict=false, 修改文件必须 0 错误
- 不引入新第三方依赖
- 不修改 ui_render.py / ui_ortho*.html / ui_pharmacy*.html 的实现 (契约测试兜底)
- 所有命令在 `D:\FC\xhaip` 执行

---

