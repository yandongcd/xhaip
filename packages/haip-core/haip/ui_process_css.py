"""Generated CSS for ui_process ? extracted from ui_process.py."""

PROCESS_CSS = """/* ═══════════════════════════════════════════════
   Gold Standard Design System
   Ref: orthopedic_surgery.html (haip-0705-2)
   ═══════════════════════════════════════════════ */
:root{{
  --bg-default:#ffffff;--bg-overlay:#f6f8fa;--bg-inset:#f0f3f6;
  --bg-subtle:#e8ecf0;--bg-elevated:#ffffff;--border:#d0d7de;
  --border-muted:#e1e5ea;--text:#1f2328;--text2:#656d76;
  --text3:#8b949e;--accent:#0969da;--accent-hover:#0550ae;

  --red:#cf222e;--red-bg:rgba(207,34,46,0.10);
  --blue:#0969da;--blue-bg:rgba(9,105,218,0.10);
  --green:#1a7f37;--green-bg:rgba(26,127,55,0.10);
  --amber:#8b6914;--amber-bg:rgba(139,105,20,0.10);
  --purple:#6e5494;--purple-bg:rgba(110,84,148,0.10);
  --radius:8px;--radius-sm:6px;--radius-full:999px;
  --shadow-sm:0 1px 3px rgba(0,0,0,0.06);
  --shadow-md:0 4px 12px rgba(0,0,0,0.08);
  --fs-sm:12px;--fs-base:14px;--fs-lg:16px;--fs-xl:20px;
  --h:52px;
}}
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
html{{font-size:16px;-webkit-font-smoothing:antialiased}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',Arial,sans-serif;background:var(--bg-default);color:var(--text);min-height:100vh;font-size:14px;line-height:1.47;display:flex;flex-direction:column}}

/* ── Header ── */
.header{{flex-shrink:0;z-index:1000;background:var(--bg-elevated);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;height:var(--h);gap:12px}}
.header-logo{{font-size:16px;font-weight:700;color:var(--accent);cursor:pointer;display:flex;align-items:center;gap:6px}}
.header-logo span{{font-weight:400;font-size:12px;color:var(--text2);margin-left:4px}}
.header-role{{display:flex;gap:4px;margin-left:12px}}
.role-pill{{background:transparent;border:1px solid var(--border);border-radius:var(--radius-full);padding:3px 12px;font-size:12px;cursor:pointer;transition:all .2s;color:var(--text2);font-family:inherit}}
.role-pill:hover{{border-color:var(--accent);color:var(--text)}}
.role-pill.active{{background:var(--accent);border-color:var(--accent);color:#fff}}
.header-patient{{margin-left:auto;font-size:13px;color:var(--text2);display:none;align-items:center;gap:8px}}
.header-patient.visible{{display:flex}}
.header-patient .hp-name{{font-weight:600;color:var(--text)}}
.header-patient .hp-badge{{font-size:10px;padding:1px 8px;border-radius:var(--radius-full);background:var(--blue-bg);color:var(--blue);white-space:nowrap}}

/* ── Hamburger Menu ── */
.menu-overlay{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);z-index:2000;display:none}}
.menu-overlay.open{{display:block}}
.menu-panel{{position:fixed;top:0;left:0;width:280px;height:100%;background:var(--bg-elevated);border-right:1px solid var(--border);z-index:2001;transform:translateX(-100%);transition:transform .2s ease;display:flex;flex-direction:column}}
.menu-panel.open{{transform:translateX(0)}}
.menu-header{{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid var(--border-muted)}}
.menu-header .close-btn{{width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:var(--radius-sm);cursor:pointer;color:var(--text2);border:none;background:none;font-size:18px;font-family:inherit}}
.menu-header .close-btn:hover{{background:var(--bg-subtle)}}
.menu-items{{flex:1;overflow-y:auto;padding:8px 0}}
.menu-item{{display:flex;align-items:center;gap:10px;padding:9px 16px;cursor:pointer;color:var(--text2);font-size:13px;transition:all .15s;border:none;background:none;width:100%;text-align:left;font-family:inherit}}
.menu-item:hover{{background:var(--bg-subtle);color:var(--text)}}
.menu-item .mi-icon{{font-size:15px;width:22px;text-align:center}}
.menu-item.active{{background:var(--blue-bg);color:var(--blue);border-left:2px solid var(--blue)}}
.menu-divider{{height:1px;background:var(--border-muted);margin:4px 12px}}
.page-panel{{display:none;padding:16px 24px;overflow-y:auto;flex:1}}
.page-panel h2{{font-size:18px;font-weight:600;margin-bottom:12px}}

/* ── 3-Column Layout ── */
.app{{display:flex;flex:1;min-height:0}}
  .leftbar{{width:260px;flex-shrink:0;border-right:1px solid var(--border-muted);background:var(--bg-overlay);display:flex;flex-direction:column;overflow:hidden}}
.lb-search{{padding:10px 12px;border-bottom:1px solid var(--border-muted)}}
.lb-search input{{width:100%;padding:6px 10px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius-full);font-size:12px;outline:none;font-family:inherit;color:var(--text)}}
.lb-search input:focus{{border-color:var(--blue)}}
.lb-header{{padding:8px 12px 4px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text3)}}
.patient-list{{flex:1;overflow-y:auto}}
.p-item{{padding:10px 12px;border-bottom:1px solid var(--border-muted);cursor:pointer;transition:all .15s;font-size:13px}}
.p-item:hover{{background:var(--blue-bg)}}
.p-item.active{{background:var(--blue-bg);border-left:3px solid var(--accent)}}
.p-item .p-name{{font-weight:500;display:flex;align-items:center;gap:6px}}
.p-item .p-name .p-age{{font-weight:400;color:var(--text2);font-size:12px}}
.p-item .p-diag{{font-size:11px;color:var(--text2);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.p-item .p-meta{{font-size:10px;color:var(--text3);margin-top:2px;display:flex;align-items:center;gap:6px}}
.p-item .p-stage{{font-size:9px;padding:1px 6px;border-radius:var(--radius-full);font-weight:500}}
.p-stage.urgent{{background:var(--red-bg);color:var(--red)}}
.p-stage.normal{{background:var(--blue-bg);color:var(--blue)}}
.lb-footer{{padding:8px 12px;font-size:10px;color:var(--text3);border-top:1px solid var(--border-muted);text-align:center}}

.center{{flex:1;overflow-y:auto;background:var(--bg-default);padding:20px 24px}}

.rightbar{{width:200px;flex-shrink:0;border-left:1px solid var(--border-muted);background:var(--bg-overlay);display:flex;flex-direction:column;padding:12px}}
.rb-title{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.3px;color:var(--text3);margin-bottom:8px}}
.rb-list{{flex:1;overflow-y:auto}}
.rb-item{{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:var(--radius-sm);transition:all .15s;font-size:var(--fs-sm);cursor:pointer}}
.rb-item:hover{{background:var(--bg-subtle)}}
.rb-item.active{{background:var(--blue-bg)}}
.rb-item .rb-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;border:2px solid var(--border-muted);transition:all .2s}}
.rb-item .rb-dot.done{{background:var(--green);border-color:var(--green);box-shadow:0 0 0 3px var(--green-bg)}}
.rb-item .rb-dot.current{{background:var(--accent);border-color:var(--accent);box-shadow:0 0 0 3px var(--blue-bg)}}
.rb-item .rb-dot.locked{{border-color:var(--border-muted)}}
.rb-info{{flex:1;min-width:0}}
.rb-item .rb-name{{font-weight:500;font-size:12px}}
.rb-item .rb-status{{font-size:9px;padding:1px 6px;border-radius:var(--radius-full);margin-left:auto}}
.rb-item .rb-status.done{{background:var(--green-bg);color:var(--green)}}
.rb-item .rb-status.active-s{{background:var(--blue-bg);color:var(--blue)}}
.rb-stats{{margin-top:12px;padding-top:8px;border-top:1px solid var(--border-muted)}}

/* ── Stage Content ── */
.stage-content{{display:none;animation:fadeIn .25s ease}}
.stage-content.active{{display:block}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.stage-hdr{{display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-muted)}}
.stage-hdr .sh-num{{width:28px;height:28px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;flex-shrink:0}}
.stage-hdr h2{{font-size:var(--fs-lg);font-weight:600;letter-spacing:-.02em}}
.stage-hdr .sh-role{{font-size:var(--fs-sm);color:var(--text3);background:var(--bg-subtle);padding:2px 10px;border-radius:var(--radius-full)}}
.stage-hdr .sh-desc{{font-size:var(--fs-sm);color:var(--text2);margin-top:2px}}

/* ── Cards ── */
.card{{background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}}
.card h3{{font-size:13px;font-weight:600;color:var(--text);margin-bottom:8px;display:flex;align-items:center;gap:6px}}
.card h3 .ch-icon{{font-size:16px}}
.card h4{{font-size:13px;font-weight:600;margin-bottom:6px}}

/* ── KPI Grid ── */
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:12px}}
.kpi{{background:var(--bg-subtle);border:1px solid var(--border-muted);border-radius:var(--radius);padding:12px 10px;text-align:center;transition:box-shadow .2s,transform .2s}}
.kpi:hover{{box-shadow:0 4px 12px rgba(0,0,0,.08);transform:translateY(-1px)}}
.kpi .val{{font-size:24px;font-weight:700;display:block;letter-spacing:-.02em;font-variant-numeric:tabular-nums}}
.kpi .val.blue{{color:var(--blue)}}.kpi .val.red{{color:var(--red)}}.kpi .val.green{{color:var(--green)}}.kpi .val.amber{{color:var(--amber)}}
.kpi .lbl{{font-size:10px;color:var(--text3);margin-top:2px;text-transform:uppercase;letter-spacing:.04em}}

/* ── Sections ── */
.section{{margin-bottom:14px}}
.section-title{{font-size:var(--fs-sm);font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);margin-bottom:8px}}
.summary-bar{{background:var(--bg-overlay);border:1px solid var(--border-muted);border-radius:var(--radius-sm);padding:12px 16px;display:flex;flex-wrap:wrap;gap:4px 12px;font-size:var(--fs-base);line-height:1.7}}
.dp{{display:flex;padding:4px 0;border-bottom:1px solid var(--border-muted);line-height:1.6}}
.dp:last-child{{border-bottom:none}}
.dpl{{width:72px;flex-shrink:0;color:var(--text3);font-size:var(--fs-sm);font-weight:500}}
.dpv{{color:var(--text);font-size:var(--fs-base);font-weight:500}}

/* ── Tabs ── */
.tabs{{display:flex;gap:4px;margin-bottom:10px;flex-wrap:wrap}}
.tab-btn{{background:transparent;border:1px solid var(--border);border-radius:var(--radius-full);padding:4px 14px;font-size:11px;cursor:pointer;transition:all .2s;color:var(--text2);font-family:inherit;white-space:nowrap}}
.tab-btn:hover{{border-color:var(--accent);color:var(--text)}}
.tab-btn.active{{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:500}}
.tab-pane{{display:none;animation:fadeIn .25s ease}}
.tab-pane.active{{display:block}}

/* ── Triage Card ── */
.triage-card{{border-radius:var(--radius);padding:12px 16px;border-left:4px solid var(--blue);background:var(--bg-elevated);border-top:1px solid var(--border);border-right:1px solid var(--border);border-bottom:1px solid var(--border)}}
.triage-card.I{{border-left-color:var(--red);background:var(--red-bg)}}
.triage-card.II{{border-left-color:var(--amber);background:var(--amber-bg)}}
.triage-card.III{{border-left-color:var(--green);background:var(--green-bg)}}
.triage-card.IV{{border-left-color:var(--blue);background:var(--blue-bg)}}
.triage-main{{font-size:18px;font-weight:700}}
.triage-sub{{font-size:12px;color:var(--text2);margin-top:3px}}
.tri-i{{color:var(--red)}}.tri-ii{{color:var(--amber)}}.tri-iii{{color:var(--green)}}.tri-iv{{color:var(--blue)}}

/* ── Tags ── */
.tag{{display:inline-block;padding:2px 8px;border-radius:var(--radius-full);font-size:var(--fs-sm);font-weight:500}}
.tag.blue{{background:var(--blue-bg);color:var(--blue)}}
.tag.red{{background:var(--red-bg);color:var(--red)}}
.tag.green{{background:var(--green-bg);color:var(--green)}}
.tag.amber{{background:var(--amber-bg);color:var(--amber)}}
.tag.purple{{background:var(--purple-bg);color:var(--purple)}}

/* ── Alerts ── */
.alert{{border-radius:var(--radius);padding:10px 14px;font-size:12px;line-height:1.5;margin-top:6px}}
.alert.red{{background:var(--red-bg);border:1px solid rgba(207,34,46,.25);color:var(--red)}}
.alert.blue{{background:var(--blue-bg);border:1px solid rgba(9,105,218,.25);color:var(--blue)}}
.alert.green{{background:var(--green-bg);border:1px solid rgba(26,127,55,.25);color:var(--green)}}
.alert.amber{{background:var(--amber-bg);border:1px solid rgba(139,105,20,.25);color:var(--amber)}}

/* ── Buttons ── */
.btn{{background:var(--accent);color:#fff;border:none;border-radius:var(--radius-full);padding:6px 16px;font-size:12px;font-weight:500;cursor:pointer;transition:all .15s;font-family:inherit;display:inline-flex;align-items:center;gap:4px}}
.btn:hover{{background:var(--accent-hover);box-shadow:0 4px 12px rgba(9,105,218,.25)}}
.btn:active{{transform:scale(.96)}}
.btn-outline{{background:transparent;border:1px solid var(--border);color:var(--text)}}
.btn-outline:hover{{background:var(--bg-subtle)}}
.btn-sm{{padding:4px 12px;font-size:11px}}
.btn-success{{background:var(--green);color:#fff}}
.fx-nav{{display:flex;justify-content:space-between;margin-top:16px;padding-top:12px;border-top:1px solid var(--border-muted)}}

/* ── Table ── */
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:var(--bg-overlay);padding:8px 10px;text-align:left;font-weight:500;color:var(--text2);border-bottom:1px solid var(--border);text-transform:uppercase;letter-spacing:.03em;font-size:11px}}
td{{padding:6px 10px;border-bottom:1px solid var(--border-muted)}}
tr:hover td{{background:var(--bg-overlay)}}

/* ── Checklist ── */
.cl-section{{margin-bottom:12px}}
.cl-section-title{{font-size:var(--fs-sm);font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.3px;margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid var(--border-muted)}}
.cl-item{{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:var(--radius-sm);font-size:var(--fs-base);border-bottom:1px solid var(--border-muted)}}
.cl-item:last-child{{border-bottom:none}}
.cl-item .ck{{width:16px;height:16px;border-radius:3px;border:2px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:10px;flex-shrink:0}}
.cl-item .ck.done{{background:var(--green);border-color:var(--green);color:#fff}}
.cl-item .cl-name{{font-weight:500;flex-shrink:0;min-width:90px}}
.cl-item .cl-dept{{font-size:10px;padding:1px 6px;border-radius:var(--radius-full);background:var(--blue-bg);color:var(--blue);margin-left:4px}}
.cl-item .cl-reason{{font-size:11px;color:var(--text3);margin-left:auto}}

/* ── Stage Bar ── */
.stage-bar{{height:3px;background:var(--accent);border-radius:2px;margin-bottom:16px;opacity:.3;transition:all .3s;width:0%}}
.stage-bar.s1{{background:var(--blue)}}.stage-bar.s2{{background:var(--green)}}
.stage-bar.s3{{background:var(--amber)}}.stage-bar.s4{{background:var(--red)}}
.stage-bar.s5{{background:var(--purple)}}.stage-bar.s6{{background:var(--blue)}}
.stage-bar.s7{{background:var(--green)}}.stage-bar.s8{{background:var(--red)}}

/* ── Followup Timeline ── */
.fu-timeline{{display:flex;justify-content:space-between;align-items:flex-start;position:relative;padding:12px 0;margin:8px 0}}
.fu-timeline::before{{content:'';position:absolute;top:10px;left:40px;right:40px;height:2px;background:var(--border)}}
.fu-node{{display:flex;flex-direction:column;align-items:center;gap:4px;position:relative;z-index:1;flex:1;text-align:center}}
.fu-dot{{width:14px;height:14px;border-radius:50%;background:var(--accent);border:3px solid var(--bg-elevated);box-shadow:0 0 0 2px var(--accent);flex-shrink:0}}
.fu-label{{font-size:13px;font-weight:600;color:var(--text)}}
.fu-sub{{font-size:10px;color:var(--text2)}}

/* ── Empty / Loading ── */
.empty{{text-align:center;padding:60px 20px;color:var(--text3)}}
.empty .e-icon{{font-size:48px;margin-bottom:12px}}
.empty .e-text{{font-size:14px;margin-bottom:4px}}
.empty .e-sub{{font-size:12px}}
.loading{{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text2)}}
.loading::before{{content:'';width:12px;height:12px;border:2px solid var(--border-muted);border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}

/* ── Toast ── */
.toast{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--text);color:var(--bg-default);padding:8px 20px;border-radius:var(--radius-full);font-size:13px;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,.2);display:none}}

/* ── Scrollbar ── */
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:transparent}}::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}

/* ── Responsive ── */
@media(max-width:900px){{.leftbar,.rightbar{{display:none}}.center{{width:100%}}.header{{flex-wrap:wrap;height:auto;padding:6px 10px}}.header-role{{margin-left:0;margin-top:4px}}}}"""
