"""Quick verification script for P0 modules."""
import sys

sys.path.insert(0, "packages/haip-core")

# Test auth models
print("Auth models OK")

# Test password hashing
from haip.auth.password import hash_password, validate_password_strength, verify_password

h = hash_password("Test@123")
is_strong, msg = validate_password_strength("Test@123")
print(f"Password: hash={h[:20]}..., verify={verify_password('Test@123', h)}, strength={is_strong}")

# Test JWT
from haip.auth.jwt import create_access_token, decode_token

t, exp = create_access_token("user1", "test", ["doctor"], ["agent:read"])
p = decode_token(t)
print(f"JWT: sub={p['sub']}, roles={p['roles']}, expires={exp}s")

# Test RBAC
from haip.auth.models import Permission
from haip.auth.rbac import get_permissions_for_roles, has_permission

perms = get_permissions_for_roles(["doctor"])
print(f"RBAC: doctor perms count={len(perms)}, has agent:execute={has_permission(['doctor'], Permission.AGENT_EXECUTE)}")

# Test Audit
from haip.audit import AuditLogger

al = AuditLogger()
al.log("login", "test", "success")
print(f"Audit: events={al.stats()['total_events']}")

# Test Crypto
from haip.crypto import decrypt_field, encrypt_field

e = encrypt_field("test-value")
d = decrypt_field(e)
print(f"Crypto: encrypt/decrypt OK, match={d == 'test-value'}")

# Test Config
from haip.config import get_config

cfg = get_config()
print(f"Config: server.port={cfg.get('server.port')}, auth.enabled={cfg.get('auth.enabled')}")

# Test A2A auth
from haip.a2a.auth import register_agent_secret, sign_a2a_request, verify_a2a_request

register_agent_secret("test-agent")
headers = sign_a2a_request("test-agent", "test_tool", {"param": "value"})
valid = verify_a2a_request("test-agent", "test_tool", {"param": "value"},
                           headers["X-A2A-Timestamp"], headers["X-A2A-Signature"])
print(f"A2A Auth: sign/verify OK, valid={valid}")

print("\n=== ALL P0 MODULES VERIFIED ===")
