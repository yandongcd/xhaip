"""Dashboard 域 — 从 web_server 拆出 (P1-6).

/dashboard /home /api/dashboard
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    """TOGAF 10 架构治理仪表盘 — 全院 39 科室成熟度热力图。"""
    from haip.togaf.dashboard import _load_analysis_data
    from haip.web_server import templates
    data = _load_analysis_data()
    template = templates.env.get_template("dashboard/index.html")
    content = template.render(request=request, DASHBOARD_DATA=data)
    return HTMLResponse(content)


@router.get("/home")
def home_redirect(request: Request):
    """Role-based home redirect for 12 portal identities.

    Priority: Bearer JWT roles > ?role= > ?identity= (mapped via PORTAL_IDENTITY_ROLES).
    """
    from haip.auth.models import PORTAL_IDENTITY_ROLES

    role: str | None = None

    # Priority 1: Bearer JWT
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from haip.auth.jwt import decode_token
            payload = decode_token(auth_header[7:])
            roles = payload.get("roles", [])
            if roles:
                role = roles[0]
        except Exception as e:
            logging.getLogger(__name__).debug("/home JWT 解析失败, 回退 query 参数: %s", e)

    # Priority 2: ?role= query param
    if role is None:
        role = request.query_params.get("role")

    # Priority 3: ?identity= query param → map via PORTAL_IDENTITY_ROLES
    if role is None:
        identity = request.query_params.get("identity")
        if identity and identity in PORTAL_IDENTITY_ROLES:
            role = PORTAL_IDENTITY_ROLES[identity]

    if role is None:
        return RedirectResponse(url="/", status_code=302)

    # Role → URL mapping (agent routes confirmed against agents/definitions/)
    ROLE_ROUTES: dict[str, str] = {
        "leadership": "/dashboard",
        "dept_head": "/dashboard",
        "pharmacist": "/pharmacy",
        "head_nurse": "/agent/nurse-general",
        "nurse": "/agent/nurse-general",
        "anesthesiologist": "/agent/anesthesia-risk",
        "med_tech": "/agent/lab-critical-value",
        "intern": "/agent/education",
        "resident": "/",
        "doctor": "/",
        "admin": "/",
    }

    target = ROLE_ROUTES.get(role, "/")
    return RedirectResponse(url=target, status_code=302)


@router.get("/api/dashboard")
def dashboard_api():
    """Dashboard data as JSON."""
    from haip.togaf.dashboard import render_dashboard_json
    return render_dashboard_json()
