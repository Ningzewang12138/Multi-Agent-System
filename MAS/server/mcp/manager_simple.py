"""
MCP 管理器 - 协调工具调用和 LLM 交互（简化版）
"""
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from .base import tool_registry, ToolResult
from .tools.filesystem import register_file_tools
from .tools.web import register_web_tools
from .tools.data import register_data_tools
# 暂时注释掉有问题的导入
# from .tools.map import register_map_tools
# from .tools.test_tools import register_test_tools

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResponse:
    """工具调用响应"""
    tool_call_id: str
    content: str
    success: bool


class MCPManager:
    """MCP 管理器"""
    
    def __init__(self):
        self.registry = tool_registry
        self._initialized = False
        self._tool_use_history: List[Dict[str, Any]] = []
    
    def initialize(self):
        """初始化并注册所有工具"""
        if self._initialized:
            return
        
        # 注册各类工具
        register_file_tools(self.registry)
        register_web_tools(self.registry)
        register_data_tools(self.registry)
        # 暂时禁用有问题的工具
        # register_map_tools(self.registry)
        # register_test_tools(self.registry)
        
        self._initialized = True
        logger.info(f"MCP Manager initialized with {len(self.registry.list_tools())} tools")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表（OpenAI 格式）"""
        if not self._initialized:
            self.initialize()
        
        return self.registry.get_openai_functions()
    
    def get_tools_by_category(self, category: Optional[str] = None) -> List[str]:
        """按类别获取工具"""
        if not self._initialized:
            self.initialize()
        
        return self.registry.list_tools(category)
    
    async def execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[ToolResponse]:
        """执行工具调用"""
        if not self._initialized:
            self.initialize()
        
        responses = []
        
        for call in tool_calls:
            try:
                # 执行工具
                result = await self.registry.execute_tool(
                    name=call.name,
                    parameters=call.arguments
                )
                
                # 记录历史
                self._tool_use_history.append({
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "arguments": call.arguments,
                    "result": result.dict()
                })
                
                # 构建响应
                if result.success:
                    content = json.dumps({
                        "result": result.result,
                        "metadata": result.metadata
                    }, ensure_ascii=False)
                else:
                    content = json.dumps({
                        "error": result.error
                    }, ensure_ascii=False)
                
                responses.append(ToolResponse(
                    tool_call_id=call.id,
                    content=content,
                    success=result.success
                ))
                
            except Exception as e:
                logger.error(f"Error executing tool {call.name}: {e}")
                responses.append(ToolResponse(
                    tool_call_id=call.id,
                    content=json.dumps({"error": str(e)}),
                    success=False
                ))
        
        return responses
    
    def parse_tool_calls(self, llm_response: Dict[str, Any]) -> List[ToolCall]:
        """从 LLM 响应中解析工具调用"""
        tool_calls = []
        
        # 支持 OpenAI 格式
        if "tool_calls" in llm_response:
            for call in llm_response["tool_calls"]:
                if call["type"] == "function":
                    tool_calls.append(ToolCall(
                        id=call["id"],
                        name=call["function"]["name"],
                        arguments=json.loads(call["function"]["arguments"])
                    ))
        
        # 支持自定义格式
        elif "function_call" in llm_response:
            func = llm_response["function_call"]
            tool_calls.append(ToolCall(
                id=func.get("id", "call_1"),
                name=func["name"],
                arguments=json.loads(func.get("arguments", "{}"))
            ))
        
        return tool_calls
    
    def format_tool_response_for_llm(self, responses: List[ToolResponse]) -> str:
        """格式化工具响应供 LLM 使用"""
        formatted = []
        
        for response in responses:
            if response.success:
                formatted.append(f"Tool {response.tool_call_id} returned:\n{response.content}")
            else:
                formatted.append(f"Tool {response.tool_call_id} failed:\n{response.content}")
        
        return "\n\n".join(formatted)
    
    def get_tool_use_history(self) -> List[Dict[str, Any]]:
        """获取工具使用历史"""
        return self._tool_use_history
    
    def clear_history(self):
        """清除历史记录"""
        self._tool_use_history = []


# 全局 MCP 管理器实例
mcp_manager = MCPManager()
