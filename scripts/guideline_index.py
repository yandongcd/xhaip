"""Step 1-2: Extract guideline references from docs/needs/, cross-reference with knowledge/guidelines/.
Produces: docs/guidelines/guideline-index.md (comprehensive cross-reference)
"""
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NEEDS_DIR = ROOT / "docs" / "needs"
GUIDELINES_DIR = ROOT / "packages" / "haip-hospital" / "knowledge" / "guidelines"
OUTPUT_DIR = ROOT / "docs" / "guidelines"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Scan existing guideline YAML files ──
existing_guidelines = {}
for gf in sorted(GUIDELINES_DIR.glob("*.yaml")):
    if gf.name.startswith("_"):
        continue
    try:
        data = yaml.safe_load(gf.read_text(encoding="utf-8"))
        name = data.get("name", gf.stem) if isinstance(data, dict) else gf.stem
        existing_guidelines[gf.stem] = {
            "file": gf.name,
            "name": name if isinstance(name, str) else gf.stem,
            "source": data.get("source", "") if isinstance(data, dict) else "",
            "version": data.get("version", "") if isinstance(data, dict) else "",
        }
    except Exception:
        existing_guidelines[gf.stem] = {"file": gf.name, "name": gf.stem, "source": "", "version": ""}

print(f"Existing guidelines: {len(existing_guidelines)}")

# ── 2. Extract guideline citations from needs documents ──
# Chinese pattern: 《...》
CN_PATTERN = re.compile(r'《([^》]+)》')
# English pattern: acronyms like "NICE NG37", "AAOS 2022", "WHO IMCI 2014", "ESPEN 2023"
EN_PATTERN = re.compile(
    r'\b((?:NICE|AAOS|NCCN|CSCO|WHO|ESPEN|ASPEN|CSPEN|ASRA|SAMBA|'
    r'SHEA|IDSA|APIC|CDC|NHSN|ACR|ESUR|NKF|ACC|AHA|ESC|KDIGO|CLSI|'
    r'EUCAST|EULAR|ACR|ARHP|GINA|GOLD|SCCM|EFORT|NASS|ASIA|SRS|'
    r'JBI|GRADE|CONSORT|STARD|TRIPOD|PRISMA|STROBE|CAP|ACS|FIGO|'
    r'EAU|AUA|CUA|BCLC|CNLC|MELD|APACHE|SOFA)\s*(?:\d{4}|v?\d+\.?\d*|'
    r'[\w\-]+))', re.IGNORECASE
)

needs_refs = defaultdict(list)  # doc_stem → list of citations
all_citations = set()

for md_file in sorted(NEEDS_DIR.glob("*.md")):
    text = md_file.read_text(encoding="utf-8")
    doc_id = md_file.stem.split("-")[0] if "-" in md_file.stem else md_file.stem

    # Chinese citations
    for m in CN_PATTERN.finditer(text):
        cite = f"《{m.group(1)}》"
        if len(cite) > 10 and cite not in all_citations:
            all_citations.add(cite)
            needs_refs[doc_id].append(cite)

    # English citations
    for m in EN_PATTERN.finditer(text):
        cite = m.group(1).strip()
        if len(cite) > 5 and cite not in all_citations:
            all_citations.add(cite)
            needs_refs[doc_id].append(cite)

print(f"Documents with citations: {len(needs_refs)}")
print(f"Unique citations found: {len(all_citations)}")

# ── 3. Match citations to existing guidelines ──
# Fuzzy matching: extract key terms from both sides
def normalize(s: str) -> str:
    """Normalize for fuzzy matching."""
    # Remove punctuation, spaces, special chars
    s = re.sub(r'[《》「」\s\-_，。、：；（）\(\)\d{4}年版]', '', s.lower())
    # Expand known abbreviations
    abbrev = {
        '老年髋部骨折诊疗与管理指南': 'nhc hip fracture',
        '术后恶心呕吐诊疗指南': 'ponv antiemetic',
        '中国高血压防治指南': 'hypertension cma',
        '中国脓毒症': 'sepsis ssc',
        '患者安全目标': 'patient safety fall prevention',
    }
    for k, v in abbrev.items():
        s = s.replace(k.lower(), v)
    return s

