"""Authentication models — User, Role, Permission, Session."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Permission(Enum):
    """Permission granularity: resource:action."""

    # Agent permissions
    AGENT_LIST = "agent:list"
    AGENT_READ = "agent:read"
    AGENT_EXECUTE = "agent:execute"

    # Patient data permissions
    PATIENT_READ = "patient:read"
    PATIENT_WRITE = "patient:write"

    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_ROLES = "admin:roles"
    ADMIN_TENANTS = "admin:tenants"
    ADMIN_LICENSES = "admin:licenses"
    ADMIN_CONFIG = "admin:config"

    # Audit
    AUDIT_READ = "audit:read"


# Predefined roles with default permissions
PREDEFINED_ROLES: dict[str, list[Permission]] = {
    "admin": [
        Permission.AGENT_LIST,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.PATIENT_READ,
        Permission.PATIENT_WRITE,
        Permission.ADMIN_USERS,
        Permission.ADMIN_ROLES,
        Permission.ADMIN_TENANTS,
        Permission.ADMIN_LICENSES,
        Permission.ADMIN_CONFIG,
        Permission.AUDIT_READ,
    ],
    "doctor": [
        Permission.AGENT_LIST,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.PATIENT_READ,
        Permission.PATIENT_WRITE,
    ],
    "pharmacist": [
        Permission.AGENT_LIST,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.PATIENT_READ,
    ],
    "dept_head": [
        Permission.AGENT_LIST,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.PATIENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.AUDIT_READ,
    ],
    "resident": [
        Permission.AGENT_LIST,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.PATIENT_READ,
    ],
}


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    email: Optional[str] = None
    display_name: Optional[str] = None
    department: Optional[str] = None


class UserLoginRequest(BaseModel):
    username: str
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    id: str
    username: str
    display_name: str
    email: Optional[str] = None
    department: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    tenant_id: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo
