# xhaip v1.0 API Reference

> Base URL: `http://localhost:8769`

---

## Agents

### `GET /api/agents`
List all registered agents with their tools.

**Example response:**
```json
[
  {
    "name": "ortho-trauma",
    "cn_name": "创伤骨科智能体",
    "type": "business",
    "port": 8701,
    "department": "骨科",
    "version": "1.0.0",
    "tools": [{"name": "diagnose", "description": "骨折诊断"}],
    "depends_on": [],
    "sub_agents": [],
    "parent": null
  }
]
```

---

### `GET /api/agents/{name}`
Get detailed info for a single agent.

**Example:** `GET /api/agents/ortho-trauma`

**Example response:**
```json
{
  "name": "ortho-trauma",
  "cn_name": "创伤骨科智能体",
  "type": "business",
  "port": 8701,
  "department": "骨科",
  "version": "1.0.0",
  "tools": [
    {
      "name": "diagnose",
      "description": "骨折诊断",
      "handler": "ortho_trauma.diagnose",
      "input": {"patient_id": "string"}
    }
  ],
  "guard": {
    "triggers": ["手术方案"],
    "high_risk_scenarios": ["抗凝管理"]
  },
  "ui": {"template": "default", "roles": ["医生", "护士"], "sidebar": []}
}
```

---

### `POST /api/call`
Invoke an agent tool.

**Request body:**
```json
{
  "agent": "ortho-trauma",
  "tool": "diagnose",
  "params": {"patient_id": "P001"}
}
```

**Example response:**
```json
{
  "status": "ok",
  "result": {"diagnosis": "股骨颈骨折", "confidence": 0.92}
}
```

---

### `GET /api/history`
Retrieve A2A call history.

**Query params:** `limit` (int, default 20)

**Example:** `GET /api/history?limit=10`

**Example response:**
```json
[
  {
    "timestamp": "2026-07-10T12:00:00",
    "agent": "ortho-trauma",
    "tool": "diagnose",
    "status": "ok"
  }
]
```

---

### `GET /api/agent-ui/{agent_name}`
Get UI config for an agent (fast UI generator).

**Example:** `GET /api/agent-ui/ortho-trauma`

**Example response:**
```json
{
  "agent": "ortho-trauma",
  "cn_name": "创伤骨科智能体",
  "type": "business",
  "tabs": [{"id": "diagnose", "label": "diagnose", "desc": "骨折诊断", "inputs": {"patient_id": "string"}}],
  "roles": ["医生"],
  "sidebar": []
}
```

---

## Guard (Safety)

### `POST /api/guard`
Execute guard safety verification on agent output.

**Request body:**
```json
{
  "output": "建议进行 THA 手术, 时机 48h 内。参考: NICE NG37",
  "scenario": "手术方案",
  "agent": "ortho-trauma",
  "cross_agent_outputs": []
}
```

**Example response:**
```json
{
  "passed": true,
  "flags": [],
  "citations": [
    {"source": "NICE NG37", "trust_level": "high", "verified": true}
  ],
  "confidence": "HIGH",
  "requires_human_review": false,
  "cross_validation_conflict": false
}
```

---

## Knowledge

### `GET /api/knowledge/stats`
Get knowledge base statistics.

**Example response:**
```json
{
  "knowledge": {"guidelines": 36, "rules": 314, "bps": 50},
  "cases": {"total": 384, "departments": 38}
}
```

---

### `GET /api/knowledge/search`
Search knowledge base.

**Query params:** `q` (string), `limit` (int, default 20)

**Example:** `GET /api/knowledge/search?q=骨折&limit=5`

**Example response:**
```json
{
  "guidelines": [{"title": "股骨颈骨折诊疗指南", "source": "NICE NG157", "score": 0.95}],
  "cases": [{"id": "P001", "diagnosis": "股骨颈骨折", "department": "骨科"}]
}
```

---

## TOGAF Dashboard

### `GET /dashboard`
TOGAF 10 architecture governance dashboard (HTML).

Returns an interactive HTML page with department maturity heatmap.

---

### `GET /api/dashboard`
Dashboard data as JSON.

**Example response:**
```json
{
  "departments": 39,
  "total_agents": 48,
  "total_rules": 314,
  "maturity": {"骨科": 0.92, "心内科": 0.88, "普外科": 0.85},
  "abb_coverage": 1.0
}
```

---

## UI (HTML Views)

### `GET /`
Web portal — Agent manager + Tool invocation + Chat interface.

---

### `GET /agent/{name}`
Generic agent professional UI — auto-rendered from YAML definition.

**Example:** `GET /agent/ortho-trauma`

---

### `GET /workflow/{name}`
Workflow-aware UI — role filtering + stage progress + auto data passing.

**Example:** `GET /workflow/ortho-trauma`

---

### `GET /process/{name}`
Clinical process UI — dynamic stages + digital patient + role switching.

**Example:** `GET /process/ortho-trauma`

---

### `GET /ortho`
Orthopedics specialty interface — 15-tab clinical workstation.

---

### `GET /pharmacy`
Pharmacy specialty interface — prescription review + drug interaction visualization.

---

## Health & Legacy

### `GET /api/health`
Health check endpoint.

**Example response:**
```json
{"status": "ok", "agents_loaded": 48, "version": "1.0.0"}
```

---

### `GET /patients`
Legacy endpoint for patient data (backward compat with demo pages).

**Query params:** `q` (string), `agent` (string)

---

### `GET /stats`
Legacy endpoint for statistics.

**Example response:**
```json
{"agents_loaded": 48, "call_history": 125, "patients_loaded": 384}
```
