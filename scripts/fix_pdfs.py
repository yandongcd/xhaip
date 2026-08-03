"""Re-extract PDFs that failed — try pdfplumber first, then pypdf with layout mode."""
from pathlib import Path

NEDS = Path(__file__).resolve().parent.parent / "docs" / "needs"
FAILED = ['A27', 'A44', 'A48', 'A77', 'A4']  # + A4 which wasn't in the list

def clean(s):
    return ''.join(c if ord(c) < 0xD800 or ord(c) > 0xDFFF else '\ufffd' for c in s)

def extract_pdf(fp: Path) -> str:
    """Multi-engine PDF text extraction."""
    text = ""
    
    # 1. Try pdfplumber (best for structured PDFs)
    try:
        import pdfplumber
        with pdfplumber.open(str(fp)) as pdf:
            pages_text = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            text = '\n'.join(pages_text)
        if len(text.strip()) > 200:
            return f"[pdfplumber] {text}"
    except Exception as e:
        print(f"    pdfplumber: {e}")
    
    # 2. Try pypdf with layout extraction
    try:
        import pypdf
        reader = pypdf.PdfReader(str(fp))
        pages_text = []
        for page in reader.pages:
            t = page.extract_text(extraction_mode="layout")
            if t:
                pages_text.append(t)
        text = '\n'.join(pages_text)
        if len(text.strip()) > 200:
            return f"[pypdf-layout] {text}"
    except Exception as e:
        print(f"    pypdf-layout: {e}")

    # 3. Try standard pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(str(fp))
        pages_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t)
        text = '\n'.join(pages_text)
        if text.strip():
            return f"[pypdf] {text}"
    except Exception:
        pass
    
    return ""

for code in FAILED:
    matches = list(NEDS.glob(f"{code}-*.pdf"))
    if not matches:
        continue
    fp = matches[0]
    md_path = NEDS / (fp.stem + '.md')
    
    if md_path.exists() and md_path.stat().st_size > 2000:
        print(f"[SKIP] {fp.name} (already {md_path.stat().st_size} bytes)")
        continue
    
    print(f"Processing {fp.name}...")
    text = extract_pdf(fp)
    
    if text and len(text.strip()) > 100:
        dept = fp.stem.split('-')[1] if '-' in fp.stem and len(fp.stem.split('-')) > 1 else ""
        md = f"""# {fp.stem}

> **科室**: {dept or '未标注'} | **编号**: {code} | **来源**: {fp.name}

---

## 文档内容

{text}

---

*由 minimax-pdf (pdfplumber + pypdf) 自动提取生成*
"""
        md_path.write_text(clean(md), encoding='utf-8')
        print(f"  -> {md_path.name}: {len(text)} chars, {md_path.stat().st_size} bytes")
    else:
        print("  -> FAILED: no extractable text (likely scanned image PDF)")
        # Write note in md file
        md = f"""# {fp.stem}

> **科室**: 未标注 | **编号**: {code} | **来源**: {fp.name}

---

## ⚠️ 无法提取

此 PDF 为扫描件/图片型文件，无可提取的文本层。建议使用 OCR 工具处理。

---
"""
        md_path.write_text(clean(md), encoding='utf-8')
