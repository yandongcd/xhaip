"""RBAC engine — role-to-permission mapping and enforcement."""

from __future__ import annotations


from haip.auth.models import Permission, PREDEFINED_ROLES


# In-memory role-permission store (PostgreSQL-backed in P1)
_role_permissions: dict[str, set[Permission]] = {
    role: set(perms) for role, perms in PREDEFINED_ROLES.items()
}
# Custom roles added at runtime
_custom_roles: dict[str, set[Permission]] = {}


def get_permissions_for_roles(roles: list[str]) -> list[str]:
    """Get all permissions granted to a set of roles."""
    all_perms: set[str] = set()
    for role_name in roles:
        perms = _role_permissions.get(role_name) or _custom_roles.get(role_name)
        if perms:
            all_perms.update(p.value for p in perms)
    return sorted(all_perms)


def has_permission(roles: list[str], permission: Permission) -> bool:
    """Check if any of the given roles grant the specified permission."""
    for role_name in roles:
        perms = _role_permissions.get(role_name) or _custom_roles.get(role_name)
        if perms and permission in perms:
            return True
    return False


def add_role(name: str, permissions: list[Permission]) -> None:
    """Add or update a custom role."""
    _custom_roles[name] = set(permissions)


def remove_role(name: str) -> bool:
    """Remove a custom role. Returns True if successful."""
    if name in _custom_roles:
        del _custom_roles[name]
        return True
    return False


def list_roles() -> dict[str, list[str]]:
    """List all roles and their permissions."""
    result: dict[str, list[str]] = {}
    for name, perms in {**_role_permissions, **_custom_roles}.items():
        result[name] = sorted(p.value for p in perms)
    return result


def add_permission_to_role(role_name: str, permission: Permission) -> bool:
    """Add a permission to an existing role. Returns True if successful."""
    role = _custom_roles.get(role_name) or _role_permissions.get(role_name)
    if role is None:
        return False
    role.add(permission)
    return True


def require_permission(permission: Permission):
    """FastAPI dependency: checks the current user has the required permission.

    Returns an async callable suitable for FastAPI Depends.
    """
    from fastapi import HTTPException, Request

    async def _check(request: Request) -> dict:
        user = getattr(request.state, "current_user", None)
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if not has_permission(user.get("roles", []), permission):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _check


def require_any_permission(*permissions: Permission):
    """FastAPI dependency: checks the user has at least one of the given permissions."""
    from fastapi import HTTPException, Request

    async def _check(request: Request) -> dict:
        user = getattr(request.state, "current_user", None)
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_roles = user.get("roles", [])
        if not any(has_permission(user_roles, p) for p in permissions):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _check
