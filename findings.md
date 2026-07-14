# xhaip 商用化 — Findings

> Research discoveries during implementation.

## Codebase Notes
- haip-core already has pydantic, httpx, fastapi, uvicorn as dependencies
- No existing auth middleware or user model
- A2A dispatches via importlib (in-process), needs to support HTTP calls for cross-container
- KnowledgeStore uses raw SQLite, needs SQLAlchemy abstraction
- Observability module exists but uses custom collectors, needs Prometheus

## Dependencies to Add
- `bcrypt` / `passlib` — password hashing
- `PyJWT` — JWT token handling
- `sqlalchemy[asyncio]` + `asyncpg` — PostgreSQL ORM
- `alembic` — DB migration
- `structlog` — structured logging
- `prometheus-client` — Prometheus metrics
- `opentelemetry-api/sdk` + exporters — distributed tracing
- `fhir.resources` — FHIR models
- `python-hl7` — HL7 v2 parsing
