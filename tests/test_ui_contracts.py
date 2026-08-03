"""全站 UI 契约测试 — DOM/JS/API 一致性 (源自 2026-07-17 workflow 三连 bug 复盘).

C1: getElementById 静态 id 必须存在于 DOM
C2: onclick 引用函数必须已定义
C3: 嵌入 PATIENTS 的页面数据非空且含 patient_id
C4: 嵌入 AGENT 的页面其值 == 路由 agent 名
C5: fetch 静态路径必须在 FastAPI 路由表注册
C6: workflow STAGES[].tool 必须存在于 agent tools
C7: querySelector('#x') 静态 id 同 C1
C9: <script> 块花括号/圆括号必须配平 (JS SyntaxError 会导致整页脚本全灭)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from haip.agent import get as get_agent
from haip.agent import load_from_dir

ROOT = Path(__file__).resolve().parent.parent
load_from_dir(str(ROOT / "packages" / "haip-hospital" / "agents" / "definitions"))

from haip.web_server import app
from haip.workflow import WORKFLOWS

client = TestClient(app)

GETELEM_RE = re.compile(r"getElementById\('([\w-]+)'\)")
QS_ID_RE = re.compile(r"querySelector\('#([\w-]+)'\)")
DOM_ID_RE = re.compile(r'id="([\w-]+)"')
ONCLICK_RE = re.compile(r'onclick="(\w+)\s*\(')
FUNC_DEF_RE = re.compile(
    r'(?:function\s+(\w+)\s*\(|(?:var|let|const)\s+(\w+)\s*=\s*(?:async\s+)?function)'
)
PATIENTS_RE = re.compile(r"var PATIENTS\s*=\s*(\[.*?\]);", re.DOTALL)
AGENT_RE = re.compile(r"var AGENT\s*=\s*'([^']*)'")
WINDOW_AGENT_RE = re.compile(r"window\.AGENT\s*=\s*(\{.*\})\s*;\s*window\.PATIENTS", re.DOTALL)
FETCH_RE = re.compile(r"""fetch\(\s*['"](/[^'"$]*)['"]\s*[,)]""")


def _html_pages() -> list[str]:
    pages = ["/", "/ortho", "/ortho-portal", "/pharmacy", "/stream-demo", "/dashboard"]
    pages += [f"/workflow/{n}" for n in WORKFLOWS]
    pages += ["/process/orthopedic-surgery", "/process/respiratory", "/process/cardiology"]
    pages += ["/agent/orthopedic-surgery", "/agent/pharmacy"]
    return pages


PAGES = _html_pages()


def _get(path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path}: {resp.status_code}"
    return resp.text


@pytest.mark.parametrize("path", PAGES)
def test_c1_c7_js_dom_ids(path):
    html = _get(path)
    js_ids = set(GETELEM_RE.findall(html)) | set(QS_ID_RE.findall(html))
    dom_ids = set(DOM_ID_RE.findall(html))
    missing = js_ids - dom_ids
    assert not missing, f"{path}: JS 引用了不存在的 id: {sorted(missing)}"


@pytest.mark.parametrize("path", PAGES)
def test_c2_onclick_functions_defined(path):
    html = _get(path)
    called = set(ONCLICK_RE.findall(html))
    defined = {a or b for a, b in FUNC_DEF_RE.findall(html)}
    missing = called - defined
    assert not missing, f"{path}: onclick 引用了未定义函数: {sorted(missing)}"


@pytest.mark.parametrize("path", PAGES)
def test_c3_patients_not_empty(path):
    html = _get(path)
    m = PATIENTS_RE.search(html)
    if not m:
        pytest.skip(f"{path} 无嵌入 PATIENTS")
    patients = json.loads(m.group(1))
    assert patients, f"{path}: PATIENTS 为空 — 检查 haip.patients 加载链路"
    assert all("patient_id" in p for p in patients), f"{path}: 患者记录缺 patient_id"


@pytest.mark.parametrize("path", [p for p in PAGES if p.startswith(("/workflow/", "/agent/"))])
def test_c4_agent_var_matches_route(path):
    html = _get(path)
    expected = path.rsplit("/", 1)[-1]
    m = WINDOW_AGENT_RE.search(html)
    if m:
        data = json.loads(m.group(1))
        assert data.get("name") == expected, f"{path}: AGENT 被污染为 {data.get('name')!r}"
        return
    m = AGENT_RE.search(html)
    if m:
        assert m.group(1) == expected, f"{path}: AGENT 被污染为 {m.group(1)!r}"
        return
    if path.startswith("/workflow/"):
        pytest.skip(f"{path} 无嵌入 AGENT (DAG 纯静态渲染)")
    # 自定义模板页 (如 templates/pharmacy.html) 由各自渲染逻辑保证, 无嵌入 AGENT
    custom_tpl = ROOT / "packages" / "haip-core" / "haip" / "templates" / f"{expected}.html"
    if custom_tpl.exists():
        pytest.skip(f"{path} 使用自定义模板 {custom_tpl.name} (无嵌入 AGENT)")
    assert m, f"{path}: 无 AGENT 变量"


@pytest.mark.parametrize("path", PAGES)
def test_c5_fetch_paths_registered(path):
    html = _get(path)
    static_fetches = {p for p in FETCH_RE.findall(html) if "'" not in p and "+" not in p}
    if not static_fetches:
        pytest.skip(f"{path} 无静态 fetch")
    unmatched = []
    for fp in static_fetches:
        fp_clean = fp.split("?")[0]
        ok = any(
            getattr(r, "path", None) == fp_clean
            or (hasattr(r, "path_regex") and r.path_regex.match(fp_clean))
            for r in app.routes
        )
        if not ok:
            unmatched.append(fp)
    assert not unmatched, f"{path}: fetch 了未注册路由: {unmatched}"


@pytest.mark.parametrize("wf_name", sorted(WORKFLOWS))
def test_c6_workflow_tools_exist(wf_name):
    wf = WORKFLOWS[wf_name]
    plugin = get_agent(wf["agent"])
    assert plugin is not None, f"workflow 引用未注册 agent: {wf['agent']}"
    tool_names = {t.name for t in plugin.tools}
    missing = [s["tool"] for s in wf["stages"] if s["tool"] not in tool_names]
    assert not missing, f"{wf_name}: stages 引用不存在的 tool: {missing}"


# ── C8: 门户聊天必须走 reason 模式 (禁止盲调 tools[0]) ──

SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.DOTALL)


def _strip_js_literals(src: str) -> str:
    """去掉字符串/模板/注释, 只留结构字符, 供括号配平检查."""
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in ("'", '"', "`"):
            quote = c
            i += 1
            while i < n and src[i] != quote:
                i += 2 if src[i] == "\\" else 1
            i += 1
        elif c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                i += 1
        elif c == "/" and i + 1 < n and src[i + 1] == "*":
            i += 2
            while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
                i += 1
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


@pytest.mark.parametrize("path", PAGES)
def test_c9_script_braces_balanced(path):
    html = _get(path)
    for idx, script in enumerate(SCRIPT_RE.findall(html)):
        stripped = _strip_js_literals(script)
        for open_ch, close_ch in (("{", "}"), ("(", ")")):
            balance = stripped.count(open_ch) - stripped.count(close_ch)
            assert balance == 0, (
                f"{path}: <script>#{idx} '{open_ch}{close_ch}' 不配平 ({balance:+d}) "
                f"— JS SyntaxError 会令整页脚本失效 (主题切换/列表加载全灭)"
            )


def test_c8_portal_chat_uses_reason_mode():
    html = _get("/")
    m = re.search(r"async function sendChat\(\).*?^\}", html, re.DOTALL | re.MULTILINE)
    assert m, "portal 缺 sendChat"
    body = m.group(0)
    assert "'reason'" in body or '"reason"' in body, "聊天必须走 reason (ReAct AgentLoop)"
    assert "tools[0]" not in body, "禁止把聊天消息盲发给 tools[0]"


def test_c8_reason_mode_returns_reply_for_any_agent():
    """任意科室 reason 聊天必须返回 reply 字段 (mock LLM 下亦然)."""
    for agent in ("pharmacy", "medical-record"):
        r = client.post("/api/call", json={
            "agent": agent, "tool": "reason", "params": {"query": "你好"}})
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") in ("ok", "blocked"), f"{agent}: {data}"
        assert isinstance(data.get("reply", ""), str) and data.get("reply") is not None, \
            f"{agent}: reason 模式无 reply — 聊天链路断裂"
