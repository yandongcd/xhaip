"""Step 3: Identify top gaps and handle web downloads.
Counts how many needs docs cite each unmatched guideline, prioritizes.
"""
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "docs" / "guidelines" / "guideline-index.md"

print("=== 从索引中提取高频未匹配指南 ===")

text = INDEX.read_text(encoding="utf-8")
in_unmatched = False
unmatched = []
for line in text.split("\n"):
    if "## 2. 未匹配指南" in line:
        in_unmatched = True
        continue
    if in_unmatched and line.startswith("## "):
        break
    if in_unmatched and line.startswith("- "):
        cite = line[2:].strip()
        # Extract just the citation text (remove tags)
        cite = re.sub(r'\s*[🌐📝✓].*$', '', cite)
        unmatched.append(cite)

# Now count by reading needs docs
NEEDS_DIR = ROOT / "docs" / "needs"
cite_count = Counter()

CN_PATTERN = re.compile(r'《([^》]+)》')
EN_PATTERN = re.compile(
    r'\b((?:NICE|AAOS|NCCN|CSCO|WHO|ESPEN|ASPEN|CSPEN|ASRA|SAMBA|'
    r'ACR|ESUR|NKF|ACC|AHA|ESC|KDIGO|CLSI|EUCAST|EULAR|'
    r'GINA|GOLD|SCCM|EFORT|NASS|ASIA|SRS|'
    r'JBI|CONSORT|STARD|TRIPOD|PRISMA|'
    r'EAU|AUA|CUA|BCLC|CNLC|FIGO|'
    r'APACHE|SOFA|SHEA|IDSA|APIC|CDC|NHSN)\s*(?:\d{4}|v?\d+\.?\d*|[\w\-]+))',
    re.IGNORECASE
)

for md_file in sorted(NEEDS_DIR.glob("*.md")):
    t = md_file.read_text(encoding="utf-8")
    for m in CN_PATTERN.finditer(t):
        cite = f"《{m.group(1)}》"
        cite_count[cite] += 1
    for m in EN_PATTERN.finditer(t):
        cite = m.group(1).strip()
        cite_count[cite] += 1

print("\n=== Top 30 最高频未匹配指南（多个文档引用）===\n")
print(f"{'引用次数':<6} {'指南名称'}")
print("-" * 80)

count = 0
for cite, n in cite_count.most_common():
    if cite in unmatched and n >= 2:
        count += 1
        needs_web = any(kw in cite for kw in [
            "ESPEN", "ASPEN", "ASRA", "SAMBA", "WS/T", "GB/T",
            "NICE NG", "AAOS 202", "KDIGO 202", "SHEA", "CDC/NHSN"
        ])
        flag = "🌐" if needs_web else "📝"
        print(f"{n:<6} {flag} {cite}")
        if count >= 30:
            break

print(f"\n=== 需要网络下载的指南（共 {sum(1 for c,u in cite_count.items() if c in unmatched and any(kw in c for kw in ['ESPEN','ASPEN','ASRA','WS/T','GB/T','NICE NG','SHEA']))} 条）===")
for cite, n in cite_count.most_common():
    if cite in unmatched and any(kw in cite for kw in [
        "ESPEN", "ASPEN", "ASRA", "SAMBA", "WS/T", "GB/T",
        "NICE NG", "AAOS 202", "SHEA", "CDC/NHSN"
    ]):
        print(f"  {n}x — {cite}")
