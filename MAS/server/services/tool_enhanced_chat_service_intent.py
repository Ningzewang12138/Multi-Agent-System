"""
智能工具调用服务 - 基于意图识别
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import logging
import uuid
import re
import asyncio
import time

from server.services.ollama_service import OllamaService
from server.mcp.manager import mcp_manager
from server.services.mcp_workspace_service import workspace_service

logger = logging.getLogger(__name__)


class ToolEnhancedChatService:
    """支持工具调用的聊天服务（智能意图识别版）"""
    
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
        
        # 如果没有工具，直接返回
        if not tools or tool_choice == "none":
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
        
        # 基于用户消息和可用工具，智能识别意图
        tool_intent = self._analyze_intent(user_message, tools)
        
        if tool_intent and (tool_choice == "required" or tool_choice == "auto"):
            # 找到了工具意图，直接执行
            logger.info(f"Detected intent to use tool: {tool_intent['tool_name']}")
            
            # 执行工具
            tool_name = tool_intent["tool_name"]
            args = tool_intent["arguments"]
            
            # 处理路径参数
            if "path" in args and not args["path"].startswith(("/", "\\")):
                args["path"] = str(workspace_path / args["path"])
            
            logger.info(f"Executing {tool_name} with {args}")
            
            try:
                result = await self.mcp.registry.execute_tool(tool_name, args)
                
                if result.success:
                    # 构建成功响应
                    success_message = self._generate_success_message(tool_name, args, result.result)
                    
                    # 创建一个包含执行结果的响应
                    response = {
                        "message": {
                            "role": "assistant",
                            "content": success_message
                        },
                        "eval_count": len(success_message.split()),
                        "prompt_eval_count": len(user_message.split())
                    }
                    
                    return self._format_response(
                        response,
                        model,
                        tool_execution={
                            "executed": True,
                            "tools_called": [tool_name],
                            "session_id": session_id,
                            "workspace_path": str(workspace_path)
                        },
                        session_id=session_id
                    )
                else:
                    # 工具执行失败
                    error_message = f"I tried to {self._describe_action(tool_name, args)}, but encountered an error: {result.error}"
                    response = {
                        "message": {
                            "role": "assistant",
                            "content": error_message
                        }
                    }
                    return self._format_response(response, model, session_id=session_id)
                    
            except Exception as e:
                logger.error(f"Error executing tool: {e}")
                error_message = f"I encountered an error while trying to {self._describe_action(tool_name, args)}: {str(e)}"
                response = {
                    "message": {
                        "role": "assistant",
                        "content": error_message
                    }
                }
                return self._format_response(response, model, session_id=session_id)
        
        else:
            # 没有检测到明确的工具意图，或者tool_choice不允许
            # 让模型正常回复
            response = self.ollama.chat(
                model=model,
                messages=messages,
                stream=False,
                temperature=temperature
            )
            return self._format_response(response, model, session_id=session_id)
    
    def _analyze_intent(self, message: str, tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """分析用户消息，识别工具调用意图"""
        
        logger.info(f"Analyzing intent for message: {message}")
        message_lower = message.lower()
        
        # 获取可用的工具名称映射
        tool_map = {}
        for tool in tools:
            func = tool.get("function", {})
            tool_name = func.get("name", "")
            tool_map[tool_name] = func
        
        logger.info(f"Available tools: {list(tool_map.keys())}")
        
        # 检查文件写入意图
        if "write_file" in tool_map:
            logger.info("Checking for write_file intent...")
            # 多种可能的表达方式
            patterns = [
                # 明确的创建文件指令
                r'create\s+(?:a\s+)?file\s+(?:named\s+|called\s+)?["\']?(.+?)["\']?\s+with\s+content\s+["\'](.+?)["\']',
                r'create\s+["\']?(.+?)["\']?\s+(?:file\s+)?with\s+["\'](.+?)["\']',
                r'write\s+["\'](.+?)["\']?\s+to\s+(?:file\s+)?["\']?(.+?)["\']?',
                r'save\s+["\'](.+?)["\']?\s+(?:to|as)\s+["\']?(.+?)["\']?',
                # 更简单的模式
                r'file\s+["\']?(.+?)["\']?\s+content\s+["\'](.+?)["\']',
                r'create\s+(\S+)\s+(.+)
        
        # 检查文件读取意图
        if "read_file" in tool_map:
            patterns = [
                r'read\s+(?:the\s+)?(?:file\s+)?["\']?(\S+?)["\']?',
                r'show\s+(?:me\s+)?(?:the\s+)?(?:content\s+of\s+)?["\']?(\S+?)["\']?',
                r'what\'s\s+in\s+["\']?(\S+?)["\']?',
                r'open\s+["\']?(\S+?)["\']?',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip().strip('"\'')
                    # 确保是文件名（包含扩展名）
                    if '.' in filename:
                        return {
                            "tool_name": "read_file",
                            "arguments": {
                                "path": filename
                            }
                        }
        
        # 检查目录列表意图
        if "list_directory" in tool_map:
            if any(word in message_lower for word in ["list", "show", "what files", "ls", "dir"]):
                if any(word in message_lower for word in ["file", "directory", "folder", "current", "workspace"]):
                    return {
                        "tool_name": "list_directory",
                        "arguments": {
                            "path": "."  # 当前目录
                        }
                    }
        
        # 检查删除文件意图
        if "delete_file" in tool_map:
            patterns = [
                r'delete\s+["\']?(\S+?)["\']?',
                r'remove\s+["\']?(\S+?)["\']?',
                r'rm\s+["\']?(\S+?)["\']?',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip().strip('"\'')
                    if '.' in filename:  # 确保是文件名
                        return {
                            "tool_name": "delete_file",
                            "arguments": {
                                "path": filename
                            }
                        }
        
        return None
    
    def _generate_success_message(self, tool_name: str, args: Dict[str, Any], result: Any) -> str:
        """生成工具执行成功的消息"""
        
        if tool_name == "write_file":
            filename = args.get("path", "").split("/")[-1].split("\\")[-1]
            return f"I've successfully created the file '{filename}' with the specified content. The file has been saved to your workspace."
        
        elif tool_name == "read_file":
            filename = args.get("path", "").split("/")[-1].split("\\")[-1]
            return f"Here's the content of '{filename}':\n\n{result}"
        
        elif tool_name == "list_directory":
            if isinstance(result, list):
                files = [item["name"] for item in result if item.get("type") == "file"]
                dirs = [item["name"] for item in result if item.get("type") == "directory"]
                
                message = "Here's what I found in the directory:\n\n"
                if files:
                    message += f"Files ({len(files)}):\n"
                    for f in files:
                        message += f"  - {f}\n"
                if dirs:
                    message += f"\nDirectories ({len(dirs)}):\n"
                    for d in dirs:
                        message += f"  - {d}/\n"
                return message
            else:
                return f"Directory listing: {result}"
        
        elif tool_name == "delete_file":
            return f"Successfully deleted the file."
        
        else:
            return f"Successfully executed {tool_name}. Result: {result}"
    
    def _describe_action(self, tool_name: str, args: Dict[str, Any]) -> str:
        """描述工具动作"""
        
        if tool_name == "write_file":
            return f"create the file '{args.get('path', 'unknown')}'"
        elif tool_name == "read_file":
            return f"read the file '{args.get('path', 'unknown')}'"
        elif tool_name == "list_directory":
            return "list the directory contents"
        elif tool_name == "delete_file":
            return f"delete the file '{args.get('path', 'unknown')}'"
        else:
            return f"execute {tool_name}"
    
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
            chunk_size = 20  # 更小的块以获得更流畅的效果
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                yield f"data: {json.dumps({'type': 'content', 'delta': {'content': chunk}})}\n\n"
                await asyncio.sleep(0.01)  # 小延迟以模拟流式效果
        
        # 如果有工具执行信息，也发送出去
        if 'tool_execution' in result:
            yield f"data: {json.dumps({'type': 'tool_execution', 'data': result['tool_execution']})}\n\n"
        
        # 发送完成信号
        yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'stop'})}\n\n"
        yield "data: [DONE]\n\n"
,
            ]
            
            for i, pattern in enumerate(patterns):
                match = re.search(pattern, message, re.IGNORECASE | re.DOTALL)
                if match:
                    logger.info(f"Pattern {i} matched: {pattern}")
                    # 根据模式确定文件名和内容的顺序
                    if "write" in pattern and "to" in pattern:
                        content, filename = match.groups()
                    else:
                        filename, content = match.groups()
                    
                    # 清理文件名和内容
                    filename = filename.strip().strip('"\'')
                    content = content.strip().strip('"\'')
                    
                    logger.info(f"Detected write_file intent: filename='{filename}', content='{content}'")
                    return {
                        "tool_name": "write_file",
                        "arguments": {
                            "path": filename,
                            "content": content
                        }
                    }
        
        # 检查文件读取意图
        if "read_file" in tool_map:
            patterns = [
                r'read\s+(?:the\s+)?(?:file\s+)?["\']?(\S+?)["\']?',
                r'show\s+(?:me\s+)?(?:the\s+)?(?:content\s+of\s+)?["\']?(\S+?)["\']?',
                r'what\'s\s+in\s+["\']?(\S+?)["\']?',
                r'open\s+["\']?(\S+?)["\']?',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip().strip('"\'')
                    # 确保是文件名（包含扩展名）
                    if '.' in filename:
                        return {
                            "tool_name": "read_file",
                            "arguments": {
                                "path": filename
                            }
                        }
        
        # 检查目录列表意图
        if "list_directory" in tool_map:
            if any(word in message_lower for word in ["list", "show", "what files", "ls", "dir"]):
                if any(word in message_lower for word in ["file", "directory", "folder", "current", "workspace"]):
                    return {
                        "tool_name": "list_directory",
                        "arguments": {
                            "path": "."  # 当前目录
                        }
                    }
        
        # 检查删除文件意图
        if "delete_file" in tool_map:
            patterns = [
                r'delete\s+["\']?(\S+?)["\']?',
                r'remove\s+["\']?(\S+?)["\']?',
                r'rm\s+["\']?(\S+?)["\']?',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip().strip('"\'')
                    if '.' in filename:  # 确保是文件名
                        return {
                            "tool_name": "delete_file",
                            "arguments": {
                                "path": filename
                            }
                        }
        
        return None
    
    def _generate_success_message(self, tool_name: str, args: Dict[str, Any], result: Any) -> str:
        """生成工具执行成功的消息"""
        
        if tool_name == "write_file":
            filename = args.get("path", "").split("/")[-1].split("\\")[-1]
            return f"I've successfully created the file '{filename}' with the specified content. The file has been saved to your workspace."
        
        elif tool_name == "read_file":
            filename = args.get("path", "").split("/")[-1].split("\\")[-1]
            return f"Here's the content of '{filename}':\n\n{result}"
        
        elif tool_name == "list_directory":
            if isinstance(result, list):
                files = [item["name"] for item in result if item.get("type") == "file"]
                dirs = [item["name"] for item in result if item.get("type") == "directory"]
                
                message = "Here's what I found in the directory:\n\n"
                if files:
                    message += f"Files ({len(files)}):\n"
                    for f in files:
                        message += f"  - {f}\n"
                if dirs:
                    message += f"\nDirectories ({len(dirs)}):\n"
                    for d in dirs:
                        message += f"  - {d}/\n"
                return message
            else:
                return f"Directory listing: {result}"
        
        elif tool_name == "delete_file":
            return f"Successfully deleted the file."
        
        else:
            return f"Successfully executed {tool_name}. Result: {result}"
    
    def _describe_action(self, tool_name: str, args: Dict[str, Any]) -> str:
        """描述工具动作"""
        
        if tool_name == "write_file":
            return f"create the file '{args.get('path', 'unknown')}'"
        elif tool_name == "read_file":
            return f"read the file '{args.get('path', 'unknown')}'"
        elif tool_name == "list_directory":
            return "list the directory contents"
        elif tool_name == "delete_file":
            return f"delete the file '{args.get('path', 'unknown')}'"
        else:
            return f"execute {tool_name}"
    
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
            chunk_size = 20  # 更小的块以获得更流畅的效果
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                yield f"data: {json.dumps({'type': 'content', 'delta': {'content': chunk}})}\n\n"
                await asyncio.sleep(0.01)  # 小延迟以模拟流式效果
        
        # 如果有工具执行信息，也发送出去
        if 'tool_execution' in result:
            yield f"data: {json.dumps({'type': 'tool_execution', 'data': result['tool_execution']})}\n\n"
        
        # 发送完成信号
        yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'stop'})}\n\n"
        yield "data: [DONE]\n\n"
