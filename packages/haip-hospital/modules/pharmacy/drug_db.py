"""药剂科 药品数据库查询."""

_SAMPLE_DRUGS = [
    {"name": "华法林", "generic": "Warfarin", "spec": "2.5mg", "category": "抗凝药"},
    {"name": "低分子肝素", "generic": "Enoxaparin", "spec": "4000IU", "category": "抗凝药"},
    {"name": "阿莫西林", "generic": "Amoxicillin", "spec": "0.5g", "category": "抗生素"},
    {"name": "头孢曲松", "generic": "Ceftriaxone", "spec": "1g", "category": "抗生素"},
    {"name": "吗啡", "generic": "Morphine", "spec": "10mg", "category": "镇痛药"},
    {"name": "布洛芬", "generic": "Ibuprofen", "spec": "200mg", "category": "NSAIDs"},
]

def search(keyword: str = "", **kwargs):
    results = [d for d in _SAMPLE_DRUGS if keyword.lower() in d["name"].lower()
               or keyword.lower() in d["generic"].lower()]
    return {"keyword": keyword, "found": len(results), "results": results}
