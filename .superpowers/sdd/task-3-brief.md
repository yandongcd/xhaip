### Task 3: 清理 8 个 .openharness/skills/*/SKILL.md

**Files:**
- Modify: 下列 8 个文件的 `source:` YAML 块：
  - `.openharness/skills/xhaip-core/SKILL.md`
  - `.openharness/skills/xhaip-pharmacy/SKILL.md`
  - `.openharness/skills/xhaip-pediatrics/SKILL.md`
  - `.openharness/skills/xhaip-pain/SKILL.md`
  - `.openharness/skills/xhaip-cardio/SKILL.md`
  - `.openharness/skills/xhaip-orthopedic/SKILL.md`
  - `.openharness/skills/xhaip-anesthesia/SKILL.md`
  - `.openharness/skills/xhaip-masterdata/SKILL.md`

**Interfaces:**
- Consumes: 无
- Produces: 无 — 仅文档路径从绝对改为仓库相对

- [ ] **Step 1: 逐文件替换 source 块路径**

统一规则：`D:\FC\xhaip\packages\...` → `packages/...`；`D:\FC\xhaip\docs\...` → `docs/...`。逐文件精确替换（保留 YAML 缩进 `  - `）：

| 文件 | 旧值 | 新值 |
|------|------|------|
| xhaip-core (第 8-9 行) | `- D:\FC\xhaip\packages\haip-core` | `- packages/haip-core` |
| | `- D:\FC\xhaip\docs\specs\xhaip-refactoring-design.md` | `- docs/specs/xhaip-refactoring-design.md` |
| xhaip-pharmacy (第 7-8 行) | `- D:\FC\xhaip\packages\haip-hospital\agents\definitions\pharmacy.yaml` | `- packages/haip-hospital/agents/definitions/pharmacy.yaml` |
| | `- D:\FC\xhaip\packages\haip-hospital\modules\pharmacy\assessment\__init__.py` | `- packages/haip-hospital/modules/pharmacy/assessment/__init__.py` |
| xhaip-pediatrics (第 7-8 行) | `...\agents\definitions\pediatrics.yaml` | `packages/haip-hospital/agents/definitions/pediatrics.yaml` |
| | `...\modules\pediatrics\__init__.py` | `packages/haip-hospital/modules/pediatrics/__init__.py` |
| xhaip-pain (第 7 行) | `- D:\FC\xhaip\packages\haip-hospital\agents\definitions\pain-hub.yaml` | `- packages/haip-hospital/agents/definitions/pain-hub.yaml` |
| xhaip-cardio (第 7-8 行) | `...\agents\definitions\cardio-surgery.yaml` | `packages/haip-hospital/agents/definitions/cardio-surgery.yaml` |
| | `...\agents\definitions\cardio-risk.yaml` | `packages/haip-hospital/agents/definitions/cardio-risk.yaml` |
| xhaip-orthopedic (第 7-8 行) | `...\agents\definitions\orthopedic-surgery.yaml` | `packages/haip-hospital/agents/definitions/orthopedic-surgery.yaml` |
| | `...\modules\orthopedics\__init__.py` | `packages/haip-hospital/modules/orthopedics/__init__.py` |
| xhaip-anesthesia (第 7-8 行) | `...\agents\definitions\anesthesia-risk.yaml` | `packages/haip-hospital/agents/definitions/anesthesia-risk.yaml` |
| | `...\modules\anesthesia\__init__.py` | `packages/haip-hospital/modules/anesthesia/__init__.py` |
| xhaip-masterdata (第 7-8 行) | `...\agents\definitions\medical-record.yaml` | `packages/haip-hospital/agents/definitions/medical-record.yaml` |
| | `...\agents\definitions\metrics.yaml` | `packages/haip-hospital/agents/definitions/metrics.yaml` |

（省略号表示前缀 `D:\FC\xhaip\packages\haip-hospital\`。）

- [ ] **Step 2: 验证无残留**

Run: `Select-String -Path ".openharness\skills\*\SKILL.md" -Pattern "D:\\FC" | Measure-Object | Select-Object Count`
Expected: `Count: 0`

- [ ] **Step 3: 提交**

```bash
git add .openharness/skills/
git commit -m "docs: 8 个 SKILL.md source 路径改为仓库相对路径, 去除 D:\FC 外部引用"
```

---

