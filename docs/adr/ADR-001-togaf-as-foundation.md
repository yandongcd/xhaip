# ADR-001: TOGAF 10 as Architecture Governance Foundation

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-10 |
| **Deciders** | xhaip v1.0 architecture team |
| **Supersedes** | N/A |

---

## Context

xhaip v1.0 is a Hospital AI Platform with **48 agents** spanning **39 clinical departments**. Each agent operates independently with its own domain logic, tools, and guard rules. As the platform scales, ensuring architectural consistency across agents becomes critical:

- Are all agents aligned with clinical domain boundaries?
- Do tool definitions follow consistent naming and input/output schemas?
- Are guard rules traceable to evidence-based clinical guidelines?
- Can we measure architecture maturity per department?

Without governance, the platform risks becoming a collection of inconsistent, untraceable AI services.

---

## Decision

**Adopt TOGAF 10 as the architecture governance foundation**, implemented as a core package (`haip-core/haip/togaf/`) with the following modules:

| Module | Responsibility |
|--------|---------------|
| `validator.py` | Agent registration gate — validates each agent against ABB (Architecture Building Blocks) |
| `governance.py` | Best practice (BP) loading, guideline reporting, maturity scoring |
| `builder.py` | Multi-department architecture building block construction |
| `dashboard.py` | Interactive maturity heatmap for 39 departments |
| `rule_engine.py` | YAML-driven clinical rule execution (diagnosis/risk/treatment) |
| `metamodel.py` | TOGAF meta-model — entity definitions, relationships |
| `audit.py` | Architecture compliance auditing |
| `analysis.py` | Cross-department architecture analysis |
| `organization.py` | Organizational mapping (departments, roles, capabilities) |
| `knowledge_agent.py` | KnowledgeAgent — guideline-driven reasoning |
| `agent_generator.py` | Auto-generate agent YAML definitions from TOGAF models |
| `patient_generator.py` | Digital patient generation aligned to department models |
| `roles.py` | Role-based access control aligned to TOGAF organization model |
| `templates/` | EA templates — capability heatmap, app landscape, roadmap, stakeholder map, value stream map |

Each agent YAML definition is validated at startup via `validator.py` against 111 ABB checks.

---

## Options Considered

### Option A: Embedded governance (rejected)
Embed governance rules directly into each agent's YAML definition. Each agent self-validates.

- **Pros**: No external dependency, simpler initial implementation.
- **Cons**: No cross-agent consistency enforcement; rules duplicated across agents; impossible to measure enterprise-wide maturity.

### Option B: Separate governance agent (rejected)
A dedicated "TOGAF Agent" that other agents call for validation.

- **Pros**: Centralized governance logic.
- **Cons**: Adds network latency on every agent call; single point of failure; governance should be architecture-level, not runtime-level concern.

### Option C: Core package with registration gate (accepted)
TOGAF governance as a core Python package, invoked at agent registration time (startup), not runtime.

- **Pros**: Enforced at load time — no runtime overhead; centralized in one package; enables enterprise-wide maturity reporting; ABB traceability for every agent.
- **Cons**: Tight coupling to startup sequence; requires TOGAF knowledge for new contributors.

---

## Outcome

- **haip-core/haip/togaf/** implemented as a core package with 16 modules
- TOGAF agent defined as a YAML definition (`agents/definitions/togaf.yaml`) — governance logic lives in code, agent definition is declarative
- **111/111 ABB checks** passing across 314 clinical rules
- **Full ABB traceability**: every rule, tool, and guard trigger is traceable to a TOGAF architecture building block
- **Independent test suite**: 25 tests covering 7 TOGAF modules

---

## Consequences

### Positive
- **Enterprise-wide visibility**: The `/dashboard` endpoint provides a real-time maturity heatmap across all 39 departments
- **Enforced consistency**: Every new agent must pass the TOGAF validator gate before registration
- **Traceable clinical rules**: 314 clinical rules across 38 departments are all ABB-traceable
- **Separation of concerns**: Governance logic is in the core package; agent definitions remain declarative YAML

### Negative
- **Learning curve**: New contributors must understand TOGAF 10 concepts (ABB, capability mapping)
- **Startup coupling**: Agent registration depends on TOGAF validation; validation failures block startup (best-effort, prints warning)
- **Maintenance overhead**: TOGAF meta-model must stay synchronized with clinical domain changes
