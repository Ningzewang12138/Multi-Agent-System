"""
最简化的工具增强聊天服务
使用最直接的提示格式
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import logging
import uuid
import re
import time

from server.services.ollama_service import OllamaService
from server.mcp.manager import mcp_manager
from server.services.mcp_workspace_service import workspace_service

logger = logging.getLogger(__name__)


class ToolEnhancedChatService:
    """支持工具调用的聊天服务（简化版）"""
    
    def __init__(self, ollama_service: OllamaService):
        self.ollama = ollama_service
        self.mcp = mcp_manager
        
    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.7,
        session_id: Optional[str] = None,
        device_id: str = "default",
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行带工具调用的聊天"""
        
        # 确保MCP管理器已初始化
        if not self.mcp._initialized:
            self.mcp.initialize()
        
        # 创建或获取会话ID
        if not session_id:
            session_id = f"chat_{uuid.uuid4().hex[:8]}"
        
        # 创建工作空间
        _, workspace_path = workspace_service.create_workspace(
            device_id=device_id,
            session_id=session_id
        )
        
        # 如果没有工具或tool_choice是none，直接调用
        if not tools or tool_choice == "none":
            response = self.ollama.chat(
                model=model,
                messages=messages,
                stream=False,
                temperature=temperature
            )
            return self._format_response(response, model, session_id=session_id)
        
        # 获取用户消息
        user_message = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_message = msg["content"]
                break
        
        # 构建工具提示
        tool_prompt = self._build_tool_prompt(tools, user_message, tool_choice)
        
        # 调用模型
        enhanced_messages = [
            {"role": "system", "content": tool_prompt},
            *messages
        ]
        
        logger.info(f"Calling model with tool prompt")
        response = self.ollama.chat(
            model=model,
            messages=enhanced_messages,
            stream=False,
            temperature=temperature
        )
        
        # 提取工具调用
        content = response.get("message", {}).get("content", "")
        tool_match = re.search(r'<tool_call>(.*?)</tool_call>', content, re.DOTALL)
        
        if not tool_match:
            # 没有工具调用
            logger.info("No tool call found in response")
            return self._format_response(response, model, session_id=session_id)
        
        # 解析工具调用
        try:
            tool_data = json.loads(tool_match.group(1).strip())
            tool_calls = tool_data.get("tool_calls", [])
            
            if not tool_calls:
                return self._format_response(response, model, session_id=session_id)
            
            logger.info(f"Found {len(tool_calls)} tool calls")
            
            # 执行工具
            results = []
            executed_tools = []
            
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                
                # 处理工作空间路径
                for key, value in args.items():
                    if isinstance(value, str) and not value.startswith("/") and not value.startswith("\\"):
                        # 相对路径，放到工作空间
                        args[key] = str(workspace_path / value)
                
                logger.info(f"Executing tool: {tool_name} with args: {args}")
                result = await self.mcp.registry.execute_tool(tool_name, args)
                
                results.append({
                    "tool": tool_name,
                    "success": result.success,
                    "result": result.result if result.success else result.error
                })
                executed_tools.append(tool_name)
            
            # 生成最终响应
            result_prompt = "Based on the tool execution results:\n\n"
            for r in results:
                status = "✓" if r["success"] else "✗"
                result_prompt += f"{status} {r['tool']}: {r['result']}\n"
            result_prompt += "\nPlease provide a helpful response to the user."
            
            final_messages = [
                *enhanced_messages,
                {"role": "assistant", "content": content},
                {"role": "system", "content": result_prompt}
            ]
            
            final_response = self.ollama.chat(
                model=model,
                messages=final_messages,
                stream=False,
                temperature=temperature
            )
            
            return self._format_response(
                final_response,
                model,
                tool_execution={
                    "executed": True,
                    "tools_called": executed_tools,
                    "session_id": session_id,
                    "workspace_path": str(workspace_path)
                },
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Error processing tool calls: {e}")
            return self._format_response(response, model, session_id=session_id)
    
    def _build_tool_prompt(self, tools: List[Dict[str, Any]], user_message: str, tool_choice: str) -> str:
        """构建工具提示"""
        
        # 构建工具列表
        tool_list = []
        for tool in tools:
            func = tool["function"]
            tool_list.append(f"- {func['name']}: {func['description']}")
        
        # 根据tool_choice构建提示
        if tool_choice == "required":
            instruction = "You MUST use one of the available tools to answer this request."
        elif tool_choice == "auto":
            instruction = "Use tools if they would help answer the user's request."
        else:
            instruction = f"You should use the {tool_choice} tool."
        
        prompt = f"""You have access to these tools:
{chr(10).join(tool_list)}

{instruction}

When using a tool, respond with this EXACT format:
<tool_call>
{{
  "tool_calls": [
    {{
      "id": "call_1",
      "type": "function",
      "function": {{
        "name": "tool_name",
        "arguments": "{{\\"param1\\": \\"value1\\"}}"
      }}
    }}
  ]
}}
</tool_call>

Then explain what you're doing."""
        
        return prompt
    
    def _format_response(
        self,
        llm_response: Dict[str, Any],
        model: str,
        tool_execution: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """格式化响应"""
        
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": llm_response.get("message", {}),
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": llm_response.get("prompt_eval_count", 0),
                "completion_tokens": llm_response.get("eval_count", 0),
                "total_tokens": (
                    llm_response.get("prompt_eval_count", 0) + 
                    llm_response.get("eval_count", 0)
                )
            }
        }
        
        if tool_execution:
            response["tool_execution"] = tool_execution
            
        if session_id:
            response["session_id"] = session_id
        
        return response
    
    async def chat_with_tools_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.7,
        session_id: Optional[str] = None,
        device_id: str = "default",
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """流式响应（简化版）"""
        
        # 暂时使用非流式实现
        result = await self.chat_with_tools(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            session_id=session_id,
            device_id=device_id,
            max_tokens=max_tokens
        )
        
        # 转换为流式格式
        if 'choices' in result:
            content = result['choices'][0]['message']['content']
            yield f"data: {json.dumps({'type': 'content', 'delta': {'content': content}})}\n\n"
        
        if 'tool_execution' in result:
            yield f"data: {json.dumps({'type': 'tool_execution', 'data': result['tool_execution']})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'stop'})}\n\n"
        yield "data: [DONE]\n\n"
