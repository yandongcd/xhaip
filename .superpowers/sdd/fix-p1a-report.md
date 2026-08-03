# P1-A 修复报告 — 规则 YAML / 端口冲突 / 孤儿 agent / 检验 key 漂移

- 执行人: fix subagent (P1-A)
- 日期: 2026-08-03
- 仓库: D:\dst\projects\xhaip
- 基准 commit: be011f7

---

## P1-1: 13 个规则 YAML 语法错误被静默丢弃

### 问题确认
`packages/haip-core/haip/togaf/rule_engine.py:107` 中 `except Exception: continue` 将全部解析失败的规则文件静默跳过，无任何可见性。

全仓扫描确认 **13 个文件解析失败**（`python yaml_census.py`，覆盖 knowledge/rules/ 与 knowledge/guideline_sources/ 递归全部 *.yaml）：

| 文件 | 错误类型 | 根因 |
|------|---------|------|
| rules/clinical_breast/breast_rules.yaml | mapping values are not allowed here | `guideline: NCCN Guidelines: Breast Cancer...` 值内含 `: `（共 3 行，line 9/81/163） |
| rules/clinical_endocrinology/endocrinology_rules.yaml | 同上 | `;` 分隔内联 map（37 行） |
| rules/clinical_gastroenterology/gastroenterology_rules.yaml | 同上 | `;` 分隔内联 map（15 行） |
| rules/clinical_geriatrics/geriatrics_rules.yaml | 同上 | `;` 分隔内联 map（19 行） |
| rules/clinical_neonatology/neonatology_rules.yaml | while parsing a block mapping | `;` 分隔内联 map + 2 处值内 prose `;`（31 行） |
| rules/clinical_nephrology/nephrology_rules.yaml | mapping values are not allowed here | `;` 分隔内联 map（30 行） |
| rules/clinical_obgyn/obgyn_rules.yaml | 同上 | `;` 分隔内联 map（6 行） |
| rules/clinical_pediatrics/pediatrics_rules.yaml | 同上 | `;` 分隔内联 map（40 行） |
| rules/clinical_psychiatry/psychiatry_rules.yaml | while parsing a block mapping | `;` 分隔内联 map + 2 处 `prolactin: -` 裸 dash 值（26 行） |
| rules/clinical_rehabilitation/rehabilitation_rules.yaml | 同上 | `;` 分隔内联 map + 值内 prose + 3 处字符串列表项含 `;`（92 行） |
| rules/clinical_tcm/tcm_rules.yaml | mapping values are not allowed here | `;` 分隔内联 map（57 行） |
| guideline_sources/registry.yaml | 同上 | `;` 分隔内联 map（150 行，342 行文件全量） |
| guideline_sources/drug_db_antiemetic.yaml | while scanning for the next token | flow 序列内项以 `>` 开头（line 205 `>50-75μg/kg`） |

### 修复内容
1. **YAML 文件修复**（编写转换脚本 `yaml_fix.py`，三种模式）：
   - SEPARATOR：`- field: X; operator: Y; value: Z` → 展开为 block map（续行 key 对齐首 key 列）。
   - PROSE-QUOTE：值内含 prose `;`（如 `type: 母乳优先; 早产儿配方奶次选`、`goal: ...; 禁忌深蹲/盘腿`、`bp_hr_limit: HR < 静息+20; RPE ≤ 13`）→ 整值合并加引号。特判 `髋:` 段为 prose（髋 ROM 详情是 goal 的延续）。
   - LIST-STRING：字符串列表项含 `;`（rehab components/readiness_criteria 共 3 行）→ 整行加引号。
   - 特例：breast 3 行 guideline 值引号化；drug_db line 205 flow 项引号化；psychiatry 2 处 `prolactin: -` → `prolactin: "-"`。
2. **可见性修复** `rule_engine.py:107`：
   ```python
   except Exception as exc:
       logger.warning("规则文件解析失败，已跳过: %s — %s: %s", yf, type(exc).__name__, exc)
       continue
   ```
   新增 `logging` + `logger = logging.getLogger(__name__)`。保留 continue（单个坏文件不阻断加载）。

### 验证
- 全量解析：修复前 13 个 FAIL → 修复后 **0 个 FAIL**（全部 174+ 个 YAML 通过 yaml.safe_load）。
- 规则 ID 保全：对 11 个 `;` 文件逐一对比 git HEAD 原文提取的 `id:` 集合 vs 修复后解析的 `id:` 集合，全部一致（geriatrics 的 9 个 "缺失" 为 `id: F1;` 正则带分号伪影，实际 ID 齐全）。
- `RuleEngine.load_all()` 由修复前（跳过 13 个文件）→ 修复后加载 **159 个规则组**，肾内科/内分泌科/乳腺中心/新生儿科/康复科/精神心理科/中医科/儿科/妇产科/老年病科等全部可加载。
- `python -m pytest packages/haip-core/tests/test_rules_engine.py packages/haip-core/tests/test_knowledge.py -q` → **59 passed**。
- `python -m ruff check packages/haip-core/haip/togaf/rule_engine.py` → clean。

