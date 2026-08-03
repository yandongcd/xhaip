# xhaip 免安装自包含 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 xhaip 仓库不依赖 xhaip 文件夹之外的任何包/路径：clone 后零安装（不执行 `pip install -e packages/haip-core`）即可运行与测试。

**Architecture:** 在仓库根目录新增 `sitecustomize.py`，Python 启动时（根目录在 sys.path 时）自动注入 `packages/haip-core`、`packages/haip-hospital`、`packages/haip-hospital/modules` 三个内部路径；同时清除全部指向仓库外部的硬编码路径（`D:\FC\...`、`C:\Users\...`、`D:\dst\projects\haip\...`），新增回归测试防止外部路径引用复发。

**Tech Stack:** Python 3.10+（仅标准库），pytest，PowerShell（仅 download.ps1 涉及）。

**Spec:** `docs/superpowers/specs/2026-08-02-xhaip-self-contained-design.md`

## Global Constraints

- 所有命令在 `D:\dst\projects\xhaip` 执行（PowerShell，`python -m pytest` / `python -m ruff` 而非裸命令）
- 禁止在代码/文档中写入任何指向 xhaip 文件夹之外的绝对路径（`D:\FC\`、`C:\Users\`、`D:\dst\projects\haip\` 等）
- ruff line-length=100；新增代码不添加注释（模块 docstring 除外）
- 提交风格遵循仓库历史：`feat:` / `fix:` / `test:` / `docs:` 前缀
- 新增测试必须通过 `tests/conftest.py`（已注入 sys.path），不再新增 `sys.path.insert`
- 最终回归：`python -m pytest packages/haip-core/tests/ tests/ -q` 全绿（当前 1759 测试）+ `python -m ruff check .` 无新增告警

---

### Task 1: 根目录 sitecustomize.py 自举（TDD）

**Files:**
- Create: `sitecustomize.py`（xhaip 根目录）
- Test: `tests/test_self_contained.py`（本任务只写注入断言部分）

**Interfaces:**
- Consumes: 无
- Produces: `sitecustomize` 模块 — 无公开 API；副作用为把 3 个内部路径按序 `sys.path.insert(0, ...)`（去重、目录不存在时跳过）。Task 7 复用同一测试文件追加扫描测试。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_self_contained.py`：

```python
"""xhaip 自包含回归测试：仓库内不得引用 xhaip 文件夹之外的路径/包。"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_BACKSLASH = chr(92)
_FORBIDDEN_PATTERNS = (
    "D:" + _BACKSLASH + "FC",
    "D:" + "/" + "FC",
    "D:" + _BACKSLASH + "dst" + _BACKSLASH + "projects" + _BACKSLASH + "haip",
    "D:" + "/" + "dst" + "/" + "projects" + "/" + "haip",
    "C:" + _BACKSLASH + "Users",
    "C:" + "/" + "Users",
)

_SKIP_DIRS = {
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "htmlcov", ".audit", ".code-review-graph", "releases", "node_modules",
    ".superpowers",
}
_SKIP_PREFIXES = (
    os.path.join("docs", "superpowers", ""),
)
_TEXT_SUFFIXES = {
    ".py", ".md", ".yaml", ".yml", ".bat", ".ps1", ".toml", ".json",
    ".txt", ".cfg", ".ini", ".sh", ".example",
}


def _iter_text_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir != ".":
            rel = rel_dir + os.sep
            if any(rel.startswith(p) for p in _SKIP_PREFIXES):
                dirnames[:] = []
                continue
        for name in filenames:
            if Path(name).suffix.lower() in _TEXT_SUFFIXES:
                yield Path(dirpath) / name


def test_sitecustomize_injects_internal_paths():
    importlib.import_module("sitecustomize")
    importlib.reload(sys.modules["sitecustomize"])
    for rel in ("packages/haip-core", "packages/haip-hospital",
                "packages/haip-hospital/modules"):
        assert str(ROOT / rel) in sys.path, f"{rel} 未注入 sys.path"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_self_contained.py::test_sitecustomize_injects_internal_paths -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sitecustomize'`（根目录下尚不存在该文件）

