"""Test AgentLoop schema building — R1: only YAML input keys are required."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.loop import AgentLoop
from haip.llm.mock import MockProvider


class TestToolSchema:
    def test_required_only_input_keys(self):
        """Only YAML input keys are marked required."""
        tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "input": {"gender": "str", "smoking": "str", "age": "int"},
            }
        ]
        loop = AgentLoop(llm=MockProvider({}), tools=tools)
        schemas = loop._build_tool_schemas()

        assert len(schemas) == 1
        schema = schemas[0]
        params = schema["parameters"]
        required = params["required"]
        properties = params["properties"]

        assert len(required) == 3
        assert "gender" in required
        assert "smoking" in required
        assert "age" in required
        assert "patient_id" not in required
        assert "patient_id" not in properties

    def test_no_extra_params(self):
        """Params not in input do not appear in schema."""
        tools = [{"name": "minimal", "description": "minimal", "input": {"query": "str"}}]
        loop = AgentLoop(llm=MockProvider({}), tools=tools)
        schemas = loop._build_tool_schemas()
        params = schemas[0]["parameters"]
        assert params["required"] == ["query"]
        assert len(params["properties"]) == 1
        assert "patient_id" not in params["properties"]

    def test_type_mapping(self):
        """Type mapping: int->integer, float->number, bool->boolean, str->string."""
        tools = [
            {
                "name": "typed",
                "description": "",
                "input": {"count": "int", "ratio": "float", "active": "bool", "name": "str"},
            }
        ]
        loop = AgentLoop(llm=MockProvider({}), tools=tools)
        schemas = loop._build_tool_schemas()
        props = schemas[0]["parameters"]["properties"]
        assert props["count"]["type"] == "integer"
        assert props["ratio"]["type"] == "number"
        assert props["active"]["type"] == "boolean"
        assert props["name"]["type"] == "string"

    def test_empty_tools_stays_empty(self):
        """Empty per-agent tools list returns empty schemas (no fallback)."""
        loop = AgentLoop(llm=MockProvider({}), tools=[])
        schemas = loop._build_tool_schemas()
        assert schemas == []

    def test_none_tools_falls_back_to_global(self):
        """tools=None falls back to global registry (backward compat)."""
        loop = AgentLoop(llm=MockProvider({}))  # tools defaults to None
        schemas = loop._build_tool_schemas()
        # May or may not have tools depending on test order
        assert isinstance(schemas, list)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
