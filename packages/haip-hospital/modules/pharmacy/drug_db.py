"""药剂科 药品数据库查询 — 20+ TPN 药品 + 肠内营养产品 + CRUD.

Port from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

from typing import Any

# ── 肠外营养药品数据库 ──
DRUGS: list[dict[str, Any]] = [
    # 氨基酸类
    {"name": "(丰海)复方氨基酸注射液(18AA)", "spec": "250ml/瓶", "type": "氨基酸",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 25.0, "nitrogen_g": 4.0, "kcal": 100.0, "osm": "~850"},
    {"name": "小儿复方氨基酸注射液(19AA-I)", "spec": "100ml/瓶", "type": "氨基酸",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 6.0, "nitrogen_g": 0.96, "kcal": 24.0, "osm": "~600"},
    # 葡萄糖/基础溶媒
    {"name": "50%葡萄糖注射液(辰欣)", "spec": "100ml/瓶", "type": "葡萄糖",
     "glucose_g": 50.0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 200.0, "osm": "~2500"},
    {"name": "10%葡萄糖注射液", "spec": "250ml/袋", "type": "葡萄糖",
     "glucose_g": 25.0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 100.0, "osm": "~500"},
    {"name": "5%葡萄糖注射液", "spec": "250ml/袋", "type": "葡萄糖",
     "glucose_g": 12.5, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 50.0, "osm": "~250"},
    {"name": "5%葡萄糖氯化钠注射液", "spec": "250ml/袋", "type": "葡萄糖",
     "glucose_g": 12.5, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 50.0, "osm": "~550", "cation_info": "Na:0.77mmol/ml"},
    {"name": "0.9%氯化钠注射液", "spec": "250ml/袋", "type": "电解质",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 0, "osm": "~308", "cation_info": "Na:0.15mmol/ml"},
    # 脂肪乳类
    {"name": "(尤文)ω-3鱼油脂肪乳注射液", "spec": "100ml/瓶", "type": "脂肪乳",
     "glucose_g": 0, "fat_g": 10.0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 90.0, "osm": "~300"},
    {"name": "(力能)20%脂肪乳(中/长链)注射液", "spec": "250ml/瓶", "type": "脂肪乳",
     "glucose_g": 0, "fat_g": 50.0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 450.0, "osm": "~350"},
    {"name": "(合文)多种油脂肪乳注射液(C6-24)", "spec": "100ml/瓶", "type": "脂肪乳",
     "glucose_g": 0, "fat_g": 20.0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 200.0, "osm": "~320"},
    # 工业三腔袋
    {"name": "(卡文)脂肪乳氨基酸(17)葡萄糖(11%)", "spec": "1440ml/袋", "type": "三腔袋",
     "glucose_g": 96.0, "fat_g": 50.0, "amino_acid_g": 48.0, "nitrogen_g": 7.7, "kcal": 1000.0, "osm": "~750"},
    {"name": "(多特)脂肪乳氨基酸(17)葡萄糖(11%)", "spec": "1920ml/袋", "type": "三腔袋",
     "glucose_g": 128.0, "fat_g": 66.0, "amino_acid_g": 64.0, "nitrogen_g": 10.2, "kcal": 1350.0, "osm": "~750"},
    {"name": "(力卡文)结构脂肪乳氨基酸(16)葡萄糖", "spec": "1206ml/袋", "type": "三腔袋",
     "glucose_g": 84.4, "fat_g": 38.0, "amino_acid_g": 40.0, "nitrogen_g": 6.4, "kcal": 850.0, "osm": "~800"},
    # 电解质
    {"name": "10%氯化钾注射液", "spec": "10ml:1g", "type": "电解质",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 0, "osm": "~2000", "cation_info": "K:1.34mmol/ml"},
    {"name": "10%氯化钠注射液", "spec": "10ml:1g", "type": "电解质",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 0, "osm": "~2000", "cation_info": "Na:1.71mmol/ml"},
    {"name": "25%硫酸镁注射液", "spec": "10ml:2.5g", "type": "电解质",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 0, "osm": "~1000", "cation_info": "Mg:1.0mmol/ml(2价)"},
    {"name": "10%葡萄糖酸钙注射液", "spec": "10ml:1g", "type": "电解质",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 0, "osm": "~600", "cation_info": "Ca:0.23mmol/ml(2价)"},
    # 微量元素 + 维生素
    {"name": "多种微量元素注射液(II)", "spec": "10ml", "type": "微量元素",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 0, "osm": "~1000"},
    {"name": "脂溶性维生素注射液(II)", "spec": "10ml", "type": "维生素",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 0, "osm": "~500"},
    {"name": "注射用水溶性维生素", "spec": "1瓶", "type": "维生素",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 0, "osm": "~300"},
    {"name": "胰岛素注射液", "spec": "10ml:400IU", "type": "其他",
     "glucose_g": 0, "fat_g": 0, "amino_acid_g": 0, "nitrogen_g": 0, "kcal": 0, "osm": ""},
]

# ── 肠内营养产品数据库 ──
ENTERAL_PRODUCTS: list[dict[str, Any]] = [
    {"name": "能全素(Nutrison)", "spec": "500ml/瓶(1kcal/ml)", "protein_g": 4.0, "fat_g": 3.9,
     "carb_g": 12.3, "kcal_per_100ml": 100},
    {"name": "百普力(Peptisorb)", "spec": "500ml/瓶(1kcal/ml)", "protein_g": 4.0, "fat_g": 1.7,
     "carb_g": 17.6, "kcal_per_100ml": 100},
    {"name": "瑞代(Glucerna)", "spec": "500ml/瓶(0.9kcal/ml)", "protein_g": 4.2, "fat_g": 3.2,
     "carb_g": 10.6, "kcal_per_100ml": 90},
    {"name": "瑞素(Fresubin)", "spec": "500ml/瓶(1kcal/ml)", "protein_g": 3.8, "fat_g": 3.4,
     "carb_g": 13.8, "kcal_per_100ml": 100},
    {"name": "能全力(Nutrison MF)", "spec": "500ml/瓶(1.5kcal/ml)", "protein_g": 6.0, "fat_g": 5.8,
     "carb_g": 18.5, "kcal_per_100ml": 150},
]

# Backward-compatible sample drugs
_SAMPLE_DRUGS = [
    {"name": "华法林", "generic": "Warfarin", "spec": "2.5mg", "category": "抗凝药"},
    {"name": "低分子肝素", "generic": "Enoxaparin", "spec": "4000IU", "category": "抗凝药"},
    {"name": "阿莫西林", "generic": "Amoxicillin", "spec": "0.5g", "category": "抗生素"},
    {"name": "头孢曲松", "generic": "Ceftriaxone", "spec": "1g", "category": "抗生素"},
    {"name": "吗啡", "generic": "Morphine", "spec": "10mg", "category": "镇痛药"},
    {"name": "布洛芬", "generic": "Ibuprofen", "spec": "200mg", "category": "NSAIDs"},
    {"name": "呋塞米", "generic": "Furosemide", "spec": "20mg", "category": "利尿剂"},
    {"name": "庆大霉素", "generic": "Gentamicin", "spec": "80mg", "category": "抗生素"},
    {"name": "甲硝唑", "generic": "Metronidazole", "spec": "0.5g", "category": "抗生素"},
]


def search(keyword: str = "", **kwargs: Any) -> dict[str, Any]:
    """药品搜索 — 支持通用名 + 商品名模糊匹配."""
    results = [d for d in _SAMPLE_DRUGS if
               keyword.lower() in d["name"].lower() or keyword.lower() in d["generic"].lower()]
    return {"keyword": keyword, "found": len(results), "results": results}


def get_all_medications(**kwargs: Any) -> dict[str, Any]:
    """获取全部 TPN 药品目录 (20+ 药物)."""
    return {"found": len(DRUGS), "results": DRUGS}


def get_enteral_products(**kwargs: Any) -> dict[str, Any]:
    """获取肠内营养产品目录."""
    return {"found": len(ENTERAL_PRODUCTS), "results": ENTERAL_PRODUCTS}


def get_drug_params(drug_name: str = "", **kwargs: Any) -> dict[str, Any]:
    """根据药品名查询参数."""
    matches = [d for d in DRUGS if drug_name in d.get("name", "")]
    if len(matches) == 1:
        return {"found": 1, "drug": matches[0]}
    return {"found": len(matches), "results": matches}


def search_by_type(drug_type: str = "", **kwargs: Any) -> dict[str, Any]:
    """按类别筛选药品."""
    results = [d for d in DRUGS if d.get("type", "") == drug_type]
    return {"drug_type": drug_type, "found": len(results), "results": results}
