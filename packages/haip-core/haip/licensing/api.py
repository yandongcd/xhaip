"""License Management API — FastAPI router for license status and info."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from haip.auth.middleware import get_current_user
from haip.auth.rbac import has_permission, Permission
from haip.licensing import LicenseManager

license_router = APIRouter(prefix="/api/license", tags=["license"])

_license_mgr = LicenseManager()


def get_license_manager() -> LicenseManager:
    """Get the license manager singleton."""
    return _license_mgr


@license_router.get("/status")
def license_status(current_user: dict = Depends(get_current_user)):
    """Get current license status (requires admin:licenses or admin:*)."""
    if not has_permission(current_user.get("roles", []), Permission.ADMIN_LICENSES):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    info = _license_mgr.get_info()
    if info is None:
        return {"status": "unknown", "message": "License not loaded"}

    return {
        "valid": info.valid,
        "customer_name": info.customer_name,
        "customer_code": info.customer_code,
        "max_agents": info.max_agents,
        "max_users": info.max_users,
        "expiry_date": info.expiry_date,
        "issued_date": info.issued_date,
        "features": info.features,
        "error": info.error if not info.valid else None,
    }


@license_router.get("/features")
def license_features():
    """Get enabled features (public — used by UI to hide/show features)."""
    info = _license_mgr.get_info()
    if info is None or not info.valid:
        return {"features": []}
    return {"features": info.features}


@license_router.get("/check/{feature}")
def license_check_feature(feature: str):
    """Check if a specific feature is enabled."""
    enabled = _license_mgr.is_feature_enabled(feature)
    return {"feature": feature, "enabled": enabled}
