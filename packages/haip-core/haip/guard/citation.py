"""Citation Engine — 引文提取、信任等级推断、指南验证."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# ── Trust Level 关键词 ──

T1_KEYWORDS = [
    "国际", "WHO", "NICE", "AAOS", "ACCP", "AHA", "ACC", "ESC",
    "WS/T", "国家标准", "全国临床检验操作规程", "grade 1", "level 1",
    "KDIGO", "ADA", "ESPEN", "CSPEN", "ASPN", "CSCO",
]

T2_KEYWORDS = ["共识", "专家", "院内", "南方医院", "广东省", "科室", "中华医学会"]

EXTRACT_PATTERNS = [
    re.compile(r"\[ref:\s*(.+?)\]"),
    re.compile(r"参考[:：]\s*(.+?)(?:[。\n]|$)"),
    re.compile(r"依据(.+?指南)[，。\n]"),
    re.compile(r"根据(.+?标准)[，。\n]"),
]

# 工具 JSON 输出中的结构化引文字段 (门户/工作流 Guard 自动带入工具结果)
STRUCTURED_CITATION_KEYS = {"guideline_ref", "guideline_refs", "guideline", "evidence", "references"}


def _walk_citation_fields(node: object) -> list[str]:
    """递归收集 JSON 结构中引文字段的字符串值。"""
    found: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.lower() in STRUCTURED_CITATION_KEYS:
                if isinstance(v, str):
                    found.append(v)
                elif isinstance(v, list):
                    found.extend(x for x in v if isinstance(x, str))
            else:
                found.extend(_walk_citation_fields(v))
    elif isinstance(node, list):
        for item in node:
            found.extend(_walk_citation_fields(item))
    return found


@dataclass
class Citation:
    claim: str = ""
    source: str = ""
    trust_level: str = "T2"
    verified: bool = False
    guideline_file: str = ""
    warning: str = ""


class CitationEngine:
    """引文提取与验证引擎。"""

    def __init__(self, guidelines_dir: str | Path = ""):
        self._index: dict[str, Path] = {}
        if guidelines_dir:
            self.index_guidelines(Path(guidelines_dir))

    def index_guidelines(self, directory: Path) -> None:
        for path in directory.rglob("*"):
            if path.suffix in (".yaml", ".yml", ".md", ".txt"):
                stem = path.stem.lower()
                self._index[stem] = path
                parts = stem.replace("-", " ").replace("_", " ").split()
                for p in parts:
                    if len(p) >= 3:
                        self._index.setdefault(p, path)

    def extract(self, text: str) -> list[Citation]:
        citations: list[Citation] = []
        seen: set[str] = set()

        def _add(source: str) -> None:
            source = source.lstrip("#").strip()
            if source and source not in seen:
                seen.add(source)
                citations.append(Citation(
                    source=source,
                    trust_level=self._guess_trust_level(source),
                ))

        for pattern in EXTRACT_PATTERNS:
            for m in pattern.finditer(text):
                _add(m.group(1))
        # 结构化提取: 工具 JSON 输出的 guideline_ref/evidence 等字段
        stripped = text.lstrip()
        if stripped.startswith(("{", "[")):
            try:
                data = json.loads(stripped)
            except (json.JSONDecodeError, ValueError):
                data = None
            if data is not None:
                for src in _walk_citation_fields(data):
                    _add(src)
        return citations

    def verify(self, citations: list[Citation]) -> list[Citation]:
        for c in citations:
            if not self._index:
                c.warning = "no guidelines indexed"
                continue
            key = c.source.lower().replace(" ", "_").replace("-", "_")
            if key in self._index:
                c.verified = True
                c.guideline_file = str(self._index[key])
            else:
                for stem, path in self._index.items():
                    if stem in key or key in stem:
                        c.verified = True
                        c.guideline_file = str(path)
                        break
                if not c.verified:
                    c.warning = "未在指南资产库中找到对应文件"
        return citations

    def _guess_trust_level(self, text: str) -> str:
        for kw in T1_KEYWORDS:
            if kw.lower() in text.lower():
                return "T1"
        for kw in T2_KEYWORDS:
            if kw.lower() in text.lower():
                return "T2"
        return "T2"

    @staticmethod
    def has_unverified(citations: list[Citation]) -> bool:
        return any(not c.verified for c in citations)

    @staticmethod
    def all_t1(citations: list[Citation]) -> bool:
        return bool(citations) and all(c.trust_level == "T1" for c in citations)

    @staticmethod
    def format_summary(citations: list[Citation]) -> str:
        parts = []
        for c in citations:
            flag = "verified" if c.verified else "unverified"
            parts.append(f"[{flag}][{c.trust_level}] {c.source}")
        return "\n".join(parts)

    @staticmethod
    def detect_conflicts(citations: list[Citation]) -> list[dict[str, Any]]:
        """检测引用指南间的冲突 (MED-3).

        冲突判定: 同一临床主题有两篇以上 T1 指南, 且内容包含相互矛盾的推荐.
        当前实现: 关键词对比, 返回冲突对列表.
        """
        t1s = [c for c in citations if c.trust_level == "T1"]
        if len(t1s) < 2:
            return []

        conflict_pairs = [
            ("40mg", "20mg"),   # 剂量矛盾 (ACCP vs ESC 低分子肝素)
            ("bid", "qd"), ("每日两次", "每日一次"),
            ("推荐", "不推荐"), ("适用", "禁忌"),
            ("48h", "72h"), ("7天", "14天"),
        ]
        conflicts = []
        for i in range(len(t1s)):
            for j in range(i + 1, len(t1s)):
                a, b = t1s[i], t1s[j]
                for kw_a, kw_b in conflict_pairs:
                    if kw_a in a.source and kw_b in b.source:
                        conflicts.append({
                            "type": "dosing_conflict" if "mg" in kw_a else "recommendation_conflict",
                            "source_a": a.source,
                            "source_b": b.source,
                            "keyword_a": kw_a,
                            "keyword_b": kw_b,
                        })
                        break
        return conflicts[:5]
