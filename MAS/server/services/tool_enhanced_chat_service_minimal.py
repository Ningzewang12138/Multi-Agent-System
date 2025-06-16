"""
极简工具调用服务 - 直接执行版本
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import logging
import uuid
import re
import asyncio
import time
from pathlib import Path

from server.services.ollama_service import OllamaService
from server.mcp.manager import mcp_manager
from server.services.mcp_workspace_service import workspace_service

logger = logging.getLogger(__name__)


class ToolEnhancedChatService:
    """支持工具调用的聊天服务（极简直接执行版）"""
    
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
        
        logger.info(f"=== ToolEnhancedChatService.chat_with_tools called ===")
        logger.info(f"Tools provided: {len(tools) if tools else 0}")
        logger.info(f"Tool choice: {tool_choice}")
        
        # 确保MCP管理器已初始化
        if not self.mcp._initialized:
            logger.info("Initializing MCP manager...")
            self.mcp.initialize()
        
        # 创建或获取会话ID
        if not session_id:
            session_id = f"chat_{uuid.uuid4().hex[:8]}"
        
        # 创建工作空间
        _, workspace_path = workspace_service.create_workspace(
            device_id=device_id,
            session_id=session_id
        )
        
        # 如果没有工具，直接返回
        if not tools or tool_choice == "none":
            logger.info("No tools or tool_choice=none, using standard chat")
            response = self.ollama.chat(
                model=model,
                messages=messages,
                stream=False,
                temperature=temperature
            )
            return self._format_response(response, model, session_id=session_id)
        
        # 获取用户的最后一条消息
        user_message = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_message = msg["content"]
                break
        
        logger.info(f"User message: {user_message}")
        
        # 如果tool_choice是required，强制执行工具
        if tool_choice == "required" or tool_choice == "auto":
            # 尝试识别意图
            executed = await self._try_execute_tool(user_message, tools, workspace_path, session_id)
            
            if executed:
                logger.info("Tool executed successfully")
                return executed
            elif tool_choice == "required":
                # 如果是required但没有执行成功，返回错误消息
                error_msg = "I couldn't identify which tool to use. Please be more specific about what you want me to do."
                response = {
                    "message": {
                        "role": "assistant",
                        "content": error_msg
                    }
                }
                return self._format_response(response, model, session_id=session_id)
        
        # 默认情况：让模型正常回复
        logger.info("Using standard LLM response")
        response = self.ollama.chat(
            model=model,
            messages=messages,
            stream=False,
            temperature=temperature
        )
        return self._format_response(response, model, session_id=session_id)
    
    async def _try_execute_tool(
        self,
        message: str,
        tools: List[Dict[str, Any]],
        workspace_path: Path,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """尝试执行工具"""
        
        logger.info("Trying to execute tool based on message")
        
        # 构建工具映射
        tool_map = {}
        for tool in tools:
            func = tool.get("function", {})
            tool_name = func.get("name", "")
            tool_map[tool_name] = func
        
        logger.info(f"Available tools: {list(tool_map.keys())}")
        
        # 检查文件创建
        if "write_file" in tool_map:
            # 多种匹配模式
            patterns = [
                (r'create\s+(?:a\s+)?file\s+(?:named\s+)?(\S+)\s+with\s+content\s+["\']?(.+?)["\']?$', False),
                (r'create\s+(\S+)\s+with\s+content\s+["\']?(.+?)["\']?$', False),
                (r'save\s+["\']?(.+?)["\']?\s+to\s+(\S+)', True),  # content first
                (r'write\s+["\']?(.+?)["\']?\s+to\s+(\S+)', True),  # content first
            ]
            
            for pattern, content_first in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    if content_first:
                        content, filename = match.groups()
                    else:
                        filename, content = match.groups()
                    
                    filename = filename.strip().strip('"\'')
                    content = content.strip().strip('"\'')
                    
                    logger.info(f"Detected file creation: {filename} with content: {content}")
                    
                    # 执行工具
                    try:
                        file_path = str(workspace_path / filename)
                        result = await self.mcp.registry.execute_tool(
                            "write_file",
                            {"path": file_path, "content": content}
                        )
                        
                        if result.success:
                            response = {
                                "message": {
                                    "role": "assistant",
                                    "content": f"I've successfully created the file '{filename}' with the specified content."
                                }
                            }
                            return self._format_response(
                                response,
                                "llama3.2",
                                tool_execution={
                                    "executed": True,
                                    "tools_called": ["write_file"],
                                    "session_id": session_id,
                                    "workspace_path": str(workspace_path)
                                },
                                session_id=session_id
                            )
                    except Exception as e:
                        logger.error(f"Error executing write_file: {e}")
        
        # 检查文件列表
        if "list_directory" in tool_map:
            if any(word in message.lower() for word in ["list", "show", "what files", "ls"]):
                logger.info("Detected list directory intent")
                try:
                    result = await self.mcp.registry.execute_tool(
                        "list_directory",
                        {"path": str(workspace_path)}
                    )
                    
                    if result.success:
                        files = result.result
                        if files:
                            file_list = "\n".join([f"- {f['name']}" for f in files if f['type'] == 'file'])
                            content = f"Files in the workspace:\n{file_list}" if file_list else "The workspace is empty."
                        else:
                            content = "The workspace is empty."
                        
                        response = {
                            "message": {
                                "role": "assistant",
                                "content": content
                            }
                        }
                        return self._format_response(
                            response,
                            "llama3.2",
                            tool_execution={
                                "executed": True,
                                "tools_called": ["list_directory"],
                                "session_id": session_id,
                                "workspace_path": str(workspace_path)
                            },
                            session_id=session_id
                        )
                except Exception as e:
                    logger.error(f"Error executing list_directory: {e}")
        
        # 检查文件读取
        if "read_file" in tool_map:
            patterns = [
                r'read\s+(?:the\s+)?(?:file\s+)?(\S+)',
                r'show\s+(?:me\s+)?(\S+)',
                r'what\'s\s+in\s+(\S+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip().strip('"\'')
                    if '.' in filename:
                        logger.info(f"Detected read file: {filename}")
                        try:
                            file_path = str(workspace_path / filename)
                            result = await self.mcp.registry.execute_tool(
                                "read_file",
                                {"path": file_path}
                            )
                            
                            if result.success:
                                content = f"Content of '{filename}':\n\n{result.result}"
                            else:
                                content = f"Error reading '{filename}': {result.error}"
                            
                            response = {
                                "message": {
                                    "role": "assistant",
                                    "content": content
                                }
                            }
                            return self._format_response(
                                response,
                                "llama3.2",
                                tool_execution={
                                    "executed": True,
                                    "tools_called": ["read_file"],
                                    "session_id": session_id,
                                    "workspace_path": str(workspace_path)
                                },
                                session_id=session_id
                            )
                        except Exception as e:
                            logger.error(f"Error executing read_file: {e}")
        
        logger.info("No tool intent detected")
        return None
    
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
        """流式响应（使用非流式实现）"""
        
        # 调用非流式版本
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
            # 分块发送内容
            for i in range(0, len(content), 50):
                chunk = content[i:i+50]
                yield f"data: {json.dumps({'type': 'content', 'delta': {'content': chunk}})}\n\n"
        
        # 如果有工具执行信息
        if 'tool_execution' in result:
            yield f"data: {json.dumps({'type': 'tool_execution', 'data': result['tool_execution']})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'stop'})}\n\n"
        yield "data: [DONE]\n\n"
