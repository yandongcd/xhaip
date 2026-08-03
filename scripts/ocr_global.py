"""Global OCR CLI — convert PDF/image to text using RapidOCR.
Usage: py -m scripts.ocr_global <file> [--output result.txt]
"""
import argparse
import sys
from pathlib import Path


def ocr_image(img_path: str) -> str:
    import numpy as np
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    with Image.open(img_path) as pil_img:
        arr = np.array(pil_img.convert('RGB'))
    result, _ = ocr(arr)
    if not result:
        return ""
    return '\n'.join(item[1] for item in result if isinstance(item[1], str) and item[1].strip())

def ocr_pdf(pdf_path: str) -> str:
    import numpy as np
    import pypdfium2 as pdfium
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    pdf = pdfium.PdfDocument(pdf_path)
    all_text = []
    for pg in range(min(len(pdf), 50)):
        page = pdf[pg]
        bitmap = page.render(scale=2)
        arr = np.array(bitmap.to_pil().convert('RGB'))
        result, _ = ocr(arr)
        if result:
            ts = '\n'.join(item[1] for item in result if isinstance(item[1], str) and item[1].strip())
            if ts.strip():
                all_text.append(ts)
    pdf.close()
    return '\n\n'.join(all_text)

def main():
    p = argparse.ArgumentParser(description='OCR PDF/Image → Text (RapidOCR)')
    p.add_argument('file', help='Input file (.pdf, .png, .jpg)')
    p.add_argument('-o', '--output', help='Output file (default: stdout)')
    args = p.parse_args()
    fp = Path(args.file)
    if not fp.exists():
        print(f"ERROR: {fp} not found", file=sys.stderr)
        sys.exit(1)
    suf = fp.suffix.lower()
    print(f"OCR: {fp.name}...", file=sys.stderr)
    if suf == '.pdf':
        text = ocr_pdf(str(fp))
    elif suf in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'):
        text = ocr_image(str(fp))
    else:
        print(f"Unsupported: {suf}", file=sys.stderr)
        sys.exit(1)
    if args.output:
        Path(args.output).write_text(text, encoding='utf-8')
        print(f"Saved: {args.output} ({len(text)} chars)", file=sys.stderr)
    else:
        print(text)

if __name__ == '__main__':
    main()
