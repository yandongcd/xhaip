"""Fix double curly braces in PROCESS_CSS and PROCESS_JS."""
import pathlib

base = pathlib.Path(r"D:\dst\projects\xhaip\packages\haip-core\haip")

for fname in ["ui_process_css.py"]:
    p = base / fname
    content = p.read_text(encoding="utf-8")
    prefix, sep, css = content.partition('= """')
    if not css:
        print(f"{fname}: no triple-quote found")
        continue
    suffix_at = css.rfind('"""')
    body = css[:suffix_at]
    tail = css[suffix_at:]
    body = body.replace("{{", "{").replace("}}", "}")
    new_content = prefix + '= """' + body + tail
    p.write_text(new_content, encoding="utf-8")
    print(f"{fname}: OK ({len(body)} chars)")
