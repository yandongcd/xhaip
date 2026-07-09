"""疼痛中枢 — 分诊 + 结果聚合."""

def triage(pain_type: str = "", vas_score: int = 0, description: str = "", **kwargs):
    route_to = "pain-hub"
    urgency = "routine"

    if vas_score >= 7 or "emergency" in description.lower():
        urgency = "urgent"

    pt = pain_type.lower()
    if "cancer" in pt:
        route_to = "cancer-pain"
    elif "acute" in pt or "post" in pt or vas_score >= 7:
        route_to = "acute-pain"
    elif "chronic" in pt or "history" in pt:
        route_to = "chronic-pain"
    elif "injection" in pt or "block" in pt or "interventional" in pt:
        route_to = "interventional-pain"
    elif "rehab" in pt or "physio" in pt:
        route_to = "pain-rehab"

    red_flags = []
    if "cauda" in description.lower() or "equina" in description.lower():
        red_flags.append("cauda_equina_syndrome")
        urgency = "critical"
    if "cancer" in description.lower() and "history" in description.lower():
        red_flags.append("cancer_history")

    return {
        "vas_score": vas_score, "pain_type": pain_type,
        "route_to": route_to, "urgency": urgency,
        "red_flags": red_flags, "severity": "critical" if red_flags else "moderate",
    }


def merge(results: list | None = None, **kwargs):
    results = results or []
    return {
        "total_agents": len(results),
        "summary": [r.get("route_to", r.get("diagnosis", "")) for r in results],
        "aggregated": True,
    }
