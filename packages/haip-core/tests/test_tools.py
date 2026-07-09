"""测试 Tool 抽象层."""

from haip.tools import BaseTool, ToolResult
from haip.tools.registry import execute, list_all, list_schemas, register, _tools


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo back input"

    def parameters(self) -> dict:
        return {"msg": {"type": "string", "description": "Message to echo"}}

    def execute(self, msg: str = "hello", **kwargs) -> ToolResult:
        return ToolResult(success=True, output=msg, data={"echo": msg})


class FailTool(BaseTool):
    name = "fail"
    description = "Always fails"

    def execute(self, **kwargs) -> ToolResult:
        raise RuntimeError("Intentional failure")


class TestToolResult:
    def test_defaults(self):
        r = ToolResult()
        assert r.success is True
        assert r.output == ""

    def test_error(self):
        r = ToolResult(success=False, error="Something went wrong")
        assert r.success is False
        assert r.error == "Something went wrong"

    def test_with_data(self):
        r = ToolResult(data={"score": 5}, confidence=0.85)
        assert r.data["score"] == 5
        assert r.confidence == 0.85


class TestToolRegistry:
    def setup_method(self):
        _tools.clear()

    def test_register_and_list(self):
        tool = EchoTool()
        register(tool)
        assert list_all()["echo"] is tool

    def test_list_schemas(self):
        register(EchoTool())
        schemas = list_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "echo"
        assert "parameters" in schemas[0]

    def test_execute_success(self):
        register(EchoTool())
        result = execute("echo", msg="world")
        assert result.success
        assert result.output == "world"

    def test_execute_unknown_tool(self):
        result = execute("nonexistent")
        assert result.success is False
        assert "Unknown tool" in result.error

    def test_execute_failure(self):
        register(FailTool())
        result = execute("fail")
        assert result.success is False
        assert "Intentional failure" in result.error
