"""OCR scanned PDFs using RapidOCR (ONNX-based, no GPU needed).
Renders PDF pages to images via pypdfium2, then OCRs each page.
"""
from pathlib import Path

import pypdfium2 as pdfium
from rapidocr_onnxruntime import RapidOCR

NEDS = Path(__file__).resolve().parent.parent / "docs" / "needs"
FAILED = ['A27', 'A44', 'A48', 'A77']

def clean(s):
    return ''.join(c if ord(c) < 0xD800 or ord(c) > 0xDFFF else '\ufffd' for c in s)

print("Loading RapidOCR model...")
ocr = RapidOCR()
print("Ready.\n")

for code in FAILED:
    matches = list(NEDS.glob(f"{code}-*.pdf"))
    if not matches:
        continue
    fp = matches[0]
    print(f"OCR: {fp.name}")
    
    pdf = pdfium.PdfDocument(str(fp))
    num_pages = min(len(pdf), 12)
    all_text = []
    
    for pg in range(num_pages):
        page = pdf[pg]
        bitmap = page.render(scale=2)
        pil_img = bitmap.to_pil()
        import numpy as np
        img_array = np.array(pil_img)
        result, elapse = ocr(img_array)
        if result is not None:
            lines = []
            for item in result:
                # RapidOCR returns: [bbox, text, confidence] for each item
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    t = item[1]
                    if isinstance(t, str) and t.strip():
                        lines.append(t.strip())
                elif isinstance(item, str) and item.strip():
                    lines.append(item.strip())
            text = '\n'.join(lines)
            all_text.append(text)
        pil_img.close()
    
    pdf.close()
    text = '\n'.join(all_text)
    
    if text.strip():
        dept = fp.stem.split('-')[1] if '-' in fp.stem and len(fp.stem.split('-')) > 1 else ""
        md = f"""# {fp.stem}

> **科室**: {dept or '未标注'} | **编号**: {code} | **来源**: {fp.name}

---

## 文档内容 (OCR 识别)

{text}

---

*由 minimax-pdf (RapidOCR + pypdfium2) 自动提取生成*
"""
        md_path = NEDS / (fp.stem + '.md')
        md_path.write_text(clean(md), encoding='utf-8')
        print(f"  -> {len(text)} chars ({num_pages} pages)")
    else:
        print("  -> FAILED (no text recognized)")

print("\nDone.")
