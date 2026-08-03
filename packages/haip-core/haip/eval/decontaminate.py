"""去污染 — n-gram 重叠检测 (Fully Open Meditron 两阶段管道借鉴, 轻量版).

用途: 评测场景/合成语料 与 知识库/外部基准 的重叠检测, 防止"同源自洽虚高"
(SEAL 教训: 生成器/评估器/知识源同源 → 分数虚高).

实现: 文本 n-gram (n=5..8) 归一化集合, Jaccard 重叠率, 超阈值标记候选污染.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

NGRAM_MIN = 5
NGRAM_MAX = 8
CONTAMINATION_THRESHOLD = 0.15  # Jaccard 重叠率阈值


def _normalize(text: str) -> str:
    """归一化: 小写、去空白、去标点."""
    text = text.lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。！？；：、（）()\[\]【】\"'《》<>.,;:!?\-_/]", "", text)
    return text


def ngrams(text: str, n: int) -> set[str]:
    """提取字符级 n-gram 集合."""
    t = _normalize(text)
    if len(t) < n:
        return {t} if t else set()
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def text_signature(text: str) -> set[str]:
    """多尺度 n-gram 并集 (n=5..8)."""
    sig: set[str] = set()
    for n in range(NGRAM_MIN, NGRAM_MAX + 1):
        sig |= ngrams(text, n)
    return sig


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def overlap_ratio(a: set[str], b: set[str]) -> float:
    """重叠率: |a ∩ b| / min(|a|, |b|) — 检测 a 是否被 b 覆盖."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def check_contamination(
    candidate: str,
    reference: str,
    threshold: float = CONTAMINATION_THRESHOLD,
) -> dict[str, Any]:
    """检测 candidate 与 reference 的重叠.

    返回 {jaccard, overlap, contaminated, detail}
    """
    a = text_signature(candidate)
    b = text_signature(reference)
    j = jaccard(a, b)
    ov = overlap_ratio(a, b)
    return {
        "jaccard": round(j, 4),
        "overlap": round(ov, 4),
        "contaminated": j >= threshold or ov >= threshold,
        "detail": f"jaccard={j:.3f} overlap={ov:.3f} (阈值 {threshold})",
    }


def check_corpus_against_refs(
    corpus: Iterable[str],
    references: Iterable[str],
    threshold: float = CONTAMINATION_THRESHOLD,
) -> list[dict[str, Any]]:
    """批量检测: corpus 中每条 vs 全部 references, 返回污染条目."""
    ref_sigs = [(r, text_signature(r)) for r in references if r]
    flagged = []
    for i, item in enumerate(corpus):
        if not item:
            continue
        item_sig = text_signature(item)
        for ref, ref_sig in ref_sigs:
            j = jaccard(item_sig, ref_sig)
            ov = overlap_ratio(item_sig, ref_sig)
            if j >= threshold or ov >= threshold:
                flagged.append({
                    "index": i,
                    "jaccard": round(j, 4),
                    "overlap": round(ov, 4),
                    "detail": f"语料[{i}] 与参考文本重叠 (j={j:.3f}, ov={ov:.3f})",
                })
                break
    return flagged
