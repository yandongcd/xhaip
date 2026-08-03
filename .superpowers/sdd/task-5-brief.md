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

