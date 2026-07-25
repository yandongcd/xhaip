# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :x:                |
| < 1.1    | :x:                |

## Reporting a Vulnerability

Do NOT create a public GitHub issue. Send details to the maintainers via private channel.

## Security Measures

- All patient PHI is encrypted via AES (Fernet with stdlib fallback)
- JWT-based authentication with configurable expiry
- Guard system enforces T1/T2 trust levels on medical outputs
- Rate limiting enabled by default in production
- CORS restricted in production mode
- Audit logging records all agent calls and patient data accesses
