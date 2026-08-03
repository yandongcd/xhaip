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

