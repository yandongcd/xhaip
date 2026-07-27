"""Knowledge Base — 指南与规则管理 (YAML → SQLite 同步)."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

# ── 数据模型 ──

CREATE_GUIDELINES = """
CREATE TABLE IF NOT EXISTS guidelines (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    abbr TEXT,
    publisher TEXT,
    version TEXT,
    trust_level TEXT DEFAULT 'T2',
    language TEXT DEFAULT 'zh',
    source_file TEXT,
    key_sections TEXT  -- JSON array of section names
)
"""

CREATE_RULES = """
CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    rule_set_id TEXT NOT NULL,
    decision_point TEXT NOT NULL,
    condition_expr TEXT,
    conclusion TEXT NOT NULL,
    rule_type TEXT DEFAULT 'deterministic',
    certainty TEXT DEFAULT 'strong',
    evidence_sources TEXT,  -- JSON array of source_id
    exceptions TEXT,        -- JSON array
    priority INTEGER DEFAULT 0
)
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_rules_set ON rules(rule_set_id)",
    "CREATE INDEX IF NOT EXISTS idx_rules_decision ON rules(decision_point)",
    "CREATE INDEX IF NOT EXISTS idx_guidelines_trust ON guidelines(trust_level)",
]


class KnowledgeStore:
    """指南 + 规则的 SQLite 存储。启动时从 YAML 同步，运行时毫秒级查询。"""

    def __init__(self, db_path: str = ":memory:"):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.db.execute("PRAGMA journal_mode=WAL")
        from haip.schema_version import ensure_version
        ensure_version(self.db, 1)
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.execute(CREATE_GUIDELINES)
        self.db.execute(CREATE_RULES)
        for idx in CREATE_INDEXES:
            self.db.execute(idx)
        self.db.commit()

    # ── 指南 ──

    def upsert_guideline(self, data: dict) -> None:
        import json
        with self._lock:
            self.db.execute(
                """INSERT OR REPLACE INTO guidelines
                   (id, name, abbr, publisher, version, trust_level, language, source_file, key_sections)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (data["id"], data["name"], data.get("abbr"), data.get("publisher"),
                 data.get("version"), data.get("trust_level", "T2"), data.get("language", "zh"),
                 data.get("source_file"), json.dumps(data.get("key_sections", []))),
            )
            self.db.commit()

    def get_guideline(self, gid: str) -> dict | None:
        row = self.db.execute("SELECT * FROM guidelines WHERE id = ?", (gid,)).fetchone()
        return dict(row) if row else None

    def search_guidelines(self, keyword: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM guidelines WHERE name LIKE ? OR abbr LIKE ? OR publisher LIKE ?",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_by_trust_level(self) -> dict[str, int]:
        rows = self.db.execute(
            "SELECT trust_level, COUNT(*) as cnt FROM guidelines GROUP BY trust_level"
        ).fetchall()
        return {r["trust_level"]: r["cnt"] for r in rows}

    # ── 规则 ──

    def upsert_rule(self, data: dict) -> None:
        import json
        with self._lock:
            self.db.execute(
                """INSERT OR REPLACE INTO rules
                   (id, rule_set_id, decision_point, condition_expr, conclusion,
                    rule_type, certainty, evidence_sources, exceptions, priority)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (data["id"], data["rule_set_id"],
                 data.get("decision_point", data.get("id", "")),
                 data.get("condition_expr"), data.get("conclusion", data.get("decision_point", "")),
                 data.get("rule_type", "deterministic"), data.get("certainty", "strong"),
                 json.dumps(data.get("evidence_sources", [])),
                 json.dumps(data.get("exceptions", [])),
                 data.get("priority", 0)),
            )
            self.db.commit()

    def find_rules(self, decision_point: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM rules WHERE decision_point = ? ORDER BY priority",
            (decision_point,),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_rules(self, rule_set_id: str = "") -> int:
        if rule_set_id:
            row = self.db.execute(
                "SELECT COUNT(*) as cnt FROM rules WHERE rule_set_id = ?", (rule_set_id,)
            ).fetchone()
        else:
            row = self.db.execute("SELECT COUNT(*) as cnt FROM rules").fetchone()
        return row["cnt"] if row else 0

    # ── YAML 同步 ──

    def sync_from_dir(self, guidelines_dir: Path | None = None,
                      rules_dir: Path | None = None) -> dict[str, int]:
        import yaml
        stats: dict[str, int] = {"guidelines": 0, "rules": 0}

        if guidelines_dir and guidelines_dir.exists():
            for path in guidelines_dir.glob("*.yaml"):
                with open(path, encoding="utf-8") as f:
                    try:
                        data = yaml.safe_load(f)
                    except yaml.YAMLError:
                        continue
                if isinstance(data, dict) and "id" in data:
                    if "rule_sets_covered" in data or "publisher" in data:
                        data["source_file"] = str(path)
                        self.upsert_guideline(data)
                        stats["guidelines"] += 1

        if rules_dir and rules_dir.exists():
            for path in rules_dir.rglob("*.yaml"):
                if path.name in ("registry.yaml", "conflict_policy.yaml"):
                    continue
                with open(path, encoding="utf-8") as f:
                    try:
                        data = yaml.safe_load(f)
                    except yaml.YAMLError:
                        continue
                if isinstance(data, dict):
                    rules = data.get("rules", [])
                    rs_id = data.get("id", path.stem)
                    for rule in rules:
                        if isinstance(rule, dict) and "id" in rule:
                            rule["rule_set_id"] = rs_id
                            self.upsert_rule(rule)
                            stats["rules"] += 1
        return stats

    def close(self) -> None:
        self.db.close()
