"""临床病例数据管理 — 加载 + 搜索 + 统计.

整合 data/patients.json (100 数字病人) 提供运行时病例查询。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CaseManager:
    """临床病例管理: 加载 + 搜索 + 统计。"""

    def __init__(self, data_dir: str | Path = ""):
        self.cases: list[dict[str, Any]] = []
        if data_dir:
            self.load(Path(data_dir))

    def load(self, directory: Path):
        """从目录加载患者数据 (JSON/YAML)。"""
        if not directory.exists():
            return
        for f in directory.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "patients" in data:
                    self.cases.extend(data["patients"])
                elif isinstance(data, list):
                    self.cases.extend(data)
            except Exception as e:
                logger.warning("病例文件加载失败 %s: %s", f, e)

    def search(self, query: str = "", department: str = "",
               diagnosis: str = "", age_min: int = 0, age_max: int = 120,
               limit: int = 50) -> list[dict[str, Any]]:
        """多条件搜索病例。"""
        results = []
        q = query.lower()
        for c in self.cases:
            if q and q not in json.dumps(c, ensure_ascii=False).lower():
                continue
            if department and c.get("department") != department:
                continue
            if diagnosis and diagnosis.lower() not in c.get("diagnosis", "").lower():
                continue
            age = c.get("age", c.get("age_months", 0))
            if age < age_min or age > age_max:
                continue
            results.append(c)
            if len(results) >= limit:
                break
        return results

    def get(self, patient_id: str) -> dict[str, Any] | None:
        for c in self.cases:
            if c.get("patient_id") == patient_id:
                return c
        return None

    def stats(self) -> dict[str, Any]:
        depts: dict[str, int] = {}
        for c in self.cases:
            d = c.get("department", "unknown")
            depts[d] = depts.get(d, 0) + 1
        return {"total": len(self.cases), "by_department": depts}

    def compatible_agents(self, patient_id: str) -> list[str]:
        """返回该患者兼容的 Agent 列表。"""
        c = self.get(patient_id)
        return c.get("compatible_agents", []) if c else []
