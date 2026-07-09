"""xhaip Demo Server — 本地 HTTP API, 供 HTML 页面调用 Agent 工具."""

from __future__ import annotations

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-hospital"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-hospital" / "modules"))

from haip.agent import load_from_dir, register, _registry, get as get_agent, DomainPlugin, ToolDef  # noqa: E402
from haip.a2a import call as a2a_call, get_history, clear_history  # noqa: E402
from haip.guard.verifier import GuardVerifier, GuardResult  # noqa: E402

YAML_DIR = PROJECT_ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
PATIENTS_FILE = PROJECT_ROOT / "packages" / "haip-hospital" / "data" / "patients.json"

# 加载患者数据
_patients_cache: list[dict] = []
COMMASPACE_AGENTS: dict[str, list[str]] = {}  # agent_name → compatible patient departments


def init_agents():
    """一次性加载所有 YAML 定义 + 补充运行时工具注册。"""
    _registry.clear()
    count = load_from_dir(str(YAML_DIR))

    # 补充未在 YAML 中声明 handler 的工具（运行时动态注册）
    extra_tools = {
        "pharmacy": [
            ToolDef(name="calculate_tpn", description="TPN 全肠外营养配比计算",
                    handler="pharmacy.tpn_calculator.compute"),
            ToolDef(name="review_prescription", description="处方审核",
                    handler="pharmacy.prescription_review.check"),
            ToolDef(name="recommend_nutrition_route", description="EN vs PN 推荐",
                    handler="pharmacy.nutrition_consultation.route"),
            ToolDef(name="list_medications", description="药品查询",
                    handler="pharmacy.drug_db.search"),
        ],
        "orthopedic-surgery": [
            ToolDef(name="classify_fracture", description="骨折分型", handler="orthopedics.assess"),
            ToolDef(name="preop_assessment", description="术前评估", handler="orthopedics.evaluate"),
            ToolDef(name="surgical_plan", description="手术方案", handler="orthopedics.plan"),
            ToolDef(name="complication_risk", description="并发症风险", handler="orthopedics.predict"),
            ToolDef(name="timing_decision", description="手术时机", handler="orthopedics.decide"),
        ],
        "cardio-surgery": [
            ToolDef(name="surgical_assess", description="心脏手术评估", handler="cardio_surgery.evaluate"),
            ToolDef(name="anticoagulation_plan", description="抗凝方案", handler="cardio_surgery.plan"),
            ToolDef(name="postop_management", description="术后管理", handler="cardio_surgery.manage"),
        ],
        "pediatrics": [
            ToolDef(name="growth_assess", description="生长发育评估", handler="pediatrics.evaluate"),
            ToolDef(name="dose_calculate", description="儿童用药剂量", handler="pediatrics.calc"),
            ToolDef(name="imci_diagnose", description="IMCI 诊断", handler="pediatrics.diagnose"),
        ],
        "cardio-risk": [
            ToolDef(name="assess_cardiac", description="心脏风险评估", handler="cardio_risk.evaluate"),
            ToolDef(name="assess_mi", description="MI 评估", handler="cardio_risk.evaluate_mi"),
            ToolDef(name="assess_hypertension", description="高血压评估", handler="cardio_risk.evaluate_htn"),
        ],
        "anesthesia-risk": [
            ToolDef(name="assess_asa", description="ASA 分级", handler="anesthesia.evaluate"),
            ToolDef(name="airway_assess", description="困难气道", handler="anesthesia.evaluate_aw"),
            ToolDef(name="anesthesia_plan", description="麻醉方案", handler="anesthesia.recommend"),
        ],
        "pain-hub": [
            ToolDef(name="triage", description="疼痛分诊", handler="pain_hub.triage"),
            ToolDef(name="aggregate", description="结果聚合", handler="pain_hub.merge"),
        ],
        "acute-pain": [
            ToolDef(name="assess_acute", description="急性疼痛评估", handler="acute_pain.assess"),
            ToolDef(name="manage_pca", description="PCA 镇痛", handler="acute_pain.pca"),
            ToolDef(name="detect_crisis", description="危象检测", handler="acute_pain.crisis"),
        ],
        "chronic-pain": [
            ToolDef(name="assess_chronic", description="慢性疼痛评估", handler="chronic_pain.assess"),
            ToolDef(name="assess_scales", description="量表评分", handler="chronic_pain.scales"),
            ToolDef(name="stepped_care", description="阶梯治疗", handler="chronic_pain.care"),
        ],
        "cancer-pain": [
            ToolDef(name="assess_cancer", description="癌痛评估", handler="cancer_pain.assess"),
            ToolDef(name="opioid_safety", description="阿片安全", handler="cancer_pain.safety"),
            ToolDef(name="palliative_refer", description="姑息转介", handler="cancer_pain.palliative"),
        ],
        "interventional-pain": [
            ToolDef(name="assess_indications", description="介入适应症", handler="interventional_pain.indicate"),
            ToolDef(name="imaging_gate", description="影像门控", handler="interventional_pain.gate"),
            ToolDef(name="postop_safety", description="术后安全", handler="interventional_pain.postop"),
        ],
        "pain-rehab": [
            ToolDef(name="exercise_rx", description="运动处方", handler="pain_rehab.exercise"),
            ToolDef(name="assess_progress", description="进展评估", handler="pain_rehab.progress"),
            ToolDef(name="comorbidity", description="合并症", handler="pain_rehab.comorbid"),
        ],
        "medical-record": [
            ToolDef(name="get_patient", description="患者查询", handler="medical_record.get_patient"),
            ToolDef(name="get_labs", description="检验结果", handler="medical_record.get_labs"),
            ToolDef(name="get_exams", description="影像报告", handler="medical_record.get_exams"),
        ],
        "metrics": [
            ToolDef(name="get_department_metrics", description="科室指标", handler="metrics.department"),
            ToolDef(name="get_quality_metrics", description="质量指标", handler="metrics.quality"),
            ToolDef(name="get_efficiency_metrics", description="效率指标", handler="metrics.efficiency"),
        ],
    }

    for agent_name, tools in extra_tools.items():
        p = get_agent(agent_name)
        if p:
            existing = {t.name for t in p.tools}
            for t in tools:
                if t.name not in existing:
                    p.tools.append(t)
        else:
            register(DomainPlugin(name=agent_name, type="business", tools=tools))

    return count


class APIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/agents":
            agents = []
            for name, p in _registry.items():
                agents.append({
                    "name": p.name, "cn_name": p.cn_name, "type": p.type,
                    "port": p.port, "department": p.department,
                    "tools": [{"name": t.name, "description": t.description,
                               "input": t.input} for t in p.tools],
                    "sub_agents": p.sub_agents, "parent": p.parent,
                })
            self._json(agents)
        elif self.path == "/history":
            self._json(get_history(50))
        elif self.path == "/stats":
            self._json({
                "agents_loaded": len(_registry),
                "call_history": len(get_history(0)),
                "patients_loaded": len(_patients_cache),
            })
        elif self.path == "/patients" or self.path.startswith("/patients?"):
            # 支持 ?agent=xxx 过滤兼容 Agent
            agent_filter = ""
            if "?" in self.path:
                qs = self.path.split("?")[1]
                for p in qs.split("&"):
                    if p.startswith("agent="):
                        agent_filter = p[6:]
            if agent_filter and agent_filter in COMMASPACE_AGENTS:
                depts = COMMASPACE_AGENTS[agent_filter]
                filtered = [p for p in _patients_cache if p.get("department") in depts]
                self._json(filtered[:30])  # 最多 30 个匹配
            else:
                self._json(_patients_cache[:50])  # 默认返回前 50 个
        else:
            self.send_response(404)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json({"status": "error", "error": "Invalid JSON"}, 400)
            return

        if self.path == "/call":
            agent = data.get("agent", "")
            tool = data.get("tool", "")
            params = data.get("params", {})
            if not agent or not tool:
                self._json({"status": "error", "error": "Missing agent or tool"}, 400)
                return
            result = a2a_call(agent, tool, params)
            self._json(result)

        elif self.path == "/clear":
            clear_history()
            self._json({"status": "ok"})

        else:
            self.send_response(404)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))

    def log_message(self, format, *args):
        pass  # 静默日志


def main():
    init_agents()

    # 加载患者数据
    global _patients_cache, COMMASPACE_AGENTS
    if PATIENTS_FILE.exists():
        with open(PATIENTS_FILE, encoding="utf-8") as f:
            _patients_cache = json.load(f).get("patients", [])
    # 构建 Agent → 科室兼容映射
    for p in _patients_cache:
        for ag in p.get("compatible_agents", []):
            if ag not in COMMASPACE_AGENTS:
                COMMASPACE_AGENTS[ag] = []
            if p["department"] not in COMMASPACE_AGENTS[ag]:
                COMMASPACE_AGENTS[ag].append(p["department"])
    # medical-record 和 metrics 兼容所有科室
    for ag in ("medical-record", "metrics"):
        COMMASPACE_AGENTS[ag] = list(set(p["department"] for p in _patients_cache))

    port = 8800
    server = HTTPServer(("127.0.0.1", port), APIHandler)
    print(f"xhaip Demo API: http://127.0.0.1:{port}")
    print(f"  GET  /agents    — 列出所有 Agent")
    print(f"  GET  /patients  — 患者列表 (?agent=xxx 过滤)")
    print(f"  POST /call      — 调用 Agent 工具")
    print(f"  GET  /history   — 调用历史")
    print(f"  GET  /stats     — 统计信息")
    print(f"  Patients loaded: {len(_patients_cache)}")
    print(f"\nCtrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\n已停止")


if __name__ == "__main__":
    main()
