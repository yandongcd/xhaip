# Task 3 Report: 构建门户 HTML — 布局与设计令牌

## 实现内容

将 `ui_ortho_portal.html` 从骨架替换为完整静态布局，包含：
- 设计令牌：CSS 自定义属性（`--accent`, `--bg`, `--card-bg`, `--text` 等），`body.light` 浅色模式
- 布局区域：header（含 `#theme-toggle`）、`#kpi-bar`（5 列 KPI）、`#patient-list`（左侧 240px）、`#capability-grid`（4 列网格）、`#stage-timeline`（11 阶段）、`#result-panel`（右侧 360px）
- 空 `<script>` 占位供 Task 4/5 填充 JS

## TDD 证据

### RED（Step 2：骨架 HTML 无锚点）
```
$ python -m pytest tests/integration/test_ortho_portal.py::TestPortalLayout -q
FF  [100%]
FAILED test_has_layout_anchors — 缺锚点 kpi-bar
FAILED test_has_title_and_tokens — 缺 --accent
2 failed, 1 warning in 1.21s
```

### GREEN（Step 4：完整 HTML 锚点全部通过）
```
$ python -m pytest tests/integration/test_ortho_portal.py -q
..........  [100%]
10 passed, 1 warning in 0.95s
```
新测试 `TestPortalLayout`（2 项）通过，原有 `TestPatientData`（3 项）、`TestUrgencyDistribution`（3 项）、`TestPortalRoute`（2 项）无回归。

## 文件变更

| 文件 | 操作 | 变更 |
|------|------|------|
| `packages/haip-core/haip/ui_ortho_portal.html` | MODIFY | 骨架 → 完整静态 HTML+CSS（含 6 个稳定锚点 + 设计令牌） |
| `tests/integration/test_ortho_portal.py` | MODIFY | 追加 `TestPortalLayout` 类（2 个测试方法） |

## 自检

- 所有 6 个锚点 id 已在 HTML 中：`kpi-bar`, `patient-list`, `capability-grid`, `result-panel`, `stage-timeline`, `theme-toggle`
- CSS 令牌 `--accent` 和 `body.light` 规则已包含
- 标题含 "创伤骨科"
- 空 `<script>` 占位符已保留
- 未删除原有测试类
- 仅 staged 指定两个文件

## 关注点

无。
