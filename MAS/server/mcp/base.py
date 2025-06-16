"""
MCP 工具基础类和注册系统
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field
import json
import logging

logger = logging.getLogger(__name__)


class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None


class ToolDefinition(BaseModel):
    """工具定义"""
    name: str
    description: str
    parameters: List[ToolParameter] = []
    returns: str = "string"  # 返回值类型描述
    
    def to_openai_function(self) -> Dict[str, Any]:
        """转换为 OpenAI 函数调用格式"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                properties[param.name]["enum"] = param.enum
            if param.required:
                required.append(param.name)
                
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPTool(ABC):
    """MCP 工具基类"""
    
    def __init__(self):
        self.definition = self._get_definition()
    
    @abstractmethod
    def _get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass
    
    def validate_parameters(self, params: Dict[str, Any]) -> Optional[str]:
        """验证参数"""
        for param in self.definition.parameters:
            if param.required and param.name not in params:
                return f"Missing required parameter: {param.name}"
            
            if param.name in params:
                value = params[param.name]
                # 基础类型验证
                if param.type == "string" and not isinstance(value, str):
                    return f"Parameter {param.name} must be a string"
                elif param.type == "number" and not isinstance(value, (int, float)):
                    return f"Parameter {param.name} must be a number"
                elif param.type == "boolean" and not isinstance(value, bool):
                    return f"Parameter {param.name} must be a boolean"
                
                # 枚举验证
                if param.enum and value not in param.enum:
                    return f"Parameter {param.name} must be one of: {param.enum}"
        
        return None


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(self, tool: MCPTool, category: str = "general"):
        """注册工具"""
        tool_name = tool.definition.name
        if tool_name in self._tools:
            logger.warning(f"Tool {tool_name} already registered, overwriting")
        
        self._tools[tool_name] = tool
        
        if category not in self._categories:
            self._categories[category] = []
        if tool_name not in self._categories[category]:
            self._categories[category].append(tool_name)
        
        logger.info(f"Registered tool: {tool_name} in category: {category}")
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """列出工具"""
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())
    
    def get_all_definitions(self) -> List[ToolDefinition]:
        """获取所有工具定义"""
        return [tool.definition for tool in self._tools.values()]
    
    def get_openai_functions(self) -> List[Dict[str, Any]]:
        """获取 OpenAI 格式的函数列表"""
        return [tool.definition.to_openai_function() for tool in self._tools.values()]
    
    async def execute_tool(self, name: str, parameters: Dict[str, Any]) -> ToolResult:
        """执行工具"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                result=None,
                error=f"Tool {name} not found"
            )
        
        # 验证参数
        error = tool.validate_parameters(parameters)
        if error:
            return ToolResult(
                success=False,
                result=None,
                error=error
            )
        
        try:
            result = await tool.execute(**parameters)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


# 全局工具注册表
tool_registry = ToolRegistry()
