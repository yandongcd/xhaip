"""EA Visual Templates — Shared CSS variable framework.

All templates use CSS variables for theming.
Each consumer customizes colors by passing a theme dict:
  theme = {"--primary": "#2e86c1", "--bg": "#0a0a0f", ...}

Templates return HTML fragments by default; use wrap_html() for full pages.
"""

from __future__ import annotations

DEFAULT_THEME: dict[str, str] = {
    "--primary": "#1565c0",
    "--primary-bg": "rgba(21,101,192,0.08)",
    "--secondary": "#e65100",
    "--secondary-bg": "rgba(230,81,0,0.08)",
    "--bg": "#f8f9fc",
    "--card-bg": "#ffffff",
    "--card-border": "#eef0f4",
    "--text": "#1a1a2e",
    "--text-secondary": "#5c6a7a",
    "--text-muted": "#8e99a9",
    "--danger": "#e74c3c",
    "--danger-bg": "rgba(231,76,60,0.08)",
    "--warning": "#ff9f0a",
    "--warning-bg": "rgba(255,159,10,0.08)",
    "--success": "#27ae60",
    "--success-bg": "rgba(39,174,96,0.08)",
    "--info": "#3498db",
    "--info-bg": "rgba(52,152,219,0.08)",
    "--radius": "8px",
    "--radius-sm": "4px",
    "--shadow": "0 1px 3px rgba(0,0,0,0.06)",
    "--font": "-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif",
    "--font-size": "13px",
    "--font-size-sm": "11px",
    "--font-size-lg": "16px",
}

SHARED_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: var(--font);
    font-size: var(--font-size);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}
.lx-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius);
    padding: 16px 20px;
    margin-bottom: 12px;
}
.lx-card-title {
    font-size: var(--font-size-lg);
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--text);
}
.lx-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: var(--font-size-sm);
    font-weight: 500;
}
.lx-badge.primary { background: var(--primary-bg); color: var(--primary); }
.lx-badge.secondary { background: var(--secondary-bg); color: var(--secondary); }
.lx-badge.danger { background: var(--danger-bg); color: var(--danger); }
.lx-badge.warning { background: var(--warning-bg); color: var(--warning); }
.lx-badge.success { background: var(--success-bg); color: var(--success); }
.lx-badge.info { background: var(--info-bg); color: var(--info); }
.lx-table { width: 100%; border-collapse: collapse; font-size: var(--font-size); }
.lx-table th {
    background: var(--bg);
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    color: var(--text-secondary);
    border-bottom: 2px solid var(--card-border);
}
.lx-table td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--card-border);
}
.lx-footer {
    padding: 8px 20px;
    font-size: var(--font-size-sm);
    color: var(--text-muted);
    border-top: 1px solid var(--card-border);
    margin-top: 16px;
}
"""


def build_theme_css(theme: dict[str, str] | None = None) -> str:
    """Build :root CSS block from theme dict."""
    merged = dict(DEFAULT_THEME)
    if theme:
        merged.update(theme)
    variables = ";".join(f"{k}:{v}" for k, v in sorted(merged.items()))
    return f":root{{{variables}}}"


def wrap_html(title: str, body: str, theme: dict[str, str] | None = None) -> str:
    """Wrap body content in a full HTML page with shared CSS + theme."""
    theme_css = build_theme_css(theme)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} · EA Templates</title>
<style>{theme_css}{SHARED_CSS}</style>
</head>
<body>
{body}
</body>
</html>"""
