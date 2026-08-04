"""审查补测: register 权限强制 / ci_decontamination_gate / evolution_hook."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))


# ── register 强制最低权限 intern (安全: 自注册不得提权) ──


class TestRegisterLeastPrivilege:
    def test_register_forces_intern_role(self, monkeypatch):
        from fastapi.testclient import TestClient
        monkeypatch.setenv("HAIP_TEST_MODE", "true")
        from haip.web_server import app

        client = TestClient(app)
        r = client.post("/api/auth/register", json={
            "username": "least_priv_user", "password": "Doctor@123",
        })
        assert r.status_code == 200
        user = r.json()["user"]
        assert user["roles"] == ["intern"], f"自注册用户应强制 intern: {user['roles']}"
        perms = user.get("permissions", [])
        assert "agent:execute" not in perms
        assert "admin:*" not in perms

    def test_register_duplicate_400(self, monkeypatch):
        from fastapi.testclient import TestClient
        monkeypatch.setenv("HAIP_TEST_MODE", "true")
        from haip.web_server import app

        client = TestClient(app)
        body = {"username": "dup_user", "password": "Doctor@123"}
        assert client.post("/api/auth/register", json=body).status_code == 200
        r = client.post("/api/auth/register", json=body)
        assert r.status_code == 400

    def test_register_weak_password_400(self, monkeypatch):
        from fastapi.testclient import TestClient
        monkeypatch.setenv("HAIP_TEST_MODE", "true")
        from haip.web_server import app

        client = TestClient(app)
        r = client.post("/api/auth/register", json={
            "username": "weak_user", "password": "weak",
        })
        assert r.status_code == 400


# ── ci_decontamination_gate (eval 去污染门禁) ──


class TestDecontaminationGate:
    def test_no_contamination_passes(self, tmp_path):
        from haip.eval.decontaminate import ci_decontamination_gate
        ref = tmp_path / "ref.yaml"
        corpus = tmp_path / "corpus.yaml"
        ref.write_text("指南: 髋部骨折 48 小时手术窗口 评估 风险 分层", encoding="utf-8")
        corpus.write_text("评测: 患者主诉 咳嗽 三日 影像 检查 提示 肺炎 可能性", encoding="utf-8")
        r = ci_decontamination_gate(
            corpus_paths=[str(corpus)], ref_paths=[str(ref)], warn_threshold=0.15, fail_threshold=0.30)
        assert r["passed"] is True
        assert r["flagged"] == 0

    def test_identical_text_fails(self, tmp_path):
        from haip.eval.decontaminate import ci_decontamination_gate
        ref = tmp_path / "ref.yaml"
        corpus = tmp_path / "corpus.yaml"
        text = "老年髋部骨折诊疗指南 手术时机 48小时 术前评估 血栓预防 早期康复"
        ref.write_text(text, encoding="utf-8")
        corpus.write_text(text, encoding="utf-8")
        r = ci_decontamination_gate(
            corpus_paths=[str(corpus)], ref_paths=[str(ref)], warn_threshold=0.15, fail_threshold=0.30)
        assert r["passed"] is False
        assert len(r["failures"]) >= 1

    def test_warn_below_fail_threshold(self, tmp_path):
        from haip.eval.decontaminate import ci_decontamination_gate
        ref = tmp_path / "ref.yaml"
        corpus = tmp_path / "corpus.yaml"
        ref.write_text("指南 髋部骨折 手术 时机 48 小时 窗口 评估 风险 分层 决策 术前 优化", encoding="utf-8")
        corpus.write_text("评测 髋部骨折 手术 时机 窗口 结合 患者 合并症 分析 决策 建议", encoding="utf-8")
        r = ci_decontamination_gate(
            corpus_paths=[str(corpus)], ref_paths=[str(ref)], warn_threshold=0.15, fail_threshold=0.30)
        assert len(r["failures"]) == 0, f"不应 fail: {r['failures']}"

    def test_missing_files_ignored(self, tmp_path):
        from haip.eval.decontaminate import ci_decontamination_gate
        r = ci_decontamination_gate(
            corpus_paths=[str(tmp_path / "nope.yaml")], ref_paths=[str(tmp_path / "missing.yaml")])
        assert r["total_corpus"] == 0


# ── evolution_hook (L6 进化钩子) ──


def _register_learning_agent(name: str = "evo-test-agent", learning: bool = True) -> None:
    """注册带/不带 learning 配置的测试 agent."""
    from haip.agent import DomainPlugin, ToolDef, _registry, register

    _registry.clear()
    learning_cfg = {"enabled": True} if learning else None
    plugin = DomainPlugin(
        name=name, type="business",
        tools=[ToolDef(name="timing_decision", description="手术时机")],
        learning=learning_cfg,
    )
    register(plugin)


class TestEvolutionHook:
    def test_non_ok_status_returns_immediately(self):
        from haip.evolution.hook import evolution_hook
        assert evolution_hook("orthopedic-surgery", "timing_decision", "error") is None

    def test_unknown_agent_returns(self):
        from haip.evolution.hook import evolution_hook
        assert evolution_hook("ghost-agent", "tool", "ok") is None

    def test_agent_without_learning_returns(self):
        from haip.evolution.hook import evolution_hook
        _register_learning_agent("evo-no-learn", learning=False)
        assert evolution_hook("evo-no-learn", "timing_decision", "ok", {"urgency": "urgent"}) is None

    def test_ok_with_gold_calls_evolve(self, monkeypatch):
        from haip.evolution.hook import evolution_hook
        _register_learning_agent("evo-learn", learning=True)
        calls = {}

        def fake_lookup_gold(agent, tool, result):
            return {"urgency": "urgent"}

        def fake_evolve(eval_runner, report, agent=None):
            calls["evolved"] = (eval_runner, agent)
            return {"action": "adopt"}

        monkeypatch.setattr("haip.evolution.hook._lookup_gold", fake_lookup_gold)
        monkeypatch.setattr("haip.evolution.engine.evolve_from_eval", fake_evolve)
        evolution_hook("evo-learn", "timing_decision", "ok", {"urgency": "urgent"})
        assert calls.get("evolved") is not None
        assert calls["evolved"][1] == "evo-learn"

    def test_no_gold_skips(self, monkeypatch):
        from haip.evolution.hook import evolution_hook
        _register_learning_agent("evo-no-gold", learning=True)
        monkeypatch.setattr("haip.evolution.hook._lookup_gold", lambda a, t, r: None)
        assert evolution_hook("evo-no-gold", "timing_decision", "ok", {}) is None

    def test_exception_silent(self, monkeypatch):
        """fire-and-forget: 任何异常不向调用方传播."""
        from haip.evolution.hook import evolution_hook
        _register_learning_agent("evo-boom", learning=True)

        def boom(agent, tool, result):
            raise RuntimeError("kg down")

        monkeypatch.setattr("haip.evolution.hook._lookup_gold", boom)
        assert evolution_hook("evo-boom", "timing_decision", "ok", {}) is None