- [ ] **Step 3: 创建 sitecustomize.py**

创建 `sitecustomize.py`（xhaip 根目录，与 pyproject.toml 同级）：

```python
"""xhaip 免安装自举：启动时注入内部包路径，无需 pip install -e。

Python 启动时若仓库根目录在 sys.path 上（从根目录运行 python -m ...），
本文件自动执行，使 packages/ 下的包无需安装即可导入。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_INTERNAL_DIRS = (
    "packages/haip-core",
    "packages/haip-hospital",
    "packages/haip-hospital/modules",
)

for _rel in _INTERNAL_DIRS:
    _d = ROOT / _rel
    if _d.is_dir():
        _p = str(_d)
        if _p not in sys.path:
            sys.path.insert(0, _p)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_self_contained.py::test_sitecustomize_injects_internal_paths -q`
Expected: PASS

- [ ] **Step 5: 验证零安装启动**

Run: `python -c "import haip; print(haip.__file__)"`
Expected: 打印 `...\packages\haip-core\haip\__init__.py`（来自仓库内部路径，而非 site-packages）

- [ ] **Step 6: 提交**

```bash
git add sitecustomize.py tests/test_self_contained.py
git commit -m "feat: 根目录 sitecustomize 自举, 免 pip install 即可运行 (self-contained)"
```

---

### Task 2: 清理 tests/test_antiemetic.py 死路径

**Files:**
- Modify: `tests/test_antiemetic.py:14-16`

**Interfaces:**
- Consumes: `tests/conftest.py`（已把 `packages/haip-hospital/modules` 注入 sys.path）
- Produces: 无 — 删除后测试行为不变（conftest 兜底已验证：35 passed）

- [ ] **Step 1: 删除死路径**

删除 `tests/test_antiemetic.py` 第 14-16 行：

```python
import sys

sys.path.insert(0, r"D:\FC\xhaip\packages\haip-hospital\modules")
```

即文件从：

```python
import sys

sys.path.insert(0, r"D:\FC\xhaip\packages\haip-hospital\modules")

import pytest
```

改为：

```python
import pytest
```

（`sys` 在文件其余 314 行中无其他使用，已核实。）

- [ ] **Step 2: 验证测试通过**

Run: `python -m pytest tests/test_antiemetic.py -q`
Expected: `35 passed`

- [ ] **Step 3: 提交**

```bash
git add tests/test_antiemetic.py
git commit -m "fix: 移除 test_antiemetic 指向已删除外部目录 D:\FC 的 sys.path"
```

---

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

### Task 4: scripts/batch_md2.py 外部技能路径可选化

**Files:**
- Modify: `scripts/batch_md2.py`

**Interfaces:**
- Consumes: 环境变量 `MINIMAX_PDF_SCRIPTS`（可选，未设置时走 pypdf 降级）
- Produces: `pdf_to_md_minimax(fp: Path) -> str` 行为不变（签名、返回值语义相同），仅外部技能目录缺失时不再静默失败而是直接降级

- [ ] **Step 1: 移除硬编码外部路径**

修改 `scripts/batch_md2.py`：

1. 第 5 行后新增 `import os`（第 5-6 行从）：

```python
import subprocess
from pathlib import Path
```

改为：

```python
import os
import subprocess
from pathlib import Path
```

2. 第 8-9 行从：

```python
NEDS_DIR = Path(__file__).resolve().parent.parent / "docs" / "needs"
PDF_SKILL = Path(r"C:\Users\12362\.config\opencode\skills\minimax-pdf\scripts")
```

改为：

```python
NEDS_DIR = Path(__file__).resolve().parent.parent / "docs" / "needs"
PDF_SKILL_DIR = Path(os.environ.get("MINIMAX_PDF_SCRIPTS", ""))
```

3. 第 16-30 行 `pdf_to_md_minimax` 从：

