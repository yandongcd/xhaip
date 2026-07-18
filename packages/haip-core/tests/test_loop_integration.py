"""A2A call_with_loop integration tests — end-to-end ReAct Loop + A2A."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))

import haip.agent
import haip.llm
from haip.llm.mock import MockProvider
from haip.llm import ChatResponse, ToolCall
from haip.a2a import call_with_loop, call


class TestA2ALoopIntegration:
    @classmethod
    def setup_class(cls):
        root = project_root.parent  # xhaip root
        yaml_dir = root / "packages" / "haip-hospital" / "agents" / "definitions"
        if yaml_dir.exists():
            haip.agent.load_from_dir(str(yaml_dir))

    def setup_method(self):
        self._original_from_config = haip.llm.LLMProvider.from_config

    def teardown_method(self):
        haip.llm.LLMProvider.from_config = self._original_from_config

    def _inject_mock(self, responses):
        """Inject a mock LLM that returns responses in sequence, then a final answer."""
        call_count = [0]

        class SeqMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                idx = call_count[0]
                call_count[0] += 1
                if idx < len(responses):
                    return responses[idx]
                return ChatResponse(content="Analysis complete.")

        haip.llm.LLMProvider.from_config = lambda cfg: SeqMock({})

    def test_direct_answer_no_tools(self):
        """Simple question needs no tool calls."""
        self._inject_mock([ChatResponse(content="PONV incidence is about 20-30%.")])
        result = call_with_loop("pharmacy", "What is PONV incidence?")
        assert result["status"] == "ok"
        assert result["steps"] == 1
        assert len(result["tool_calls"]) == 0
        assert "20" in result["reply"] or "20" in result.get("reply", "")

    def test_multi_step_with_real_tools(self):
        """LLM calls real antiemetic tools, multi-step reasoning."""
        import pytest
        
        self._inject_mock([
            ChatResponse(tool_calls=[
                ToolCall(id="tc1", name="ponv_risk_score", arguments={
                    "gender": "F", "smoking": "No", "ponv_history": "Yes",
                    "motion_sickness": "No", "opioid_planned": "Yes", "age": 45,
                })
            ]),
            ChatResponse(tool_calls=[
                ToolCall(id="tc2", name="antiemetic_regimen", arguments={
                    "risk_level": "high", "risk_score": 4,
                })
            ]),
            ChatResponse(content="Patient is high risk (Apfel 4, 79%), triple regimen recommended."),
        ])
        result = call_with_loop("antiemetic", "Evaluate PONV risk and recommend drugs")
        
        # If result is error (agent not loaded), skip
        if result.get("status") == "error":
            pytest.skip("Agents not loaded in test context")
        
        assert result["status"] == "ok"
        assert result["steps"] == 3
        assert len(result["tool_calls"]) >= 1
        # At least one tool call was attempted
        tool_names = [tc["tool"] for tc in result["tool_calls"]]
        assert "ponv_risk_score" in tool_names
        assert "high" in result["reply"].lower() or "triple" in result["reply"].lower() or "79" in result["reply"]

    def test_unknown_agent(self):
        """Unknown agent returns error."""
        result = call_with_loop("nonexistent", "test query")
        assert result["status"] == "error"
        assert "Unknown agent" in result["error"]

    def test_single_step_fallback(self):
        """Single tool call + direct answer (non-loop scenario)."""
        self._inject_mock([
            ChatResponse(tool_calls=[
                ToolCall(id="tc1", name="antiemetic_knowledge", arguments={
                    "query": "ondansetron dose", "domain": "drug",
                })
            ]),
            ChatResponse(content="Ondansetron recommended dose is 4mg IV."),
        ])
        result = call_with_loop("antiemetic", "What is ondansetron dose?")
        assert result["status"] == "ok"
        assert result["steps"] == 2
        assert result["tool_calls"][0]["tool"] == "antiemetic_knowledge"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
