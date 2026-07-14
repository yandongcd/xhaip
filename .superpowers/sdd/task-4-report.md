# Task 4: 门户 JS — 患者队列 + 能力卡 + 阶段时间轴渲染

## 实现内容

- `packages/haip-core/haip/ui_ortho_portal.html`: 将占位 `<script>/* Task 4/5 填充 JS */</script>` 替换为完整 JS 块，包含：
  - 常量 `PATIENT_IDS` (5 患者)、`CAPS` (8 能力卡)、`STAGES` (11 阶段)
  - 渲染函数 `renderPatients()` / `renderCaps()` / `renderStages()`
  - 患者选择 `selectPatient(pid)`
  - API 调用助手 `apiCall(path, body)`
  - 异步患者加载 `loadPatients()` (POST /api/call, tool=his_patient)
  - 主题切换事件绑定
  - 两个空占位函数 `computeKpi()` / `runCapability()` (Task 5 覆盖)
- `tests/integration/test_ortho_portal.py`: 追加 `TestPortalContent` 类 (3 测试)

## TDD 证据

### RED (Step 2)
```
$ python -m pytest tests/integration/test_ortho_portal.py::TestPortalContent -q
FFF    [100%]
3 failed — 占位脚本不含 JS 常量，确认失败
```

### GREEN (Step 4)
```
$ python -m pytest tests/integration/test_ortho_portal.py -q
.............    [100%]
13 passed — TestPortalContent + 所有已有测试通过
```

## 修改文件

| 文件 | 操作 |
|------|------|
| `packages/haip-core/haip/ui_ortho_portal.html` | 替换 script 块 |
| `tests/integration/test_ortho_portal.py` | 追加 TestPortalContent |

## 自审

- 所有 13 集成测试通过，无回归
- 两个占位函数保持空签名，供 Task 5 覆盖
- 未删除已有测试类 (TestPatientData / TestUrgencyDistribution / TestPortalRoute / TestPortalLayout)

## 关切

无。
