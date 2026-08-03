"""多语言嗓音健康 — 声学评估 + 语言路由 + 国际患者引导."""
from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="voice-health", department="惠侨医疗中心")
_GUIDELINES = ["ASHA 美国言语-语言-听力协会嗓音评估标准(2025)", "中华医学会耳鼻咽喉头颈外科学分会嗓音疾病诊疗指南(2024)"]
_agent.rule_engine.load_all()

def voice_assess(**kwargs) -> dict:
    f0 = float(kwargs.get("F0", 120) or 120); jitter = float(kwargs.get("Jitter", 1.0) or 1.0)
    shimmer = float(kwargs.get("Shimmer", 3.0) or 3.0); hnr = float(kwargs.get("HNR", 20) or 20); mpt = float(kwargs.get("MPT", 15) or 15)
    abn = []; grade = "G0(正常)"
    if jitter > 1.04: abn.append("Jitter↑ — 音调微扰异常"); grade = "G1(轻度)" if grade == "G0(正常)" else grade
    if shimmer > 3.81: abn.append("Shimmer↑ — 振幅微扰异常"); grade = "G2(中度)" if jitter > 2 else "G1(轻度)"
    if hnr < 15: abn.append("HNR↓ — 嗓音质量下降"); grade = "G2(中度)"
    if mpt < 10: abn.append("MPT↓ — 呼吸支持不足")
    if not abn: abn.append("声学参数在正常范围")
    return {"status": "ok", "grade": grade, "abnormalities": abn, "F0": f0, "summary": f"GRBAS — {grade}"}

def language_routing(**kwargs) -> dict:
    query = kwargs.get("query", ""); lang = kwargs.get("target_language", "zh")
    response = {"zh": "您好！惠侨医疗中心为您服务。", "en": "Hello! Huigiao Medical Center at your service.", "ja": "こんにちは！惠僑医療センターがご案内します。", "ko": "안녕하세요! 혜교의료센터입니다."}
    return {"status": "ok", "lang": lang, "response": response.get(lang, response["en"]), "query": query[:100]}

def referral_guide(**kwargs) -> dict:
    country = kwargs.get("country", ""); condition = kwargs.get("condition", "")
    return {"status": "ok", "steps": ["1. 国际医疗部预约(电话/邮件/微信)", "2. 病历翻译(中/英/日)", "3. 专科分诊+预约挂号", "4. 就诊+检查+MDT", "5. 保险直付/费用预缴"], "summary": f"国际患者就诊引导 — {country} / {condition}"}
