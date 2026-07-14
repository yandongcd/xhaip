# haip-0710 → xhaip 精简收货计划

> v2.0 — 经架构/临床/飞检三轮审视 + 风暴精简 | 2026-07-12

## 目标

将 haip-0710 领先资产融入 xhaip，实现两库合一。精简策略：收获高价值，舍弃沉没资产。

## 核心原则

1. **收 (Harvest)**: 高价值可执行资产 → 移植
2. **融 (Absorb)**: 概念融入现有结构 → 不保留旧形态
3. **舍 (Discard)**: 沉没资产 → README 链接

## 收货清单

| # | 内容 | 方式 |
|---|------|------|
| 1 | GitHub 社区设施 (8 项) | 复制 + 路径修正 |
| 2 | 骨科 8 engine 模块 | 移植 + xhaip 适配 |
| 3 | TPN dataclass 升级 | 替换 xhaip 裸 dict |
| 4 | 6 个合并 operational skill | 合并 enrich |
| 5 | 患者 provenance + validate_patients.py | xhaip 现有数据加字段 |
| 6 | 架构概念融入 CURRENT | 300 行新文档 |

## 舍弃清单

| # | 内容 | 理由 |
|---|------|------|
| 1 | 0710 202 patients 全量合并 | 清洗成本高，xhaip 已有 498 |
| 2 | 16 SQL schemas | 不执行，README 链接 |
| 3 | 44 reference PDFs | 不执行，不索引 |
| 4 | 23 TOGAF education skills | docs/REFERENCE/ 已覆盖精华 |
| 5 | 4 UI design skills | 公开文档维护更好 |
| 6 | 3 dataset indexes | references 链接 |
| 7 | 0710 architecture.md 原样搬 | 描述旧系统 |
| 8 | 42 空壳 BP | 删除（虚假完备性） |
| 9 | NX 域 | Nexent 已剥离 |
| 10 | Archive 19 脚本 | 无复用价值 |

## Phase 1: 基础设施 + 数据质量 + 架构融合

### P1.1 GitHub 社区设施

| 文件 | 操作 |
|------|------|
| `.github/CODEOWNERS` | 复制 + 更新维护者 |
| `.github/dependabot.yml` | 复制 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 复制 + 命令修正 |
| `.github/SECURITY.md` | 复制 + 更新版本 |
| `.github/ISSUE_TEMPLATE/bug_report.md` | 复制 |
| `.github/ISSUE_TEMPLATE/feature_request.md` | 复制 |
| `.github/scripts/branch-protection.ps1` | 复制 + repo 名更新 |
| `.github/workflows/ci.yml` | 合并增强为 6-job |

### P1.2 患者数据

- patients.json 每个记录加 `provenance` 字段
- labs 格式升级为数组 (code/name/value/unit/ref_range/flag)
- 修复 4 个致命数据错误: P245/P246/P0001×2
- 新增 `scripts/validate_patients.py`

### P1.3 架构文档

```
docs/architecture/
├── INDEX.md
├── CURRENT/architecture.md     ← 融合 xhaip 真实架构 + 0710 核心概念
├── DESIGN/ (permission, rule-governance, design-decisions)
├── REFERENCE/ (TOGAF 5, UI 4, legacy v4)
├── semantic-mapping.md
├── ownership-matrix.md
└── path-mapping.md
```

## Phase 2: Engine 移植 + Skills 合并

### P2.1 骨科 Engine 移植

```python
# 每文件加 @origin 标注头
modules/orthopedics/
├── timing_engine.py       (825行, T2 仲裁)
├── checklist.py           (192行, 11项分诊)
├── fracture_classifier.py
├── complication_predictor.py
├── surgery_planner.py
├── completeness.py
├── rehab_tracker.py
└── osteoporosis_mgmt.py
```

### P2.2 TPN Dataclass 升级

0710 `TpnInput`/`TpnResult` dataclass 替换 xhaip module 的 dict 接口。

### P2.3 Skills 合并

6 个合并 skill: cardio / pharmacy / orthopedic / anesthesia / hospital-context / tco-roi

标记分段懒加载: `## QUICK_REF` + `## FULL:xxx`

## Phase 3: 合规标注 + 收尾

- `[DEV-ONLY]` 标注 (权限未实现)
- Citation 强制字段 (Agent YAML)
- `@origin` 头 (移植文件)
- 更新 README + AGENTS.md
- 删除 42 空壳 BP
