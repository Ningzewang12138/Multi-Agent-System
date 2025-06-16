"""
测试 MCP 工具
用于验证MCP功能是否正常工作
"""
import logging
from datetime import datetime
from typing import Optional

from ..base import MCPTool, ToolDefinition, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class TestHelloTool(MCPTool):
    """简单的测试问候工具"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="test_hello",
            description="简单的测试工具，返回问候消息",
            parameters=[
                ToolParameter(
                    name="name",
                    type="string",
                    description="要问候的名字",
                    required=True
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="问候语言",
                    required=False,
                    default="中文",
                    enum=["中文", "English", "日本語", "Español"]
                )
            ]
        )
    
    async def execute(self, name: str, language: str = "中文") -> ToolResult:
        """执行问候"""
        try:
            greetings = {
                "中文": f"你好，{name}！欢迎使用MCP服务。",
                "English": f"Hello, {name}! Welcome to MCP services.",
                "日本語": f"こんにちは、{name}さん！MCPサービスへようこそ。",
                "Español": f"¡Hola, {name}! Bienvenido a los servicios MCP."
            }
            
            message = greetings.get(language, greetings["中文"])
            
            # 生成测试文件
            content = f"""
{'='*50}
MCP测试结果
{'='*50}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
名字: {name}
语言: {language}

{message}

这是一个测试文件，用于验证MCP工作空间功能是否正常。
如果您能看到这个文件，说明MCP服务运行正常！
{'='*50}
"""
            
            return ToolResult(
                success=True,
                result={
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                },
                metadata={
                    "output_file": {
                        "name": f"test_hello_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        "content": content
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error in test_hello: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )


class TestCalculationTool(MCPTool):
    """简单的计算测试工具"""
    
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="test_calculation",
            description="简单的计算测试工具",
            parameters=[
                ToolParameter(
                    name="a",
                    type="number",
                    description="第一个数字",
                    required=True
                ),
                ToolParameter(
                    name="b",
                    type="number",
                    description="第二个数字",
                    required=True
                ),
                ToolParameter(
                    name="operation",
                    type="string",
                    description="运算类型",
                    required=False,
                    default="add",
                    enum=["add", "subtract", "multiply", "divide"]
                )
            ]
        )
    
    async def execute(self, a: float, b: float, operation: str = "add") -> ToolResult:
        """执行计算"""
        try:
            operations = {
                "add": (a + b, f"{a} + {b} = {a + b}"),
                "subtract": (a - b, f"{a} - {b} = {a - b}"),
                "multiply": (a * b, f"{a} × {b} = {a * b}"),
                "divide": (a / b if b != 0 else None, f"{a} ÷ {b} = {a / b if b != 0 else '错误：除数不能为0'}")
            }
            
            result, expression = operations.get(operation, operations["add"])
            
            if result is None:
                return ToolResult(
                    success=False,
                    error="除数不能为0"
                )
            
            return ToolResult(
                success=True,
                result={
                    "calculation": expression,
                    "result": result,
                    "operation": operation
                }
            )
            
        except Exception as e:
            logger.error(f"Error in test_calculation: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )


def register_test_tools(registry):
    """注册测试工具"""
    registry.register(TestHelloTool(), category="general")
    registry.register(TestCalculationTool(), category="general")
    logger.info("Test tools registered")
