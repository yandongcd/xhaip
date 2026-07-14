## Task 2: 鏂板 /ortho-portal 璺敱

**Files:**
- Modify: `packages/haip-core/haip/web_server.py` (鍦?`/ortho` 璺敱 `:580-584` 涔嬪悗鎻掑叆)
- Test: `tests/integration/test_ortho_portal.py`

**Interfaces:**
- Consumes: `Path`, `HTMLResponse`锛堟枃浠堕《閮ㄥ凡 import锛沗/ortho` 璺敱宸蹭娇鐢ㄥ悓娆撅級銆?- Produces: `GET /ortho-portal` 鈫?200 text/html锛岃鍙?`ui_ortho_portal.html`銆?
- [ ] **Step 1: 鍐欒矾鐢?200 鐨勫け璐ユ祴璇?*

鍦?`test_ortho_portal.py` 杩藉姞锛?
```python
class TestPortalRoute:
    def test_route_returns_200(self):
        r = client.get("/ortho-portal")
        assert r.status_code == 200

    def test_route_is_html(self):
        r = client.get("/ortho-portal")
        body = r.text.lower()
        for tag in ["<!doctype", "<html", "<head", "<body", "<title"]:
            assert tag in body, f"缂?{tag}"
```

- [ ] **Step 2: 杩愯纭澶辫触**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalRoute -q`
Expected: FAIL锛?04锛岃矾鐢辨湭瀹氫箟 / 鏂囦欢涓嶅瓨鍦級銆?
- [ ] **Step 3: 娣诲姞璺敱**

鍦?`web_server.py` `ortho_ui()` 鍑芥暟涔嬪悗锛坄/pharmacy` 涔嬪墠锛夋彃鍏ワ細

```python
@app.get("/ortho-portal", response_class=HTMLResponse)
def ortho_portal_ui():
    """鍒涗激楠ㄧ璇婄枟闂ㄦ埛 鈥?KPI 鐪嬫澘 + AI 璇婄枟鑳藉姏鍗?+ 鎮ｈ€呴槦鍒?+ 娴佺▼鏃堕棿杞淬€?""
    with open(Path(__file__).parent / "ui_ortho_portal.html", encoding="utf-8") as f:
        return f.read()
```

- [ ] **Step 4: 寤哄崰浣?HTML 浣胯矾鐢卞彲杩斿洖**

Create `packages/haip-core/haip/ui_ortho_portal.html`锛堟渶灏忛鏋讹紝Task 3 濉厖锛夛細

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xhaip 鈥?鍒涗激楠ㄧ璇婄枟闂ㄦ埛</title>
</head>
<body>
<div id="app">鍒涗激楠ㄧ璇婄枟闂ㄦ埛 鍔犺浇涓€?/div>
</body>
</html>
```

- [ ] **Step 5: 杩愯纭閫氳繃**

Run: `python -m pytest tests/integration/test_ortho_portal.py::TestPortalRoute -q`
Expected: PASS锛? 椤癸級銆?
- [ ] **Step 6: Commit**

```powershell
git -C D:\FC\xhaip add packages/haip-core/haip/web_server.py packages/haip-core/haip/ui_ortho_portal.html tests/integration/test_ortho_portal.py
git -C D:\FC\xhaip commit -m "feat(ortho): 鏂板 /ortho-portal 璺敱 + HTML 楠ㄦ灦"
```

---

