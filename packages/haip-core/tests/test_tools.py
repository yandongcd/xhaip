"""Tests for haip.tools — base tool abstraction."""

import pytest
from haip.tools import BaseTool, ToolResult


class TestToolResult:
    def test_success_result(self):
        result = ToolResult(success=True, output="ok")
        assert result.success is True
        assert result.output == "ok"
        assert result.error == ""

    def test_failure_result(self):
        result = ToolResult(success=False, error="bad")
        assert result.success is False
        assert result.error == "bad"

    def test_result_with_citations(self):
        result = ToolResult(
            success=True,
            output="diagnosis",
            citations=[{"title": "CMA指南", "url": "https://cma.org"}, {"title": "NCCN v3"}],
            confidence=0.85,
        )
        assert len(result.citations) == 2
        assert result.citations[0]["title"] == "CMA指南"
        assert result.confidence == 0.85

    def test_result_with_data(self):
        result = ToolResult(success=True, output="ok", data={"items": [1, 2, 3]})
        assert result.data["items"] == [1, 2, 3]

    def test_default_values(self):
        result = ToolResult(success=True)
        assert result.output == ""
        assert result.error == ""
        assert result.data == {}
        assert result.citations == []
        assert result.confidence == 0.0


class TestBaseTool:
    def test_concrete_tool(self):
        class MyTool(BaseTool):
            name = "my_tool"
            description = "test tool"

            def parameters(self) -> dict:
                return {"param1": "str"}

            def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, output=f"done: {kwargs}")

        tool = MyTool()
        assert tool.name == "my_tool"
        result = tool.execute(param1="hello")
        assert result.success is True
        assert "hello" in result.output

    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseTool()

    def test_default_parameters(self):
        class SimpleTool(BaseTool):
            name = "s"
            description = "d"
            def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True)

        assert SimpleTool().parameters() == {}
