"""Tenant Management API — FastAPI router for tenant CRUD operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from haip.auth.middleware import get_current_user
from haip.auth.rbac import Permission, has_permission
from haip.tenants import get_tenant_manager

tenant_router = APIRouter(prefix="/api/tenants", tags=["tenants"])


@tenant_router.get("")
def list_tenants(current_user: dict = Depends(get_current_user)):
    """List all tenants (admin only)."""
    if not has_permission(current_user.get("roles", []), Permission.ADMIN_TENANTS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    mgr = get_tenant_manager()
    return [
        {
            "id": t.id,
            "name": t.name,
            "hospital_name": t.hospital_name,
            "hospital_code": t.hospital_code,
            "status": t.status.value,
            "max_users": t.max_users,
            "max_agents": t.max_agents,
            "created_at": t.created_at,
            "expires_at": t.expires_at,
            "features": t.features,
        }
        for t in mgr.list_all()
    ]


@tenant_router.post("")
def create_tenant(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Create a new tenant (admin only)."""
    if not has_permission(current_user.get("roles", []), Permission.ADMIN_TENANTS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    import asyncio
    loop = asyncio.new_event_loop()
    data = loop.run_until_complete(request.json())

    mgr = get_tenant_manager()
    tenant = mgr.create(
        name=data.get("name", ""),
        hospital_name=data.get("hospital_name", ""),
        hospital_code=data.get("hospital_code", ""),
        admin_email=data.get("admin_email", ""),
        max_users=data.get("max_users", 100),
        max_agents=data.get("max_agents", 48),
    )

    return {
        "status": "ok",
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "hospital_name": tenant.hospital_name,
            "status": tenant.status.value,
        },
    }


@tenant_router.get("/{tenant_id}")
def get_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single tenant."""
    if not has_permission(current_user.get("roles", []), Permission.ADMIN_TENANTS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    mgr = get_tenant_manager()
    tenant = mgr.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {
        "id": tenant.id,
        "name": tenant.name,
        "hospital_name": tenant.hospital_name,
        "hospital_code": tenant.hospital_code,
        "status": tenant.status.value,
        "max_users": tenant.max_users,
        "max_agents": tenant.max_agents,
        "enabled_agents": tenant.enabled_agents,
        "disabled_agents": tenant.disabled_agents,
        "his_adapter_type": tenant.his_adapter_type,
        "features": tenant.features,
        "created_at": tenant.created_at,
        "expires_at": tenant.expires_at,
    }


@tenant_router.post("/{tenant_id}/activate")
def activate_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    """Activate a tenant."""
    if not has_permission(current_user.get("roles", []), Permission.ADMIN_TENANTS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    mgr = get_tenant_manager()
    if not mgr.activate(tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"status": "ok", "tenant_id": tenant_id, "status_new": "active"}


@tenant_router.post("/{tenant_id}/suspend")
def suspend_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    """Suspend a tenant."""
    if not has_permission(current_user.get("roles", []), Permission.ADMIN_TENANTS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    mgr = get_tenant_manager()
    if not mgr.suspend(tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"status": "ok", "tenant_id": tenant_id, "status_new": "suspended"}


@tenant_router.post("/{tenant_id}/features")
def update_features(
    tenant_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Enable/disable features for a tenant."""
    if not has_permission(current_user.get("roles", []), Permission.ADMIN_TENANTS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    import asyncio
    loop = asyncio.new_event_loop()
    data = loop.run_until_complete(request.json())

    mgr = get_tenant_manager()
    tenant = mgr.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    for feature, enabled in data.get("features", {}).items():
        mgr.set_feature(tenant_id, feature, bool(enabled))

    return {"status": "ok", "tenant_id": tenant_id, "features": tenant.features}
