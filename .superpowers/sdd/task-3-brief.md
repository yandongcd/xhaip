## Task 3: 鏋勫缓闂ㄦ埛 HTML 鈥?甯冨眬涓庤璁′护鐗?
**Files:**
- Modify: `packages/haip-core/haip/ui_ortho_portal.html` (鏁翠綋濉厖)
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: `/ortho-portal` 璺敱 (Task 2)銆?- Produces: HTML 鍚互涓嬬ǔ瀹氶敋鐐?id/class锛屼緵娴嬭瘯涓庡悗缁?JS 浣跨敤锛?  - `#kpi-bar`锛圞PI 瀹瑰櫒锛夈€乣#patient-list`锛堟偅鑰呴槦鍒楋級銆乣#capability-grid`锛堣兘鍔涘崱缃戞牸锛夈€乣#result-panel`锛堝彸渚х粨鏋滈潰鏉匡級銆乣#stage-timeline`锛?1 闃舵鏃堕棿杞达級銆乣#theme-toggle`锛堜富棰樺垏鎹㈡寜閽級銆?
- [ ] **Step 1: 鍐欏竷灞€閿氱偣瀛樺湪鎬х殑澶辫触娴嬭瘯**

鍦?`test_ortho_portal.py` 杩藉姞锛?
```python
class TestPortalLayout:
    def _body(self):
        return client.get("/ortho-portal").text

    def test_has_layout_anchors(self):
        body = self._body()
        for anchor in ["kpi-bar", "patient-list", "capability-grid",
                       "result-panel", "stage-timeline", "theme-toggle"]:
            assert anchor in body, f"缂洪敋鐐?{anchor}"

    def test_has_title_and_tokens(self):
        body = self._body()
        assert "鍒涗激楠ㄧ" in body
        assert "--accent" in body  # 澶嶇敤 ui_ortho 璁捐浠ょ墝
        assert "body.light" in body  # 娴呰壊妯″紡
```

