"""OCR scanned PDFs using Windows.Media.OCR (built-in, no external tools).
Converts PDF pages to images via pypdfium2, then OCR via PowerShell WinRT bridge.
"""
import subprocess
import tempfile
from pathlib import Path

import pypdfium2 as pdfium

NEDS = Path(__file__).resolve().parent.parent / "docs" / "needs"
FAILED = ['A27', 'A44', 'A48', 'A77']

def clean(s):
    return ''.join(c if ord(c) < 0xD800 or ord(c) > 0xDFFF else '\ufffd' for c in s)

def pdf_page_to_png(pdf_path: Path, page_num: int, output_png: Path):
    """Render a single PDF page to PNG using pypdfium2."""
    pdf = pdfium.PdfDocument(str(pdf_path))
    page = pdf[page_num]
    bitmap = page.render(scale=2)  # 2x for better OCR
    pil_img = bitmap.to_pil()
    pil_img.save(str(output_png), 'PNG')
    pdf.close()

def ocr_with_windows(png_path: Path) -> str:
    """Use Windows.Media.OCR to extract text from image via PowerShell."""
    ps_script = f'''
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime]
$task = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync(
    [Windows.Storage.Streams.IRandomAccessStream][Windows.Storage.Streams.RandomAccessStreamReference]::CreateFromFile(
        [Windows.Storage.StorageFile]::GetFileFromPathAsync("{png_path.as_posix()}").GetAwaiter().GetResult()
    ).OpenReadAsync().GetAwaiter().GetResult()
).GetAwaiter().GetResult()
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$ocrResult = $engine.Result.RecognizeAsync(
    [Windows.Graphics.Imaging.SoftwareBitmap]::CreateCopyFromBuffer(
        (await [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync(
            [Windows.Storage.Streams.IRandomAccessStream](New-Object Windows.Storage.Streams.InMemoryRandomAccessStream)
        ))
    )
)
$ocrResult.GetAwaiter().GetResult().Text
'''
    # Simpler PowerShell approach: use System.Drawing + Windows OCR
    ps_simple = f'''
[Reflection.Assembly]::LoadWithPartialName("System.Drawing") | Out-Null
$img = [System.Drawing.Image]::FromFile("{png_path.as_posix()}")
$ms = New-Object System.IO.MemoryStream
$img.Save($ms, [System.Drawing.Imaging.ImageFormat]::Bmp)
$ms.Position = 0
$decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync(
    [Windows.Storage.Streams.IRandomAccessStream]$ms
).GetAwaiter().GetResult()
$bitmap = [Windows.Graphics.Imaging.SoftwareBitmap]::Convert(
    (await $decoder.GetSoftwareBitmapAsync()),
    [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
    [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied
)
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$result = (await $engine.Result.RecognizeAsync($bitmap))
$result.Text
'''
    return ""

# Simpler: just use a cmdlet approach
def ocr_png_file(png_path: Path) -> str:
    """Use Windows OCR via a simpler Python winrt approach."""
    try:
        # Try direct PowerShell call with simplest possible script
        ps_code = f'''
$file = [Windows.Storage.StorageFile]::GetFileFromPathAsync("{png_path.as_posix()}").GetAwaiter().GetResult()
$stream = [Windows.Storage.Streams.RandomAccessStreamReference]::CreateFromFile($file)
$decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream).AsTask().Result
$bitmap = [Windows.Graphics.Imaging.SoftwareBitmap]::Convert($decoder.GetSoftwareBitmapAsync().AsTask().Result, [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8)
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$ocr = $engine.Result.RecognizeAsync($bitmap).AsTask().Result
$ocr.Text
'''
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', 
             f'Add-Type -AssemblyName System.Runtime.WindowsRuntime; [Windows.Media.Ocr.OcrEngine,Windows.Media.Ocr,ContentType=WindowsRuntime]|Out-Null; {ps_code}'],
            capture_output=True, text=True, timeout=60
        )
        if result.stdout.strip():
            return result.stdout.strip()
        if result.stderr.strip():
            print(f"    PS stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"    OCR error: {e}")
    return ""


for code in FAILED:
    matches = list(NEDS.glob(f"{code}-*.pdf"))
    if not matches:
        continue
    fp = matches[0]
    
    print(f"OCR: {fp.name}...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        all_text = []
        
        try:
            pdf = pdfium.PdfDocument(str(fp))
            num_pages = min(len(pdf), 10)  # Max 10 pages
            pdf.close()
            
            for pg in range(num_pages):
                png_path = tmp / f"page_{pg:03d}.png"
                print(f"  Page {pg+1}/{num_pages}...")
                pdf_page_to_png(fp, pg, png_path)
                text = ocr_png_file(png_path)
                if text and text.strip():
                    all_text.append(text)
        except Exception as e:
            print(f"  Error: {e}")
        
        text = '\n'.join(all_text)
    
    if text.strip():
        dept = fp.stem.split('-')[1] if '-' in fp.stem and len(fp.stem.split('-')) > 1 else ""
        md = f"""# {fp.stem}

> **科室**: {dept or '未标注'} | **编号**: {code} | **来源**: {fp.name}

---

## 文档内容 (OCR 识别)

{text}

---

*由 minimax-pdf (Windows OCR + pypdfium2) 自动提取生成*
"""
        md_path = NEDS / (fp.stem + '.md')
        md_path.write_text(clean(md), encoding='utf-8')
        print(f"  -> {len(text)} chars, {md_path.stat().st_size} bytes")
    else:
        print("  -> FAILED: could not OCR")