matched = set()
unmatched = set()

for cite in all_citations:
    found = False
    cite_norm = normalize(cite)
    for stem, info in existing_guidelines.items():
        stem_norm = normalize(stem)
        name_norm = normalize(str(info.get("name", "")))
        # Check if any significant keyword overlap (at least 5 chars)
        for keyword in cite_norm.split():
            if len(keyword) >= 3 and (keyword in stem_norm or keyword in name_norm):
                matched.add(cite)
                found = True
                break
        if found:
            break
    if not found:
        unmatched.add(cite)

print(f"Matched to existing guidelines: {len(matched)}")
print(f"Unmatched (need to download or create): {len(unmatched)}")

# ── 4. Generate guideline index markdown ──
lines = [
    "# xhaip 指南引用索引",
    f"\n> 自动生成于 2026-07-26 | 来源: {len(needs_refs)} 份需求文档 | 已有指南: {len(existing_guidelines)} 份",
    f"\n> 匹配率: {len(matched)}/{len(all_citations)} ({len(matched)*100//max(len(all_citations),1)}%)",
    "",
    "---",
    "",
    "## 1. 已匹配指南（可直接引用）",
    "",
]
for cite in sorted(matched):
    lines.append(f"- {cite} ✓")

lines.extend([
    "",
    "## 2. 未匹配指南（需从网络获取或创建）",
    "",
])
for cite in sorted(unmatched):
    # Determine if this needs web download
    needs_web = any(kw in cite for kw in [
        "WS/T", "GB/T", "WS_T", "GB_T",  # Chinese standards
        "NICE", "ESPEN", "ASPEN", "ASRA", "SAMBA",  # International
    ])
    tag = " 🌐 需下载" if needs_web else " 📝 可从docs/needs提取"
    lines.append(f"- {cite}{tag}")

lines.extend([
    "",
    "## 3. 按科室分布",
    "",
])

# By department (from doc filename)
dept_map = defaultdict(set)
for doc_id, cites in needs_refs.items():
    # Find matching need file
    matching = list(NEEDS_DIR.glob(f"{doc_id}-*.md"))
    if matching:
        dept_name = matching[0].stem.split("-", 1)[1].split("-")[0] if len(matching[0].stem.split("-")) > 1 else "未知"
    else:
        dept_name = "未知"
    dept_map[dept_name].update(cites)

for dept in sorted(dept_map.keys()):
    lines.append(f"### {dept}")
    for cite in sorted(dept_map[dept]):
        status = "✓" if cite in matched else "❌"
        lines.append(f"- {status} {cite}")
    lines.append("")

lines.extend([
    "## 4. 已有指南全文清单",
    "",
])
for stem in sorted(existing_guidelines.keys()):
    info = existing_guidelines[stem]
    lines.append(f"- `{info['file']}` — {info['name']}")

lines.extend([
    "",
    "## 5. 待下载指南（P0 优先）",
    "",
    "| 指南 | 供谁引用 | 来源 | 状态 |",
    "|------|---------|------|:---:|",
    "| WS/T 405-2012 检验危急值 | lab-critical-value | 国家卫健委 | 🌐 待下载 |",
    "| WS/T 312-2009 医院感染监测 | infection-control | 国家卫健委 | 🌐 待下载 |",
    "| ESPEN 2023 肠外肠内营养 | pharmacy | ESPEN官网 | 🌐 待下载 |",
    "| ASRA 2025 抗凝指南 | anesthesia | ASRA官网 | 🌐 待下载 |",
    "",
    "---",
    "*由 scripts/guideline_index.py 自动生成*",
])

output_path = OUTPUT_DIR / "guideline-index.md"
output_path.write_text("\n".join(lines), encoding="utf-8")
print(f"\nIndex written to: {output_path}")
print(f"Total lines: {len(lines)}")

# ── 5. Summary for unmatched P0 items ──
print("\n=== P0 缺失指南 ===")
for cite in sorted(unmatched):
    if any(kw in cite for kw in ["WS/T", "GB/T", "NICE", "ESPEN", "ASPEN", "ASRA", "SAMBA", "KDIGO"]):
        print(f"  🔴 {cite}")
