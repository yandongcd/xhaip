"""Fix CSS syntax errors and clean up styles."""
import pathlib

p = pathlib.Path(r"D:\dst\projects\xhaip\packages\haip-core\haip\ui_process_css.py")
content = p.read_text(encoding="utf-8")

# Split into prefix, body, suffix
marker = 'PROCESS_CSS = """'
prefix_end = content.index(marker) + len(marker)
suffix_start = content.rindex('"""')
prefix = content[:prefix_end]
body = content[prefix_end:suffix_start]
suffix = content[suffix_start:]

# Fix @keyframes missing closing }
body = body.replace(
    "@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}",
    "@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}"
)
body = body.replace(
    "@keyframes spin{to{transform:rotate(360deg)}",
    "@keyframes spin{to{transform:rotate(360deg)}}"
)

# Remove inline concatenated duplicate triage rules
old_triage = (".triage-card.III{border-left-color:var(--green);background:var(--green-bg)}"
              ".triage-card.I{border-left:5px solid var(--red)}"
              ".triage-card.II{border-left:5px solid var(--amber)}"
              ".triage-card.III{border-left:5px solid var(--green)}"
              ".triage-card.IV{border-left:5px solid var(--blue)}")
new_triage = ".triage-card.III{border-left-color:var(--green);background:var(--green-bg)}"
body = body.replace(old_triage, new_triage)

# Redesign center column components
# Stage header: cleaner, no card wrapper
body = body.replace(
    ".stage-hdr{display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:14px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}",
    ".stage-hdr{display:flex;align-items:center;gap:16px;margin-bottom:24px;padding:0 0 16px 0;border-bottom:2px solid var(--border)}"
)
body = body.replace(
    '.stage-hdr .sh-num{width:32px;height:32px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;flex-shrink:0;box-shadow:0 2px 8px rgba(8,145,178,0.3)}',
    '.stage-hdr .sh-num{width:36px;height:36px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;flex-shrink:0}'
)
body = body.replace(
    '.stage-hdr h2{font-size:var(--fs-xl);font-weight:700;letter-spacing:-.02em}',
    '.stage-hdr h2{font-size:20px;font-weight:700;color:var(--text)}'
)
body = body.replace(
    '.stage-hdr .sh-role{font-size:var(--fs-sm);color:var(--text3);background:var(--bg-subtle);padding:3px 12px;border-radius:var(--radius-full);border:1px solid var(--border-muted)}',
    '.stage-hdr .sh-role{font-size:12px;color:var(--text3);background:var(--bg-subtle);padding:4px 14px;border-radius:var(--radius-full)}'
)

# Cards: cleaner, no shadow, bigger padding
body = body.replace(
    ".card{background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}",
    ".card{background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius);padding:24px;margin-bottom:16px}"
)
body = body.replace(
    ".card:hover{box-shadow:0 2px 8px rgba(0,0,0,0.08)}",
    ""
)
body = body.replace(
    ".card h3{font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px;display:flex;align-items:center;gap:8px}",
    ".card h3{font-size:15px;font-weight:700;color:var(--text);margin-bottom:14px;display:flex;align-items:center;gap:8px}"
)

# Sections: cleaner titles
body = body.replace(
    ".section-title{font-size:var(--fs-sm);font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);margin-bottom:8px}",
    ".section-title{font-size:13px;font-weight:700;color:var(--accent);margin-bottom:10px}"
)
body = body.replace(
    ".summary-bar{background:var(--bg-default);border:1px solid var(--border-muted);border-radius:var(--radius-sm);padding:14px 18px;display:flex;flex-wrap:wrap;gap:6px 16px;font-size:var(--fs-base);line-height:1.8;color:var(--text)}",
    ".summary-bar{background:var(--bg-overlay);border-radius:var(--radius-sm);padding:16px 20px;font-size:14px;line-height:2;color:var(--text)}"
)

# Tabs: proper tab bar style
body = body.replace(
    ".tabs{display:flex;gap:4px;margin-bottom:10px;flex-wrap:wrap}",
    ".tabs{display:flex;gap:0;margin-bottom:0;border-bottom:2px solid var(--border)}"
)
body = body.replace(
    ".tab-btn{padding:8px 20px;font-size:13px;color:var(--text2);background:transparent;border:none;border-bottom:3px solid transparent;cursor:pointer;transition:all .2s;font-family:inherit;font-weight:500;border-radius:0}",
    ".tab-btn{padding:10px 24px;font-size:14px;color:var(--text3);background:transparent;border:none;border-bottom:2px solid transparent;margin-bottom:-2px;cursor:pointer;transition:all .2s;font-family:inherit;font-weight:500}"
)
body = body.replace(
    ".tab-btn:hover{color:var(--accent);border-bottom-color:var(--border)}",
    ".tab-btn:hover{color:var(--accent);background:var(--bg-subtle)}"
)
body = body.replace(
    ".tab-btn.active{color:var(--accent);border-bottom-color:var(--accent);font-weight:700}",
    ".tab-btn.active{color:var(--accent);border-bottom-color:var(--accent);font-weight:700}"
)
body = body.replace(
    ".tab-pane{display:none;animation:fadeIn .25s ease}",
    ".tab-pane{display:none;padding:20px 0 0 0;animation:fadeIn .25s ease}"
)

# Alert: bigger, better borders
body = body.replace(
    ".alert{border-radius:var(--radius);padding:10px 14px;font-size:12px;line-height:1.5;margin-top:6px}",
    ".alert{border-radius:var(--radius-sm);padding:12px 16px;font-size:13px;line-height:1.6;margin-top:12px}"
)

# Triage: cleaner
body = body.replace(
    ".triage-card{border-radius:var(--radius);padding:12px 16px;border-left:4px solid var(--blue);background:var(--bg-elevated);border-top:1px solid var(--border);border-right:1px solid var(--border);border-bottom:1px solid var(--border)}",
    ".triage-card{border-radius:var(--radius);padding:16px 20px;margin-top:12px;border-left:4px solid var(--border);background:var(--bg-elevated)}"
)
body = body.replace(
    ".triage-sub{font-size:12px;color:var(--text2);margin-top:3px}",
    ".triage-sub{font-size:13px;color:var(--text2);margin-top:4px}"
)

p.write_text(prefix + body + suffix, encoding="utf-8")
print("All CSS fixes applied")