---

## P1-4: 4 组 agent 端口冲突

### 冲突确认（修复前，扫描 agents/definitions/*.yaml）
- 8820: anesthesia.yaml vs pediatrics.yaml
- 8840: emergency-triage.yaml vs pain-hub.yaml
- 8841: acute-pain.yaml vs pc-aki.yaml
- 8843: hip-fracture-mdt.yaml vs joint-surgery.yaml

### 决策依据
- agents/ 下 .bat 启动器（根目录 `agents/*.bat`）：`pediatrics-web.bat`(8820)、`pain-hub-web.bat`(8840)、`acute-pain-web.bat`(8841) 存在 → 这 3 个 agent 保留原端口。
- `packages/haip-core/haip/web_launcher.py:22` DEFAULT_PORTS 亦确认 `pediatrics: 8820, pain-hub: 8840, acute-pain: 8841`（`_resolve_port` 优先读 YAML port 字段，无需改代码）。
- hip-fracture-mdt vs joint-surgery 均无 .bat；保留 hip-fracture-mdt（依赖关系更完整），joint-surgery 换端口。
- 空闲端口通过全量扫描 81 个 agent 的端口后从空闲区选取（运行时验证，未猜测）。

### 修复后端口
| Agent | 原端口 | 新端口 | 说明 |
|-------|--------|--------|------|
| anesthesia | 8820 | **8822** | 8822 空闲，邻近 8818-8821 麻醉/手术簇 |
| pediatrics | 8820 | 8820（保留） | 有 pediatrics-web.bat |
| emergency-triage | 8840 | **8832** | 8832 空闲，邻近 8831 |
| pain-hub | 8840 | 8840（保留） | 有 pain-hub-web.bat |
| acute-pain | 8841 | 8841（保留） | 有 acute-pain-web.bat |
| pc-aki | 8841 | **8862** | 先曾暂定 8844，后因 tpn-prescription 复活需用历史端口 8844 而改 8862 |
| hip-fracture-mdt | 8843 | 8843（保留） | 无 .bat，保留更完整 MDT 定义 |
| joint-surgery | 8843 | **8861** | 无 .bat，换 8861（空闲） |

注：docker-compose.yml 中 `anesthesia-risk` 服务用的是 8829（独立服务名），与本组修改无关，未动。

### 验证
- 重复端口扫描：81 个 agent → **0 duplicates**（修复前 4 组）。
- 最终含新增 agent 后：83 个 agent → **0 duplicates**。

---

## P1-5a: 孤儿模块 — 仅 .deprecated 定义的 agent

### 现状确认
- `tpn-prescription.yaml.deprecated`、`fall-prevention.yaml.deprecated` 存在；无对应活跃 YAML（sepsis-early-warning 已在先前批次修复为活跃 YAML + .deprecated 并存）。
- 模块 `modules/tpn_prescription`、`modules/fall_prevention` 存在。

### Handler 解析验证（python import + hasattr）
- tpn_prescription: nutrition_screen ✓ / energy_calculate ✓ / formula_design ✓ / safety_check ✓
- fall_prevention: morse_assess ✓ / prevention_plan ✓ / postop_check ✓
- 全部解析成功 → **创建活跃 YAML**。

### 决策
- `sepsis-early-warning.yaml` 修复模式为：活跃 YAML 与 .deprecated 内容一致（同 port 8846）。沿用该模式。
- **tpn-prescription.yaml**（新建）= .deprecated 内容逐字拷贝，port **8844**（历史端口）。
- **fall-prevention.yaml**（新建）= .deprecated 内容拷贝，port 8842 → **8863**（8842 为活跃 spine-surgery 占用，spine-surgery 保留）。
- 患者数据 `patients.json`/`patients_v2.json` 的 compatible_agents 中多处引用 `tpn-prescription` / `fall-prevention`（如 FB001 跌倒患者）——**数据文件未改动**，且这些引用在复活后反而有效。

### 验证
- `python scripts/validate_agents.py` → **83/83 passed**，exit 0。
- 重复端口扫描：83 agents → **0 duplicates**。
- `python -m pytest tests/test_handler_contracts.py` → **444 passed**（309+ handler 契约含新 agent）。

---

## P1-5b: 检验 key 大小写漂移（4 个模块）

### 数据实况（对 patients.json 10659 人 + patients_v2.json 10 人做 key 普查）
- D-dimer 变体：`D_Dimer`(10647) / `D_dimer`(10647) / `D-Dimer`(33)。模块读 `D-dimer`（不存在 → 恒用默认值 0.5）。
- Troponin 变体：`Troponin`(890) / `troponin`(45)。模块读 `troponin`（只命中 45 人）。
- `hsTnI`(10647) 全部为 0.0 —— 数据生成问题，**未触碰数据**（按指令）。
- K+ 变体：`K+`(10287) / `K`(101) / v2 中 `k`。
- TBil 变体：`TBil`(10647) / `TBIL`(7)。
- 注：`D_Dimer` 与 `D_dimer` 在 10090/10647 患者中数值不同（数据生成不一致，超出本次范围，未改动）。