- [ ] **Step 2: 杩愯纭澶辫触**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalLayout -q`
Expected: FAIL锛堥鏋舵棤杩欎簺閿氱偣锛夈€?
- [ ] **Step 3: 鍐欏畬鏁?HTML 甯冨眬锛堝惈 CSS 浠ょ墝 + 闈欐€佺粨鏋勶級**

灏?`ui_ortho_portal.html` 鍏ㄦ枃鏇挎崲涓轰笅杩板唴瀹癸紙CSS 澶嶇敤 ui_ortho 浠ょ墝锛汮S 閫昏緫鍦?Task 4/5 濉厖锛屾湰姝ュ厛鏀鹃潤鎬侀鏋朵笌绌?`<script>` 鍗犱綅锛夛細

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xhaip 鈥?鍒涗激楠ㄧ璇婄枟闂ㄦ埛</title>
<style>
:root{--bg:#1c1c1e;--card-bg:#2c2c2e;--text:#f5f5f7;--text-secondary:#a1a1a6;--accent:#0a84ff;--danger:#ff453a;--warning:#ff9f0a;--success:#30d158;--border:#38383a;--bg-gradient:radial-gradient(ellipse at 50% 0%,var(--card-bg) 0%,var(--bg) 60%)}
body.light{--bg:#f2f2f7;--card-bg:#ffffff;--text:#1c1c1e;--text-secondary:#6e6e73;--accent:#007aff;--danger:#ff3b30;--warning:#ff9500;--success:#34c759;--border:#e5e5ea;--bg-gradient:radial-gradient(ellipse at 50% 0%,#ffffff 0%,#f2f2f7 60%)}
*{margin:0;padding:0;box-sizing:border-box}
::selection{background:var(--accent);color:#fff}
body{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','PingFang SC','Microsoft YaHei',sans-serif;-webkit-font-smoothing:antialiased;background:var(--bg-gradient);color:var(--text);height:100vh;overflow:hidden;display:flex;flex-direction:column;letter-spacing:-.01em}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.header{height:52px;flex-shrink:0;padding:0 20px;background:var(--card-bg);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px)}
.header h1{font-size:16px;font-weight:600}
.header .sub{font-size:11px;color:var(--text-secondary)}
.header .spacer{margin-left:auto}
.btn{padding:6px 14px;border:1px solid var(--border);border-radius:8px;font-size:12px;cursor:pointer;background:transparent;color:var(--text);font-family:inherit;transition:all .12s}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn-primary{background:var(--accent);color:#fff;border-color:var(--accent)}
#kpi-bar{flex-shrink:0;display:grid;grid-template-columns:repeat(5,1fr);gap:12px;padding:14px 20px}
.kpi{background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:12px 16px}
.kpi .val{font-size:24px;font-weight:700}
.kpi .label{font-size:11px;color:var(--text-secondary);margin-top:2px}
.body-grid{flex:1;display:flex;overflow:hidden}
#patient-list{width:240px;flex-shrink:0;background:var(--card-bg);border-right:1px solid var(--border);overflow-y:auto;padding:8px}
.p-card{padding:10px 12px;border-radius:10px;cursor:pointer;transition:all .12s;border:1px solid transparent}
.p-card:hover{background:var(--bg)}
.p-card.active{background:rgba(10,132,255,.12);border-color:var(--accent)}
.p-card .p-name{font-size:13px;font-weight:600}
.p-card .p-meta{font-size:11px;color:var(--text-secondary);margin-top:2px}
.center{flex:1;overflow-y:auto;padding:16px 20px}
#capability-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.cap{background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:14px;cursor:pointer;transition:all .15s}
.cap:hover{border-color:var(--accent);transform:translateY(-2px)}
.cap .cap-ico{font-size:20px}
.cap .cap-title{font-size:13px;font-weight:600;margin-top:6px}
.cap .cap-desc{font-size:11px;color:var(--text-secondary);margin-top:3px}
#stage-timeline{margin-top:20px;background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:14px}
#stage-timeline h3{font-size:13px;color:var(--accent);margin-bottom:10px}
.stage-row{display:flex;gap:10px;align-items:flex-start;padding:6px 0;font-size:12px}
.stage-row .num{width:20px;height:20px;border-radius:50%;background:var(--accent);color:#fff;font-size:11px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.stage-row .st-desc{color:var(--text-secondary);font-size:11px}
#result-panel{width:360px;flex-shrink:0;background:var(--card-bg);border-left:1px solid var(--border);overflow-y:auto;padding:16px}
#result-panel h3{font-size:13px;color:var(--accent);margin-bottom:10px}
.result-box{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:12px;font-family:'SF Mono',Consolas,monospace;font-size:11px;line-height:1.5;white-space:pre-wrap;word-break:break-word}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
.badge.high{background:rgba(255,69,58,.15);color:var(--danger)}
.badge.moderate,.badge.medium,.badge.urgent{background:rgba(255,159,10,.15);color:var(--warning)}
.badge.low,.badge.emergency{background:rgba(48,209,88,.15);color:var(--success)}
.muted{color:var(--text-secondary);font-size:12px}
</style>
</head>
<body>
<div class="header">
  <h1>馃Υ 鍒涗激楠ㄧ 路 璇婄枟闂ㄦ埛</h1>
  <span class="sub">鑰佸勾楂嬮儴楠ㄦ姌绮惧噯娌荤枟鏅鸿兘浣?/span>
  <div class="spacer"></div>
  <button class="btn" id="theme-toggle">鈽€ 娴呰壊</button>
  <button class="btn btn-primary" onclick="location.href='/workflow/orthopedic-surgery'">杩涘叆瀹屾暣宸ヤ綔娴?鈫?/button>
</div>

<div id="kpi-bar"><div class="kpi"><div class="val" id="kpi-total">鈥?/div><div class="label">鍦ㄩ櫌楂嬮儴楠ㄦ姌</div></div>
<div class="kpi"><div class="val" id="kpi-pending">鈥?/div><div class="label">寰呮墜鏈?/div></div>
<div class="kpi"><div class="val" id="kpi-48h">鈥?/div><div class="label">48h 鎵嬫湳绐楄揪鏍囩巼</div></div>
<div class="kpi"><div class="val" id="kpi-highrisk">鈥?/div><div class="label">楂樺嵄骞跺彂鐥囬璀?/div></div>
<div class="kpi"><div class="val" id="kpi-avgfactor">鈥?/div><div class="label">骞冲潎寤惰繜鍥犵礌鏁?/div></div></div>

<div class="body-grid">
  <div id="patient-list"><div class="muted" style="padding:8px">鍔犺浇鎮ｈ€呪€?/div></div>
  <div class="center">
    <div id="capability-grid"></div>
    <div id="stage-timeline"><h3>璇婄枟鍏ㄦ祦绋?路 11 闃舵</h3><div id="stage-rows"></div></div>
  </div>
  <div id="result-panel"><h3>缁撴灉闈㈡澘</h3><div class="muted" id="result-empty">鈫?閫夋嫨鎮ｈ€呭悗鐐瑰嚮涓婃柟鑳藉姏鍗℃煡鐪?AI 璇婄枟缁撴灉</div><div id="result-content"></div></div>
</div>

<script>
/* Task 4/5 濉厖 JS */
</script>
</body>
</html>
```

- [ ] **Step 4: 杩愯纭甯冨眬娴嬭瘯閫氳繃**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalLayout -q`
Expected: PASS锛? 椤癸級銆?
- [ ] **Step 5: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-core/haip/ui_ortho_portal.html tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 闂ㄦ埛 HTML 甯冨眬 + 璁捐浠ょ墝"
```

---

