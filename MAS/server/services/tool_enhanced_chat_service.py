"""
工具增强的聊天服务
支持在聊天对话中调用MCP工具
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
import json
import logging
import uuid
import re
import time
from dataclasses import dataclass

from server.services.ollama_service import OllamaService
from server.mcp.manager import mcp_manager, ToolCall
from server.services.mcp_workspace_service import workspace_service

logger = logging.getLogger(__name__)


@dataclass
class ChatToolCall:
    """聊天中的工具调用"""
    id: str
    type: str = "function"
    function: Dict[str, Any] = None


class ToolEnhancedChatService:
    """支持工具调用的聊天服务"""
    
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
        
        # 准备增强的消息
        enhanced_messages = self._prepare_messages_with_tools(
            messages, tools, tool_choice
        )
        
        # 第一次LLM调用
        logger.info(f"First LLM call with {len(tools or [])} tools available")
        initial_response = self.ollama.chat(
            model=model,
            messages=enhanced_messages,
            stream=False,
            temperature=temperature,
            options={"num_predict": max_tokens} if max_tokens else None
        )
        
        # 检查是否有工具调用
        tool_calls = self._extract_tool_calls(initial_response)
        
        if not tool_calls:
            # 没有工具调用，直接返回
            logger.info("No tool calls detected, returning direct response")
            return self._format_final_response(
                initial_response, 
                model, 
                session_id=session_id
            )
        
        logger.info(f"Detected {len(tool_calls)} tool calls")
        
        # 执行工具调用
        tool_results = await self._execute_tool_calls(
            tool_calls, 
            session_id, 
            workspace_path
        )
        
        # 构建包含工具结果的消息
        messages_with_results = self._build_messages_with_tool_results(
            messages, tool_calls, tool_results
        )
        
        # 第二次LLM调用，生成最终响应
        logger.info("Second LLM call with tool results")
        final_response = self.ollama.chat(
            model=model,
            messages=messages_with_results,
            stream=False,
            temperature=temperature,
            options={"num_predict": max_tokens} if max_tokens else None
        )
        
        return self._format_final_response(
            final_response,
            model,
            tool_execution={
                "executed": True,
                "tools_called": [tc["function"]["name"] for tc in tool_calls],
                "session_id": session_id,
                "workspace_path": str(workspace_path)
            }
        )
    
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
        """流式执行带工具调用的聊天"""
        
        # 初始化
        if not self.mcp._initialized:
            self.mcp.initialize()
        
        if not session_id:
            session_id = f"chat_{uuid.uuid4().hex[:8]}"
        
        _, workspace_path = workspace_service.create_workspace(
            device_id=device_id,
            session_id=session_id
        )
        
        # 准备消息
        enhanced_messages = self._prepare_messages_with_tools(
            messages, tools, tool_choice
        )
        
        # 收集流式响应以检查工具调用
        collected_response = ""
        found_tool_call = False
        
        # 第一阶段：流式获取初始响应
        for chunk in self.ollama.chat(
            model=model,
            messages=enhanced_messages,
            stream=True,
            temperature=temperature,
            options={"num_predict": max_tokens} if max_tokens else None
        ):
            collected_response += chunk
            
            # 检查是否包含工具调用标记
            if not found_tool_call and self._detect_tool_call_in_text(collected_response):
                found_tool_call = True
                logger.info("Tool call pattern detected in stream")
            
            if not found_tool_call:
                # 如果还没有检测到工具调用，正常输出内容
                yield f"data: {json.dumps({'type': 'content', 'delta': {'content': chunk}})}\n\n"
        
        # 解析完整响应中的工具调用
        if found_tool_call:
            tool_calls = self._parse_tool_calls_from_text(collected_response)
            
            if tool_calls:
                logger.info(f"Parsed {len(tool_calls)} tool calls from stream")
                
                # 发送工具调用事件
                for tool_call in tool_calls:
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool_call': tool_call})}\n\n"
                
                # 执行工具
                tool_results = await self._execute_tool_calls(
                    tool_calls,
                    session_id,
                    workspace_path
                )
                
                # 发送工具结果
                for tool_call, result in zip(tool_calls, tool_results):
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool_call_id': tool_call['id'], 'result': result})}\n\n"
                
                # 构建新消息并获取最终响应
                messages_with_results = self._build_messages_with_tool_results(
                    messages, tool_calls, tool_results
                )
                
                # 流式发送最终响应
                for chunk in self.ollama.chat(
                    model=model,
                    messages=messages_with_results,
                    stream=True,
                    temperature=temperature,
                    options={"num_predict": max_tokens} if max_tokens else None
                ):
                    yield f"data: {json.dumps({'type': 'content', 'delta': {'content': chunk}})}\n\n"
        
        # 发送完成事件
        yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'stop', 'session_id': session_id})}\n\n"
        yield "data: [DONE]\n\n"
    
    def _prepare_messages_with_tools(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: str
    ) -> List[Dict[str, Any]]:
        """准备包含工具定义的消息"""
        
        if not tools:
            return messages
        
        # 构建工具描述
        tool_descriptions = []
        for tool in tools:
            func = tool.get("function", {})
            params_desc = []
            if "parameters" in func and "properties" in func["parameters"]:
                for param_name, param_info in func["parameters"]["properties"].items():
                    param_desc = f"{param_name}: {param_info.get('type', 'any')}"
                    if "description" in param_info:
                        param_desc += f" - {param_info['description']}"
                    params_desc.append(param_desc)
            
            tool_desc = f"Tool: {func.get('name', 'unknown')}\n"
            tool_desc += f"Description: {func.get('description', 'No description')}\n"
            if params_desc:
                tool_desc += "Parameters:\n"
                for pd in params_desc:
                    tool_desc += f"  - {pd}\n"
            
            tool_descriptions.append(tool_desc)
        
        # 构建系统提示
        system_prompt = f"""You are a helpful assistant with access to the following tools:

