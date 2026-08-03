"""Multi-tenant architecture — tenant isolation and management.

Isolation strategy: Schema-per-tenant (PostgreSQL schemas) or
ID-prefix separation (for simpler setups).

Each tenant has:
    - Unique tenant_id
    - Hospital name and metadata
    - Status (active / suspended / trial)
    - Configuration overrides
    - Data isolation
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"


@dataclass
class Tenant:
    """A single hospital/tenant instance."""

    id: str
    name: str
    hospital_name: str = ""
    hospital_code: str = ""
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: str = ""
    expires_at: str = ""

    # Contact info
    admin_email: str = ""
    admin_phone: str = ""

    # Configuration overrides
    max_users: int = 100
    max_agents: int = 48
    enabled_agents: list[str] = field(default_factory=list)
    disabled_agents: list[str] = field(default_factory=list)

    # HIS adapter
    his_adapter_type: str = "mock"  # mock | fhir | hl7v2 | rest
    his_endpoint: str = ""
    his_credentials: dict[str, str] = field(default_factory=dict)

    # Features
    features: dict[str, bool] = field(default_factory=lambda: {
        "ai_suggestions": True,
        "guard_safety": True,
        "knowledge_base": True,
        "mdt_workflow": True,
        "reporting": False,
        "export": False,
    })

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)


class TenantManager:
    """Manages tenants — create, activate, suspend, query."""

    def __init__(self):
        self._tenants: dict[str, Tenant] = {}
        self._default_tenant: Tenant | None = None

    def create(self, name: str, hospital_name: str = "", **kwargs) -> Tenant:
        """Create a new tenant."""
        tenant_id = kwargs.pop("tenant_id", uuid.uuid4().hex[:8])
        tenant = Tenant(
            id=tenant_id,
            name=name,
            hospital_name=hospital_name or name,
            **kwargs,
        )
        self._tenants[tenant.id] = tenant
        if self._default_tenant is None:
            self._default_tenant = tenant
        return tenant

    def get(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID."""
        return self._tenants.get(tenant_id)

    def get_default(self) -> Tenant | None:
        """Get the default tenant."""
        return self._default_tenant

    def list_active(self) -> list[Tenant]:
        """List all active tenants."""
        return [t for t in self._tenants.values() if t.status == TenantStatus.ACTIVE]

    def list_all(self) -> list[Tenant]:
        """List all tenants."""
        return list(self._tenants.values())

    def activate(self, tenant_id: str) -> bool:
        """Activate a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.ACTIVE
            return True
        return False

    def suspend(self, tenant_id: str) -> bool:
        """Suspend a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.SUSPENDED
            return True
        return False

    def set_feature(self, tenant_id: str, feature: str, enabled: bool) -> bool:
        """Enable or disable a feature for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.features[feature] = enabled
            return True
        return False

    def is_feature_enabled(self, tenant_id: str, feature: str) -> bool:
        """Check if a feature is enabled for a tenant."""
        tenant = self.get(tenant_id)
        if tenant:
            return tenant.features.get(feature, False)
        return False

    def is_agent_enabled(self, tenant_id: str, agent_name: str) -> bool:
        """Check if an agent is enabled for a tenant."""
        tenant = self.get(tenant_id)
        if not tenant:
            return True  # No restrictions if no tenant

        if agent_name in tenant.disabled_agents:
            return False
        if tenant.enabled_agents and agent_name not in tenant.enabled_agents:
            return False
        return True

    def get_his_config(self, tenant_id: str) -> dict[str, Any]:
        """Get HIS adapter configuration for a tenant."""
        tenant = self.get(tenant_id)
        if not tenant:
            return {"type": "mock", "endpoint": ""}
        return {
            "type": tenant.his_adapter_type,
            "endpoint": tenant.his_endpoint,
            "credentials": tenant.his_credentials,
        }

    def delete(self, tenant_id: str) -> bool:
        """Delete a tenant (soft — marks as expired)."""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.EXPIRED
            return True
        return False


# Global singleton
_tenant_manager = TenantManager()


def get_tenant_manager() -> TenantManager:
    """Get the global tenant manager singleton."""
    return _tenant_manager


def init_default_tenant():
    """Initialize a default tenant for single-hospital deployments."""
    mgr = get_tenant_manager()
    if not mgr.list_all():
        mgr.create(
            name="default",
            hospital_name="Default Hospital",
            hospital_code="DH",
            max_users=100,
            max_agents=48,
        )
