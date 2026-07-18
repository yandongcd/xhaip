"""检验危急值智能体 — 单元测试.

覆盖:
  - check_critical_value: 危急/非危急/边界/异常输入
  - classify_and_route: 路由推荐
  - batch_screen: 批量筛查
  - notification_record: 报告闭环记录
"""

import pytest
from lab_critical_value import (
    check_critical_value,
    classify_and_route,
    batch_screen,
    notification_record,
    CRITICAL_THRESHOLDS,
)


class TestCheckCriticalValue:
    def test_k_high_critical(self):
        """高钾: K+=6.5 -> 一级危急高值"""
        r = check_critical_value(item="K+", value=6.5)
        assert r["is_critical"] is True
        assert r["direction"] == "高值危急"
        assert r["level"] == "一级危急"

    def test_k_low_critical(self):
        """低钾: K+=2.0 -> 一级危急低值"""
        r = check_critical_value(item="K+", value=2.0)
        assert r["is_critical"] is True
        assert r["direction"] == "低值危急"
        assert r["level"] == "一级危急"

    def test_k_normal(self):
        """K+=4.0 非危急"""
        r = check_critical_value(item="K+", value=4.0)
        assert r["is_critical"] is False
        assert r["direction"] is None
        assert r["level"] is None

    def test_k_boundary_high(self):
        """高钾边界: K+=6.0 (恰好触达)"""
        r = check_critical_value(item="K+", value=6.0)
        assert r["is_critical"] is True
        assert r["direction"] == "高值危急"

    def test_k_boundary_low(self):
        """低钾边界: K+=2.5 (恰好触达)"""
        r = check_critical_value(item="K+", value=2.5)
        assert r["is_critical"] is True
        assert r["direction"] == "低值危急"

    def test_k_just_normal_low(self):
        """低钾非危急: K+=2.6 (>2.5)"""
        r = check_critical_value(item="K+", value=2.6)
        assert r["is_critical"] is False

    def test_glu_critical_high(self):
        """高血糖危急: Glu=25.0"""
        r = check_critical_value(item="Glu", value=25.0)
        assert r["is_critical"] is True
        assert r["direction"] == "高值危急"

    def test_ctni_critical(self):
        """cTnI危急: cTnI=2.0"""
        r = check_critical_value(item="cTnI", value=2.0)
        assert r["is_critical"] is True
        assert r["level"] == "一级危急"
        assert "胸痛" in (r.get("review_note") or "")

    def test_inr_critical(self):
        """INR危急: INR=5.0"""
        r = check_critical_value(item="INR", value=5.0)
        assert r["is_critical"] is True
        assert r["direction"] == "高值危急"

    def test_lac_critical(self):
        """乳酸危急: Lac=5.0"""
        r = check_critical_value(item="Lac", value=5.0)
        assert r["is_critical"] is True
        assert "液体复苏" in (r.get("review_note") or "")

    def test_ph_low_critical(self):
        """酸中毒: pH=7.1"""
        r = check_critical_value(item="pH", value=7.1)
        assert r["is_critical"] is True
        assert r["direction"] == "低值危急"

    def test_ph_high_critical(self):
        """碱中毒: pH=7.7"""
        r = check_critical_value(item="pH", value=7.7)
        assert r["is_critical"] is True
        assert r["direction"] == "高值危急"

    def test_unknown_item(self):
        """未知检验项目返回非危急"""
        r = check_critical_value(item="UnknownItem", value=100)
        assert r["is_critical"] is False
        assert r["message"] == "该项目不在危急值阈值表中"

    def test_empty_item(self):
        """空item返回error"""
        r = check_critical_value(item="", value=1.0)
        assert r["status"] == "error"
        assert r["is_critical"] is False

    def test_non_numeric_value(self):
        """非数值value返回error"""
        r = check_critical_value(item="K+", value="abc")
        assert r["status"] == "error"

    def test_extreme_value(self):
        """极端异常值检测"""
        r = check_critical_value(item="K+", value=1e15)
        assert r["status"] == "error"
        assert "数值异常" in r["message"]

    def test_unit_mismatch(self):
        """单位不匹配"""
        r = check_critical_value(item="K+", value=5.0, unit="mg/dL")
        assert r["status"] == "error"
        assert "单位不匹配" in r["message"]

    def test_hb_low_critical(self):
        """血红蛋白危急低值"""
        r = check_critical_value(item="Hb", value=40)
        assert r["is_critical"] is True
        assert r["direction"] == "低值危急"

    def test_plt_low_critical(self):
        """血小板危急低值"""
        r = check_critical_value(item="PLT", value=15)
        assert r["is_critical"] is True

    def test_wbc_high_critical(self):
        """白细胞危急高值"""
        r = check_critical_value(item="WBC", value=60)
        assert r["is_critical"] is True
        assert r["direction"] == "高值危急"

    def test_cr_critical_high(self):
        """肌酐危急"""
        r = check_critical_value(item="Cr", value=600)
        assert r["is_critical"] is True

    def test_neonatal_bilirubin_critical(self):
        """新生儿胆红素危急"""
        r = check_critical_value(item="TBil新生儿", value=400)
        assert r["is_critical"] is True

    def test_all_thresholds_have_keys(self):
        """所有阈值条目字段完整性"""
        required = {"item", "cn_name", "significance"}
        for t in CRITICAL_THRESHOLDS:
            for k in required:
                assert k in t, f"{t.get('item', '?')} 缺少 {k}"
            assert t.get("low") is not None or t.get("high") is not None, (
                f"{t['item']} 阈值未定义"
            )


