"""
改进的工具增强聊天服务
优化了工具调用提示和解析逻辑
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
        
        # 检查是否应该使用工具
        if tool_choice == "none" or not tools:
            # 不使用工具，直接调用
            response = self.ollama.chat(
                model=model,
                messages=messages,
                stream=False,
                temperature=temperature,
                options={"num_predict": max_tokens} if max_tokens else None
            )
            return self._format_final_response(response, model, session_id=session_id)
        
        # 准备增强的消息
        enhanced_messages = self._prepare_messages_with_tools_v2(
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
        tool_calls = self._extract_tool_calls_v2(initial_response)
        
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
        messages_with_results = self._build_messages_with_tool_results_v2(
            enhanced_messages, tool_calls, tool_results
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
    
    def _prepare_messages_with_tools_v2(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: str
    ) -> List[Dict[str, Any]]:
        """准备包含工具定义的消息（改进版）"""
        
        if not tools:
            return messages
        
        # 构建工具描述（更简洁明确的格式）
        tool_list = []
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "No description")
            
            # 构建参数说明
            params = func.get("parameters", {}).get("properties", {})
            param_list = []
            for pname, pinfo in params.items():
                ptype = pinfo.get("type", "string")
                pdesc = pinfo.get("description", "")
                param_list.append(f"{pname} ({ptype}): {pdesc}")
            
            tool_str = f"{name}: {desc}"
            if param_list:
                tool_str += f"\n  Parameters: {', '.join(param_list)}"
            tool_list.append(tool_str)
        
        # 构建系统提示（更清晰的指令）
        system_prompt = f"""You are a helpful assistant with access to tools. Available tools:

{chr(10).join(tool_list)}

To use a tool, you MUST respond with the exact format:
ACTION: <tool_name>
ARGS: {{"param1": "value1", "param2": "value2"}}

Example:
ACTION: write_file
ARGS: {{"path": "test.txt", "content": "Hello World"}}

After I execute the tool, I'll show you the result and you can provide a final response.

Tool choice mode: {tool_choice}
- If "auto": Use tools when they would help answer the user's request
- If "required": You must use at least one tool
- If a specific tool name: You must use that specific tool

Important: Only use tools when necessary. If you can answer without tools, do so directly."""
        
        # 添加系统提示
        enhanced_messages = [{"role": "system", "content": system_prompt}]
        enhanced_messages.extend(messages)
        
        return enhanced_messages
    
    def _extract_tool_calls_v2(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从LLM响应中提取工具调用（改进版）"""
        
        message = response.get("message", {})
        content = message.get("content", "")
        
        tool_calls = []
        
        # 查找ACTION/ARGS格式
        action_pattern = r'ACTION:\s*(\w+)\s*\nARGS:\s*(\{[^}]+\})'
        matches = re.findall(action_pattern, content, re.MULTILINE)
        
        for i, (action, args_str) in enumerate(matches):
            try:
                # 解析参数
                args = json.loads(args_str)
                
                tool_call = {
                    "id": f"call_{i+1}",
                    "type": "function",
                    "function": {
                        "name": action,
                        "arguments": json.dumps(args)
                    }
                }
                tool_calls.append(tool_call)
                logger.info(f"Extracted tool call: {action} with args: {args}")
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse args for {action}: {args_str}, error: {e}")
        
        # 如果没有找到ACTION格式，尝试其他格式
        if not tool_calls:
            # 尝试原有的格式
            tool_calls = self._parse_tool_calls_from_text(content)
        
        return tool_calls
    
    def _build_messages_with_tool_results_v2(
        self,
        original_messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """构建包含工具结果的消息列表（改进版）"""
        
        messages = original_messages.copy()
        
        # 构建工具执行结果的描述
        results_text = "Tool execution results:\n\n"
        
        for tool_call, result in zip(tool_calls, tool_results):
            tool_name = tool_call["function"]["name"]
            if result["success"]:
                results_text += f"✓ {tool_name}: Success\n"
                results_text += f"  Result: {json.dumps(result['result'], ensure_ascii=False)}\n\n"
            else:
                results_text += f"✗ {tool_name}: Failed\n"
                results_text += f"  Error: {result.get('error', 'Unknown error')}\n\n"
        
        # 添加工具结果作为系统消息
        messages.append({
            "role": "system",
            "content": results_text + "Now provide a helpful response to the user based on these results."
        })
        
        return messages
    
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
        enhanced_messages = self._prepare_messages_with_tools_v2(
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
            if not found_tool_call and "ACTION:" in collected_response:
                found_tool_call = True
                logger.info("Tool call pattern detected in stream")
            
            if not found_tool_call:
                # 如果还没有检测到工具调用，正常输出内容
                yield f"data: {json.dumps({'type': 'content', 'delta': {'content': chunk}})}\n\n"
        
        # 解析完整响应中的工具调用
        if found_tool_call:
            tool_calls = self._extract_tool_calls_v2({"message": {"content": collected_response}})
            
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
                messages_with_results = self._build_messages_with_tool_results_v2(
                    enhanced_messages, tool_calls, tool_results
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
    
    # 保留其他原有方法...
    def _parse_tool_calls_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中解析工具调用（保留原有实现作为备份）"""
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
        
        return tool_calls
    
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