### 修复（4 模块各加模块级 `_pick(labs, *keys)` helper，大小写 + `-`/`_` 归一化容错）
```python
def _pick(labs: dict | None, *keys: str):
    """取首个存在的检验值 — 大小写/连字符-下划线容错."""
    if not labs:
        return None
    for k in keys:
        if k in labs:
            return labs[k]
    norm: dict = {}
    for k, v in labs.items():
        norm[str(k).lower().replace("-", "_")] = v
    for k in keys:
        nk = str(k).lower().replace("-", "_")
        if nk in norm:
            return norm[nk]
    return None
```

| 模块 | 修复点 | 变更 |
|------|--------|------|
| modules/vte_management/__init__.py:214 | `labs.get("D-dimer", 0.5)` | → `_pick(labs, "D_Dimer", "D-dimer", "D_dimer", "D-Dimer") or 0.5` |
| modules/cardio_risk/__init__.py:115 + :279 | `labs.get("troponin", labs.get("cTnI", ...))` / `lab_results.get("troponin", 0)` | → `_pick(labs|lab_results, "troponin", "Troponin", "cTnI", "hsTnI")`（显式参数优先语义保留） |
| modules/cardiovascular_monitor/__init__.py:67 | `labs.get("troponin", 0)` | → `_pick(labs, "troponin", "Troponin", "cTnI", "hsTnI") or 0` |
| modules/pacer/__init__.py:162-163 | `labs.get("amylase")` / `labs.get("troponin")` | → `_pick(labs, "amylase", "Amylase") or 50`、`_pick(labs, "troponin", "Troponin", "cTnI", "hsTnI") or 0.01` |

### pacer 淀粉酶标签与阈值核查
- 模块判据文本（保留未改，line 50）：`"引流液淀粉酶 >3x血清淀粉酶上限 POD≥3"`。
- 模块读取的是 lab_results 的 **血清** 淀粉酶（引流液淀粉酶不存在于数据）。
- **标签修复**（line 183）：`引流液淀粉酶={amylase} (>3xULN)` → `血清淀粉酶={amylase} (>3xULN对照; 引流液标准)`，使输出标签诚实。
- **阈值说明（报告留痕）**：判据文本描述的是引流液淀粉酶 vs 3x 血清上限；模块用血清淀粉酶 >200 近似。由于数据无引流液淀粉酶字段，保持阈值 200 不变，仅标签修正 —— 若需严格 ISGPF 口径需数据补充引流液字段（超出本次范围）。
- 其余 `引流液淀粉酶` 引用（line 37 判据、192 建议"测定引流液淀粉酶/胆红素"）语义正确，未改。

### 验证
- 端到端（真实患者数据）：
  - `assess_risk(P001)` → `D-二聚体: 0.7 mg/L (升高)`（修复前恒为默认 0.5）
  - `assess_risk(P260)`（仅 `D-Dimer` 变体）→ 归一化命中 2.57 值路径
  - `evaluate_mi(P260)`（`Troponin: 1.689`）→ ok
  - `event_identify` / `complication_scan` / `evaluate` → ok
- `python -m pytest tests/ -k "vte or cardio_risk or pacer or cardiovascular or fall or tpn"` → **68 passed**。
- 复跑 `-k "cardio_risk or vte"` → 32 passed。
- `python -m ruff check .../modules/` → clean。

---

## 综合验证汇总

| 检查 | 结果 |
|------|------|
| YAML 全量解析（rules + guideline_sources） | 0 FAIL（修复前 13 FAIL） |
| `pytest test_rules_engine + test_knowledge` | 59 passed |
| `python scripts/validate_agents.py` | 83/83 passed, exit 0 |
| 端口重复扫描（83 agents） | 无重复 |
| `pytest tests/ -k "vte or cardio_risk or pacer or cardiovascular or fall or tpn"` | 68 passed |
| `pytest tests/test_handler_contracts.py` | 444 passed |
| `ruff check`（rule_engine + 全部 modules/） | clean |
| 患者数据文件 | 未改动 |

## 暂存与提交
- 暂存：仅本次变更文件（24 个修改 + 2 个新增），未用 `git add -A`；`docs/review/`、`eval_report.json`、`patient_agent.py`、`progression.py` 等非本次文件未暂存。
- 测试运行生成的 `knowledge/.guideline_snapshot.json` 已删除（运行时产物）。
- commit SHA: 见 `git log -1`（提交后回填）。

## 遗留观察（不阻塞）
1. `modules/orthopedics/__init__.py:167` 同样存在 `labs.get("troponin", labs.get("cTnI", 0))` 大小写漂移模式 —— 不在 P1-5b 指定 4 模块内，未改，建议后续统一处理。
2. `D_Dimer` 与 `D_dimer` 数据值不一致（10090/10647）为数据质量问题，未触碰。
3. hsTnI 全 0 为数据生成问题，未触碰。
4. pacer 血清淀粉酶 vs 引流液判据口径差异已在报告中说明，标签已诚实化。