```python
def pdf_to_md_minimax(fp: Path) -> str:
    """Use minimax-pdf reformat_parse.py to extract PDF content."""
    try:
        result = subprocess.run(
            ["py", str(PDF_SKILL / "reformat_parse.py"),
             "--input", str(fp), "--format", "text"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Fallback to pypdf
    return pdf_to_md_fallback(fp)
```

改为：

```python
def pdf_to_md_minimax(fp: Path) -> str:
    """Use minimax-pdf reformat_parse.py to extract PDF content."""
    if PDF_SKILL_DIR.is_dir():
        try:
            result = subprocess.run(
                ["py", str(PDF_SKILL_DIR / "reformat_parse.py"),
                 "--input", str(fp), "--format", "text"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

    return pdf_to_md_fallback(fp)
```

- [ ] **Step 2: 验证导入与 lint**

Run: `python -c "import scripts.batch_md2"`（从根目录）
Expected: 无输出、无报错（`PDF_SKILL_DIR` 为空 Path 时 `.is_dir()` 为 False，安全）

Run: `python -m ruff check scripts/batch_md2.py`
Expected: `All checks passed!`

- [ ] **Step 3: 提交**

```bash
git add scripts/batch_md2.py
git commit -m "fix: batch_md2 移除 C:\Users 外部技能路径, 改 MINIMAX_PDF_SCRIPTS 可选降级"
```

---

### Task 5: tools/medical-standards-downloader 相对路径化

**Files:**
- Modify: `tools/medical-standards-downloader/update_index.py`
- Modify: `tools/medical-standards-downloader/generate_all_refs.py`
- Modify: `tools/medical-standards-downloader/download_refs.py`
- Modify: `tools/medical-standards-downloader/download.ps1`

**Interfaces:**
- Consumes: 无
- Produces: 4 个脚本输出路径全部改为基于 `Path(__file__)` / `$PSScriptRoot` 的相对定位（`<root>/docs/standards/...`），不再硬编码 `D:\dst\projects\xhaip`

- [ ] **Step 1: 修改 update_index.py**

第 6 行从：

```python
IDX = Path(r"D:\dst\projects\xhaip\docs\standards\standards-index.json")
```

改为：

```python
IDX = Path(__file__).resolve().parent.parent.parent / "docs" / "standards" / "standards-index.json"
```

（`tools/medical-standards-downloader/` 上溯 3 级 = 仓库根。）

- [ ] **Step 2: 修改 generate_all_refs.py**

第 7 行从：

```python
OUTPUT = Path("D:/dst/projects/xhaip/docs/standards/downloads")
```

改为：

```python
OUTPUT = Path(__file__).resolve().parent.parent.parent / "docs" / "standards" / "downloads"
```

- [ ] **Step 3: 修改 download_refs.py**

第 9 行从：

```python
OUTPUT = Path("D:/dst/projects/xhaip/docs/standards/downloads")
```

改为：

```python
OUTPUT = Path(__file__).resolve().parent.parent.parent / "docs" / "standards" / "downloads"
```

- [ ] **Step 4: 修改 download.ps1**

第 10 行从：

```powershell
$OutputDir = "D:\dst\projects\xhaip\docs\standards\downloads"
```

改为：

```powershell
$OutputDir = Join-Path $PSScriptRoot "..\..\docs\standards\downloads"
```

第 197 行从：

```powershell
Write-Host "    - URLs saved to D:\dst\projects\xhaip\docs\standards\downloads\"
```

改为：

```powershell
Write-Host "    - URLs saved to $OutputDir"
```

- [ ] **Step 5: 验证无残留 + 语法**

Run: `Select-String -Path "tools\medical-standards-downloader\*" -Pattern "D:\\dst|D:/dst" | Measure-Object | Select-Object Count`
Expected: `Count: 0`

Run: `python -m py_compile tools/medical-standards-downloader/update_index.py tools/medical-standards-downloader/generate_all_refs.py tools/medical-standards-downloader/download_refs.py`
Expected: 无输出（编译成功）

