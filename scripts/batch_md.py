"""Batch extract text from docs/needs → .md files.
Usage: py scripts/batch_md.py [--limit N]
"""
import re
from pathlib import Path

NEDS_DIR = Path(__file__).resolve().parent.parent / "docs" / "needs"

# ── DOCX → MD ─────────────────────────────────────────────────
def docx_to_md(fp: Path) -> str:
    from docx import Document
    try:
        doc = Document(str(fp))
    except Exception:
        return f"[读取失败: {fp.name}]\n"
    
    lines = []
    title = fp.stem
    lines.append(f"# {title}\n")
    lines.append(f"> 来源: {fp.name} | 科室需求文档\n")
    lines.append("")
    
    for para in doc.paragraphs:
        t = para.text.strip()
        if not t:
            lines.append("")
            continue
        style = para.style.name if para.style else ""
        if style and 'Heading' in style:
            level = re.search(r'\d+', style)
            lv = int(level.group()) if level else 2
            lines.append(f"{'#' * min(lv+1, 6)} {t}\n")
        elif re.match(r'^(第[一二三四五六七八九十\d]+[章节]|[一二三四五六七八九十]、|\d+[\.、])', t) and len(t) < 60:
            lines.append(f"## {t}\n")
        else:
            lines.append(f"{t}\n")
    
    return '\n'.join(lines)

# ── PDF → MD ──────────────────────────────────────────────────
def pdf_to_md(fp: Path) -> str:
    import pypdf
    try:
        reader = pypdf.PdfReader(str(fp))
    except Exception:
        return f"[读取失败: {fp.name}]\n"
    
    title = fp.stem
    lines = [f"# {title}\n", f"> 来源: {fp.name} | 科室需求文档 (PDF)\n", ""]
    
    for page in reader.pages:
        t = page.extract_text()
        if t:
            for line in t.split('\n'):
                line = line.strip()
                if line:
                    lines.append(f"{line}\n")
            lines.append("")
    
    return '\n'.join(lines)

def clean_text(s: str) -> str:
    """Remove surrogate characters that can't be UTF-8 encoded."""
    return ''.join(c if ord(c) < 0xD800 or ord(c) > 0xDFFF else '\ufffd' for c in s)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    files = sorted(NEDS_DIR.glob('*'))
    # Filter: only originals, not .mod or .md files
    originals = [f for f in files if f.suffix.lower() in ('.doc', '.docx', '.pdf') 
                 and '.mod.' not in f.name]

    if args.limit:
        originals = originals[:args.limit]

    total = len(originals)
    for idx, fp in enumerate(originals, 1):
        md_path = NEDS_DIR / (fp.stem + '.md')
        print(f"[{idx}/{total}] {fp.name} → {md_path.name}")
        
        suf = fp.suffix.lower()
        if suf in ('.docx', '.doc'):
            md = docx_to_md(fp)
        elif suf == '.pdf':
            md = pdf_to_md(fp)
        else:
            md = f"# {fp.stem}\n\n[不支持的格式]\n"
        
        md_path.write_text(clean_text(md), encoding='utf-8')
    
    print(f"\nDone. {total} markdown files → {NEDS_DIR}")

if __name__ == '__main__':
    main()
