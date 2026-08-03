"""Extract text from old binary .doc using COM (correct extension)."""
import re
import shutil
from pathlib import Path

fp = Path(__file__).resolve().parent.parent / "docs" / "needs" / "A1-病理科-病理报告智能解读系统.docx"
fp_renamed = fp.with_suffix('.doc')
out_md = fp.with_suffix('.md')

# Rename so Word can open it
if not fp_renamed.exists():
    shutil.copy2(fp, fp_renamed)

try:
    import win32com.client
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(str(fp_renamed))
    text = doc.Content.Text
    doc.Close()
    word.Quit()
    
    def clean(s):
        return ''.join(c if ord(c) < 0xD800 or ord(c) > 0xDFFF else '\ufffd' for c in s)
    
    text = clean(text)
    print(f"Extracted {len(text)} chars")
    
    md = f"""# A1-病理科-病理报告智能解读系统

> **科室**: 病理科 | **编号**: A1 | **来源**: A1-病理科-病理报告智能解读系统.doc

---

## 文档内容

{text}

---

*由 minimax-docx (COM Word) 自动提取生成*
"""
    out_md.write_text(md, encoding='utf-8')
    print(f"Saved: {len(text)} chars to {out_md.name}")

except Exception as e:
    print(f"Failed: {e}")
    # Fallback: try reading raw text from WordDocument stream
    import olefile
    ole = olefile.OleFileIO(str(fp))
    wd = ole.openstream('WordDocument').read()
    # Skip binary header, look for readable text
    text = ''
    for i in range(0x200, len(wd)-1, 2):
        if i+1 < len(wd):
            b1, b2 = wd[i], wd[i+1]
            if b1 == 0 and 0x20 <= b2 < 0x7F:
                text += chr(b2)
            elif 0x20 <= b1 < 0xFF and b2 == 0:
                text += chr(b1)
            elif b1 == 0 and b2 == 0:
                text += '\n'
    # Clean
    text = re.sub(r'\x00+', '\n', text)
    text = re.sub(r'\n{4,}', '\n\n', text)
    print(f"Fallback extracted {len(text)} chars")
    if text.strip():
        md = f"""# A1-病理科-病理报告智能解读系统

> **科室**: 病理科 | **编号**: A1

---

{text}
"""
        out_md.write_text(md, encoding='utf-8')