Run: `powershell -NoProfile -Command "& 'D:\dst\projects\xhaip\tools\medical-standards-downloader\download.ps1' -List"`（仅列出目录内容，不触发下载）
Expected: 正常输出目录列表（若目录为空则显示 0 个文件），无路径报错

- [ ] **Step 6: 提交**

```bash
git add tools/medical-standards-downloader/
git commit -m "fix: medical-standards-downloader 硬编码绝对路径改脚本相对定位"
```

---

### Task 6: 清理 docs 下两处外部路径

**Files:**
- Modify: `docs/specs/xhaip-refactoring-design.md:17`
- Modify: `docs/commercial-readiness.md:50`

**Interfaces:**
- Consumes: 无
- Produces: 无 — 历史文档中的外部路径描述改写为仓库相对/通用表述

- [ ] **Step 1: 修改 docs/specs/xhaip-refactoring-design.md**

第 17 行从：

```
D:\FC\xhaip\
```

改为：

```
xhaip/
```

- [ ] **Step 2: 修改 docs/commercial-readiness.md**

第 50 行从：

```
> 方法: 以南方医院 14 类 174 角色逐一扮演审视 (5 批次并行), 报告见 `D:\FC\productions\xhaip-role-audit\`。
```

改为：

```
> 方法: 以南方医院 14 类 174 角色逐一扮演审视 (5 批次并行), 报告见外部审计存档 (历史路径已失效)。
```

- [ ] **Step 3: 验证**

Run: `Select-String -Path "docs\specs\xhaip-refactoring-design.md","docs\commercial-readiness.md" -Pattern "D:\\FC|C:\\Users" | Measure-Object | Select-Object Count`
Expected: `Count: 0`

- [ ] **Step 4: 提交**

```bash
git add docs/specs/xhaip-refactoring-design.md docs/commercial-readiness.md
git commit -m "docs: 清理 specs/commercial-readiness 中的 D:\FC 外部路径引用"
```

---

### Task 7: 回归防护测试 test_self_contained.py 扫描测试

**Files:**
- Modify: `tests/test_self_contained.py`（追加扫描测试，Task 1 已建文件）

**Interfaces:**
- Consumes: `_iter_text_files`（Task 1 已定义）、`_FORBIDDEN_PATTERNS`、`_SKIP_DIRS`、`_SKIP_PREFIXES`
- Produces: `test_no_external_absolute_paths()` — 断言仓库内无外部绝对路径引用（此测试能捕获 D:\FC、C:\Users、兄弟项目 haip 路径）

- [ ] **Step 1: 追加扫描测试**

在 `tests/test_self_contained.py` 末尾追加：

```python
def test_no_external_absolute_paths():
    offenders = []
    for fp in _iter_text_files(ROOT):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pat in _FORBIDDEN_PATTERNS:
            if pat in text:
                offenders.append((str(fp.relative_to(ROOT)), pat))
    assert not offenders, (
        "外部路径引用:\n" + "\n".join(f"{p}: {pat}" for p, pat in sorted(offenders))
    )
```

- [ ] **Step 2: 运行确认通过**

Run: `python -m pytest tests/test_self_contained.py -q`
Expected: `2 passed`（注入测试 + 扫描测试；Task 1-6 修复完成后应立即全绿）

- [ ] **Step 3: 证明扫描测试确实能捕获违规（红→绿验证）**

Run（PowerShell）:

```powershell
New-Item -ItemType Directory -Force -Path "temp_probe" | Out-Null
Set-Content -Path "temp_probe/probe.py" -Value "X = r'D:\FC\xhaip\probe'"
python -m pytest tests/test_self_contained.py::test_no_external_absolute_paths -q
Remove-Item -Recurse -Force "temp_probe"
```

Expected: 中间 pytest 输出 FAIL，断言信息包含 `temp_probe\probe.py`；`Remove-Item` 后重新运行 `python -m pytest tests/test_self_contained.py -q` 恢复 `2 passed`。