class TestClassifyAndRoute:
    def test_high_k_route(self):
        """高钾->肾内/ICU"""
        r = classify_and_route(item="K+", value=6.5)
        assert r["is_critical"] is True
        assert "肾内科" in r["departments"]
        assert "ICU" in r["departments"]
        assert r["response_min"] == 10
        assert "医务处" in r["escalation"]

    def test_ctni_route_green_channel(self):
        """cTnI->胸痛绿色通道"""
        r = classify_and_route(item="cTnI", value=2.0)
        assert r["is_critical"] is True
        assert r["special_channel"] == "胸痛绿色通道"
        assert "心内科" in r["departments"]

    def test_non_critical_no_route(self):
        """非危急值不产生路由"""
        r = classify_and_route(item="K+", value=4.0)
        assert r["is_critical"] is False
        assert r["departments"] == []

    def test_patient_dept_excluded(self):
        """当前科室从路由中排除"""
        r = classify_and_route(item="K+", value=6.5, patient_dept="肾内科")
        assert "肾内科" not in r["departments"]

    def test_hb_route_transfusion(self):
        """Hb危急->输血科+急诊"""
        r = classify_and_route(item="Hb", value=40)
        assert r["is_critical"] is True
        assert "输血科" in r["departments"]

    def test_lac_route_sepsis(self):
        """Lac危急->ICU+急诊 含脓毒症标注"""
        r = classify_and_route(item="Lac", value=5.0)
        assert r["is_critical"] is True
        assert "脓毒症" in (r.get("special_note") or "")


class TestBatchScreen:
    def test_batch_mixed(self):
        """混合危急+非危急批量筛查"""
        labs = [
            {"item": "K+", "value": 6.5},      # 危急
            {"item": "Na+", "value": 140},      # 正常
            {"item": "Glu", "value": 2.0},      # 危急低值
            {"item": "Hb", "value": 120},       # 正常
            {"item": "cTnI", "value": 3.0},     # 危急
        ]
        r = batch_screen(labs=labs)
        assert r["status"] == "ok"
        assert r["hits_count"] == 3
        assert r["misses"] == 2
        assert r["total_screened"] == 5
        assert r["hits_by_level"]["一级危急"] == 3

    def test_batch_empty(self):
        """空列表返回error"""
        r = batch_screen(labs=[])
        assert r["status"] == "error"

    def test_batch_none(self):
        """None输入返回error"""
        r = batch_screen(labs=None)
        assert r["status"] == "error"

    def test_batch_sorted_by_level(self):
        """命中清单按危急级别排序"""
        labs = [
            {"item": "BUN", "value": 40},       # 二级警戒
            {"item": "K+", "value": 7.0},        # 一级危急
            {"item": "D-Dimer", "value": 6000},  # 二级警戒
            {"item": "cTnI", "value": 1.0},      # 一级危急
        ]
        r = batch_screen(labs=labs)
        assert r["hits_count"] == 4
        assert r["hits"][0]["level"] == "一级危急"
        assert r["hits"][1]["level"] == "一级危急"
        assert r["hits"][2]["level"] == "二级警戒"
        assert r["hits"][3]["level"] == "二级警戒"

    def test_batch_all_normal(self):
        """全部正常无命中"""
        labs = [
            {"item": "K+", "value": 4.0},
            {"item": "Na+", "value": 140},
            {"item": "Glu", "value": 5.0},
        ]
        r = batch_screen(labs=labs)
        assert r["hits_count"] == 0
        assert r["misses"] == 3


class TestNotificationRecord:
    def test_critical_notification(self):
        """危急值通知记录生成"""
        r = notification_record(item="K+", value=7.0, notified_to="肾内科值班医生", ack=False)
        assert r["is_critical"] is True
        assert r["notified_to"] == "肾内科值班医生"
        assert r["ack"] is False
        assert r["timeout"] is True
        assert r["record_id"].startswith("CV-")
        assert "created_at" in r
        assert r["level"] == "一级危急"
        assert r["timeout_minutes"] == 10
        assert "lis_subscription" in r
        assert r["lis_subscription"]["channel"] == "HL7-ORU-R01"

    def test_notification_acked(self):
        """已确认的通知记录"""
        r = notification_record(item="cTnI", value=1.5, notified_to="心内科", ack=True)
        assert r["ack"] is True
        assert r["timeout"] is False
        assert r["ack_at"] is not None

    def test_non_critical_no_record(self):
        """非危急值无记录"""
        r = notification_record(item="K+", value=4.0, notified_to="any")
        assert r["is_critical"] is False
        assert r["record_id"] is None
        assert r["message"] == "非危急值无需报告记录"

    def test_second_level_timeout(self):
        """二级警戒超时30分钟"""
        r = notification_record(item="D-Dimer", value=6000, notified_to="呼吸科", ack=False)
        assert r["level"] == "二级警戒"
        assert r["timeout_minutes"] == 30


class TestThresholdTable:
    def test_threshold_count(self):
        """阈值表至少20条"""
        assert len(CRITICAL_THRESHOLDS) >= 20, f"阈值表仅{len(CRITICAL_THRESHOLDS)}条"