{chr(10).join(tool_descriptions)}

When you need to use a tool, respond with a special JSON block in your message:
<tool_call>
{{
  "tool_calls": [
    {{
      "id": "call_1",
      "type": "function",
      "function": {{
        "name": "tool_name",
        "arguments": "{{\\"param1\\": \\"value1\\", \\"param2\\": \\"value2\\"}}"
      }}
    }}
  ]
}}
</tool_call>

Important:
- Tool choice strategy is: {tool_choice}
- Only use tools when necessary to answer the user's question
- You can call multiple tools if needed
- Make sure the arguments JSON is properly escaped
- Always provide helpful context before and after tool calls"""
        
        # 添加系统提示
        enhanced_messages = [{"role": "system", "content": system_prompt}]
        enhanced_messages.extend(messages)
        
        return enhanced_messages
    
    def _extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从LLM响应中提取工具调用"""
        
        message = response.get("message", {})
        content = message.get("content", "")
        
        # 尝试从内容中解析工具调用
        tool_calls = self._parse_tool_calls_from_text(content)
        
        # 如果消息中直接包含tool_calls（某些模型可能支持）
        if not tool_calls and "tool_calls" in message:
            tool_calls = message["tool_calls"]
        
        return tool_calls
    
    def _parse_tool_calls_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中解析工具调用"""
        tool_calls = []
        
        # 查找<tool_call>标签
        tool_call_pattern = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(tool_call_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                # 解析JSON
                data = json.loads(match.strip())
                if "tool_calls" in data:
                    tool_calls.extend(data["tool_calls"])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call JSON: {match[:100]}...")
                
        # 如果没有找到标签，尝试查找裸JSON
        if not tool_calls:
            json_pattern = r'\{[^{}]*"tool_calls"[^{}]*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)
            
            for match in matches:
                try:
                    # 尝试扩展匹配以获取完整的JSON
                    start = text.find(match)
                    end = start + len(match)
                    
                    # 计算大括号平衡
                    brace_count = match.count('{') - match.count('}')
                    while brace_count > 0 and end < len(text):
                        if text[end] == '{':
                            brace_count += 1
                        elif text[end] == '}':
                            brace_count -= 1
                        end += 1
                    
                    full_json = text[start:end]
                    data = json.loads(full_json)
                    
                    if "tool_calls" in data:
                        tool_calls.extend(data["tool_calls"])
                except:
                    continue
        
        # 确保每个工具调用都有ID
        for i, tc in enumerate(tool_calls):
            if "id" not in tc:
                tc["id"] = f"call_{i+1}"
        
        return tool_calls
    
    def _detect_tool_call_in_text(self, text: str) -> bool:
        """检测文本中是否包含工具调用模式"""
        patterns = [
            r'<tool_call>',
            r'"tool_calls"',
            r'"function".*"name".*"arguments"'
        ]
        return any(re.search(pattern, text) for pattern in patterns)
    
    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        session_id: str,
        workspace_path
    ) -> List[Dict[str, Any]]:
        """执行工具调用"""
        
        results = []
        
        for tool_call in tool_calls:
            try:
                func = tool_call.get("function", {})
                tool_name = func.get("name", "")
                arguments_str = func.get("arguments", "{}")
                
                # 解析参数
                try:
                    arguments = json.loads(arguments_str)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse arguments for {tool_name}: {arguments_str}")
                    arguments = {}
                
                logger.info(f"Executing tool: {tool_name} with args: {arguments}")
                
                # 处理工作空间路径
                processed_args = self._process_workspace_paths(
                    arguments, workspace_path
                )
                
                # 执行工具
                result = await self.mcp.registry.execute_tool(
                    name=tool_name,
                    parameters=processed_args
                )
                
                if result.success:
                    results.append({
                        "success": True,
                        "result": result.result,
                        "metadata": result.metadata
                    })
                else:
                    results.append({
                        "success": False,
                        "error": result.error
                    })
                    
            except Exception as e:
                logger.error(f"Error executing tool {tool_call}: {e}")
                results.append({
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def _process_workspace_paths(self, parameters: Dict[str, Any], workspace_path) -> Dict[str, Any]:
        """处理参数中的工作空间路径"""
        processed = parameters.copy()
        
        for key, value in processed.items():
            if isinstance(value, str):
                if value.startswith("@workspace/"):
                    filename = value[11:]
                    processed[key] = str(workspace_path / filename)
                elif value == "@workspace":
                    processed[key] = str(workspace_path)
        
        return processed
    
    def _build_messages_with_tool_results(
        self,
        original_messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """构建包含工具结果的消息列表"""
        
        # 保留原始消息，但添加了工具系统提示
        messages = self._prepare_messages_with_tools(original_messages, [], "none")
        
        # 添加助手的工具调用消息
        assistant_msg = {
            "role": "assistant",
            "content": "I'll help you with that. Let me use the appropriate tools.",
            "tool_calls": tool_calls
        }
        messages.append(assistant_msg)
        
        # 添加工具结果消息
        for tool_call, result in zip(tool_calls, tool_results):
            tool_msg = {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False)
            }
            messages.append(tool_msg)
        
        # 添加提示让助手基于工具结果回答
        messages.append({
            "role": "system",
            "content": "Based on the tool results above, please provide a helpful response to the user's question."
        })
        
        return messages
    
    def _format_final_response(
        self,
        llm_response: Dict[str, Any],
        model: str,
        tool_execution: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """格式化最终响应"""
        
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