- [ ] **Step 4: 提交**

```bash
git add tests/test_self_contained.py
git commit -m "test: 自包含回归防护 — 扫描全仓禁止外部绝对路径引用"
```

---

### Task 8: 文档更新 + 全量验证

**Files:**
- Modify: `README.md:14-16`（快速开始）
- Modify: `AGENTS.md:9-12`（快速开始）

**Interfaces:**
- Consumes: Task 1 的 sitecustomize.py（使"直接运行"成为可能）
- Produces: 文档不再要求 `pip install -e "packages/haip-core[dev]"`

- [ ] **Step 1: 更新 README.md 快速开始**

第 14-20 行从：

````markdown
```bash
pip install -e "packages/haip-core[dev]"
python -m pytest packages/haip-core/tests/ tests/integration/ -v

# 数据质量检查
python scripts/validate_patients.py
```
````

改为：

````markdown
```bash
# 免安装自包含: 从仓库根目录直接运行 (sitecustomize.py 自动注入内部包路径)
python -m uvicorn haip.web_server:app
python -m pytest packages/haip-core/tests/ tests/ -v

# 数据质量检查
python scripts/validate_patients.py
```

> 可选: 需要打包分发时 `pip install -e "packages/haip-core[dev]"`（仅此场景需要）。
````

- [ ] **Step 2: 更新 AGENTS.md 快速开始**

第 9-12 行从：

````markdown
```bash
cd xhaip
pip install -e "packages/haip-core[dev]"
pytest packages/haip-core/tests/ tests/integration/ -v
ruff check .
mypy packages/haip-core/haip/
```
````

改为：

````markdown
```bash
cd xhaip
python -m pytest packages/haip-core/tests/ tests/ -v   # 免安装: sitecustomize.py 自动注入内部路径
python -m ruff check .
python -m mypy packages/haip-core/haip/
```
````

- [ ] **Step 3: 全量回归**

Run: `python -m pytest packages/haip-core/tests/ tests/ -q`
Expected: `1759 passed`（无新增失败；若数量有出入以"全部通过、无失败"为准）

Run: `python -m ruff check .`
Expected: 无新增告警（修复文件仅删改路径字符串，不影响 lint）

- [ ] **Step 4: 零安装冒烟验证**

Run（模拟未安装 haip-core 的干净导入路径）:

```powershell
$env:PYTHONPATH = ""; Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
python -c "import sitecustomize; import haip; from haip.web_server import app; print('self-contained OK')"
```

Expected: 打印 `self-contained OK`（依赖 sitecustomize 注入，而非任何 pip 安装的 haip 包）

- [ ] **Step 5: 提交**

```bash
git add README.md AGENTS.md
git commit -m "docs: 快速开始改为免安装直接运行, pip install -e 降级为可选"
```

---

## Self-Review 记录（计划作者执行）

1. **Spec 覆盖**：sitecustomize 自举 → Task 1；test_antiemetic 死路径 → Task 2；8 个 SKILL.md → Task 3；batch_md2 → Task 4；medical-standards-downloader → Task 5；docs 历史引用 → Task 6；回归防护测试 → Task 7；README/AGENTS 文档 + 验证 → Task 8。成功标准 1-4 均有对应任务。
2. **占位符扫描**：所有步骤含完整代码/命令/预期输出；SKILL.md 替换表为逐文件完整新旧值。
3. **类型一致性**：`pdf_to_md_minimax` 签名与降级行为跨 Task 4 前后一致；`_iter_text_files`/`_FORBIDDEN_PATTERNS` 在 Task 1 定义、Task 7 复用，名称一致；`sitecustomize` 模块名在 Task 1 测试与 Task 8 冒烟验证一致。
4. **有意偏移 TDD**：Task 7 扫描测试在修复完成后落地（而非前置红基线），避免提交红色测试污染历史；Step 3 的红→绿探针验证证明该测试确实能捕获违规，回归防护能力等效且更干净。
