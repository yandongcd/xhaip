# 设计文档：xhaip 免安装自包含（无外部依赖）

- 日期: 2026-08-02
- 状态: 已批准（用户确认方案 A）
- 目标: xhaip 仓库内代码不再依赖 xhaip 文件夹之外的任何包/路径，clone 后零安装即可运行

## 背景与现状

xhaip 的核心引擎位于 `packages/haip-core`，业务位于 `packages/haip-hospital`。
当前运行/测试依赖 `pip install -e "packages/haip-core[dev]"`（把包装入 xhaip 外的
site-packages），且存在多处指向仓库外部的硬编码路径引用：

1. `tests/test_antiemetic.py:16` — `sys.path.insert(0, r"D:\FC\xhaip\...")`（该路径已不存在，属死代码，靠 `tests/conftest.py` 兜底才能过测试）
2. `.openharness/skills/*/SKILL.md`（8 个）— 文档中 `D:\FC\xhaip\...` 旧仓库路径
3. `scripts/batch_md2.py` — 依赖 `C:\Users\...\.config\opencode\skills\minimax-pdf\scripts`（本机 opencode 技能路径）
4. `tools/medical-standards-downloader/*` — 硬编码 `D:\dst\projects\xhaip\...` 绝对路径（虽在仓库内，但不可移植）

用户需求（已确认）：
- 把 haip-core 集成进 xhaip，不依赖 xhaip 文件夹之外的包
- 方案选择: **方案 A — 根目录 `sitecustomize.py` 自举**（免安装自包含）

## 方案选型

| 方案 | 做法 | 结论 |
|------|------|------|
| A. sitecustomize 自举 | 根目录 sitecustomize.py 自动注入内部包路径 | **采用**（改动最小、零安装、测试体系零破坏） |
| B. 根 pyproject 统一管理 | packages.find where=["packages"] 合并发行版 | 仍需一次 `pip install -e .`，非真正免安装 |
| C. 物理合并 | packages 上移根目录平铺 | 动 1759 个测试路径机制，风险大收益小 |

## 组件与改动

### 1. 新增 `sitecustomize.py`（xhaip 根目录）

- Python 启动时自动执行（当根目录位于 sys.path，即从仓库根运行 `python -m ...` 时）
- 将以下路径按序加入 `sys.path`（去重；目录不存在时静默跳过，不抛异常）：
  - `<root>/packages/haip-core`
  - `<root>/packages/haip-hospital`
  - `<root>/packages/haip-hospital/modules`
- `<root>` 由 `Path(__file__).resolve().parent` 定位，不依赖 cwd
- 只读操作，不引入任何第三方依赖

预期效果：
- `cd xhaip && python -m uvicorn haip.web_server:app` — 直接可用
- `cd xhaip && python -m pytest` — 直接可用
- `agents/*.bat` — 不受影响（本身已设 PYTHONPATH）

### 2. 清理外部路径引用

| 文件 | 改动 |
|------|------|
| `tests/test_antiemetic.py:16` | 删除死路径 `sys.path.insert(0, r"D:\FC\xhaip\...")` |
| `.openharness/skills/xhaip-{core,pharmacy,orthopedic,cardio,anesthesia,pain,pediatrics,masterdata}/SKILL.md` | `D:\FC\xhaip\` → 仓库相对路径 |
| `scripts/batch_md2.py` | minimax-pdf 路径改为可选（目录存在才启用，否则跳过并提示） |
| `tools/medical-standards-downloader/{update_index,generate_all_refs,download_refs}.py` 与 `download.ps1` | `D:\dst\projects\xhaip\...` → 脚本所在目录相对定位 |

### 3. 文档更新

- `README.md` 快速开始: 移除 `pip install -e "packages/haip-core[dev]"` 前置步骤，改为直接运行
- `AGENTS.md` 快速开始: 同上；保留 `pip install -e` 为可选打包方式（注明）

### 4. 回归防护 — 新增 `tests/test_self_contained.py`

- 扫描仓库内 `.py/.md/.yaml/.yml/.bat/.ps1/.toml/.json` 文件，断言不含外部绝对路径引用：
  - `D:\FC\`、`D:\dst\projects\haip\`（兄弟项目）、`C:\Users\` 等
- 白名单豁免：历史归档类文档（`.superpowers/sdd/`、`docs/superpowers/plans/` 历史记录）、`tools/medical-standards-downloader/`（已改为相对路径后不再需要豁免）
- 断言 `sitecustomize.py` 存在且能正确注入 3 个内部路径（导入并检查 sys.path）

## 错误处理

- `sitecustomize.py` 全程只添加存在的目录；`ImportError`/路径异常不处理即静默（符合 sitecustomize 惯例）
- `batch_md2.py`：外部技能目录缺失时降级跳过并打印警告，不中断
- 若用户环境存在 site-packages 里的 sitecustomize：本仓库根目录在 sys.path 优先级更高，先加载我们的（纯增量行为，无冲突）

## 测试策略

- 新增 `tests/test_self_contained.py`（外部引用扫描 + sitecustomize 注入断言）
- 全量回归: `pytest packages/haip-core/tests/ tests/`（1759 测试）
- 质量门禁: `ruff check .`、`mypy packages/haip-core/haip/`

## 成功标准

1. 全新环境 clone xhaip 后，仅安装第三方依赖（pip 装 pydantic/fastapi 等），不安装 haip-core 自身包即可:
   `cd xhaip && python -m uvicorn haip.web_server:app` 正常启动
2. 仓库内无任何指向 xhaip 文件夹之外的文件/路径引用（含死代码）
3. 1759 测试全绿，ruff/mypy 无新增告警
4. 不再需要 `pip install -e "packages/haip-core"`（文档不再要求，测试不再依赖）

## 明确不做（YAGNI）

- 不合并 packages/haip-core 与 packages/haip-hospital（保持现有架构）
- 不移除第三方 pip 依赖（pydantic/fastapi/sqlalchemy 等为正常依赖，不属于"xhaip 外部的包"范畴——即非本仓库自研包）
- 不改动 46 个 agents/*.bat（已有 PYTHONPATH，行为不变）
- 不迁移 .openharness/skills 结构
