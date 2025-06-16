"""
超简单的工具增强聊天服务
直接在响应中查找工具调用模式
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
    """支持工具调用的聊天服务（超简化版）"""
    
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
        
        # 如果tool_choice是required，强制添加工具调用提示
        if tool_choice == "required":
            # 获取第一个工具作为示例
            first_tool = tools[0]["function"]
            tool_name = first_tool["name"]
            
            # 添加明确的指令
            instruction = f"\nYou MUST use the {tool_name} tool. Respond with:\n<tool_call>\n{{\n  \"tool_calls\": [{{\n    \"id\": \"call_1\",\n    \"type\": \"function\",\n    \"function\": {{\n      \"name\": \"{tool_name}\",\n      \"arguments\": \"{{\\\"param1\\\": \\\"value1\\\"}}\"\n    }}\n  }}]\n}}\n</tool_call>"
            
            # 修改最后一条用户消息
            enhanced_messages = messages.copy()
            if enhanced_messages and enhanced_messages[-1]["role"] == "user":
                enhanced_messages[-1]["content"] += instruction
            
            messages = enhanced_messages
        
        # 调用模型
        logger.info(f"Calling model with {len(tools)} tools, choice: {tool_choice}")
        response = self.ollama.chat(
            model=model,
            messages=messages,
            stream=False,
            temperature=temperature
        )
        
        # 获取响应内容
        content = response.get("message", {}).get("content", "")
        logger.info(f"Model response preview: {content[:200]}...")
        
        # 尝试多种模式提取工具调用
        tool_calls = self._extract_tool_calls_flexible(content)
        
        if not tool_calls:
            logger.info("No tool calls found")
            return self._format_response(response, model, session_id=session_id)
        
        logger.info(f"Found {len(tool_calls)} tool calls")
        
        # 执行工具调用
        executed_tools = []
        results = []
        
        for tc in tool_calls:
            try:
                tool_name = tc["name"]
                args = tc["arguments"]
                
                # 处理路径参数
                if "path" in args and not args["path"].startswith(("/", "\\")):
                    args["path"] = str(workspace_path / args["path"])
                
                logger.info(f"Executing {tool_name} with {args}")
                result = await self.mcp.registry.execute_tool(tool_name, args)
                
                results.append({
                    "tool": tool_name,
                    "success": result.success,
                    "result": result.result if result.success else result.error
                })
                executed_tools.append(tool_name)
                
            except Exception as e:
                logger.error(f"Error executing tool: {e}")
                results.append({
                    "tool": tc.get("name", "unknown"),
                    "success": False,
                    "result": str(e)
                })
        
        # 如果有成功的工具执行，生成最终响应
        if any(r["success"] for r in results):
            # 构建结果描述
            result_text = "I've executed the following actions:\n\n"
            for r in results:
                if r["success"]:
                    result_text += f"✓ {r['tool']}: {r['result']}\n"
                else:
                    result_text += f"✗ {r['tool']}: Failed - {r['result']}\n"
            
            # 生成新的响应
            final_messages = messages + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": "Great! Now summarize what you did."}
            ]
            
            final_response = self.ollama.chat(
                model=model,
                messages=final_messages,
                stream=False,
                temperature=temperature
            )
            
            # 合并响应
            final_content = result_text + "\n" + final_response.get("message", {}).get("content", "")
            final_response["message"]["content"] = final_content
            
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
        else:
            # 没有成功的工具执行
            return self._format_response(response, model, session_id=session_id)
    
    def _extract_tool_calls_flexible(self, content: str) -> List[Dict[str, Any]]:
        """灵活提取工具调用"""
        tool_calls = []
        
        # 方法1：查找<tool_call>标签或直接的JSON
        # 先尝试找到JSON格式的tool_calls
        json_pattern = r'\{\s*"tool_calls"\s*:\s*\[(.*?)\]\s*\}'
        json_match = re.search(json_pattern, content, re.DOTALL)
        if json_match:
            try:
                # 重建完整的JSON
                full_json = '{"tool_calls": [' + json_match.group(1) + ']}'
                data = json.loads(full_json)
                if "tool_calls" in data:
                    for tc in data["tool_calls"]:
                        tool_calls.append({
                            "name": tc["function"]["name"],
                            "arguments": json.loads(tc["function"]["arguments"])
                        })
                    return tool_calls
            except Exception as e:
                logger.warning(f"Failed to parse JSON: {e}")
        
        # 备用方法：查找<tool_call>标签
        tool_match = re.search(r'<tool_call>(.*?)</tool_call>', content, re.DOTALL)
        if tool_match:
            try:
                data = json.loads(tool_match.group(1).strip())
                if "tool_calls" in data:
                    for tc in data["tool_calls"]:
                        tool_calls.append({
                            "name": tc["function"]["name"],
                            "arguments": json.loads(tc["function"]["arguments"])
                        })
                    return tool_calls
            except:
                pass
        
        # 方法2：查找ACTION/ARGS格式
        action_match = re.search(r'ACTION:\s*(\w+)\s*\nARGS:\s*(\{[^}]+\})', content)
        if action_match:
            try:
                tool_calls.append({
                    "name": action_match.group(1),
                    "arguments": json.loads(action_match.group(2))
                })
                return tool_calls
            except:
                pass
        
        # 方法3：查找函数调用模式
        # 例如: write_file("hello.txt", "content")
        func_pattern = r'(\w+)\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
        func_match = re.search(func_pattern, content)
        if func_match:
            tool_name = func_match.group(1)
            # 猜测参数
            if tool_name == "write_file":
                tool_calls.append({
                    "name": tool_name,
                    "arguments": {
                        "path": func_match.group(2),
                        "content": func_match.group(3)
                    }
                })
                return tool_calls
        
        # 方法4：查找明显的意图
        if "write_file" in content or "create a file" in content.lower():
            # 尝试提取文件名和内容
            file_match = re.search(r'(?:file\s+named?|create)\s+["\']?(\w+\.\w+)["\']?', content, re.I)
            content_match = re.search(r'(?:content|with)\s+["\']([^"\']+)["\']', content, re.I)
            
            if file_match and content_match:
                tool_calls.append({
                    "name": "write_file",
                    "arguments": {
                        "path": file_match.group(1),
                        "content": content_match.group(1)
                    }
                })
                return tool_calls
        
        return tool_calls
    
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
        """流式响应（简化实现）"""
        
        # 使用非流式实现
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
            # 分块发送
            chunk_size = 50
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                yield f"data: {json.dumps({'type': 'content', 'delta': {'content': chunk}})}\n\n"
        
        if 'tool_execution' in result:
            yield f"data: {json.dumps({'type': 'tool_execution', 'data': result['tool_execution']})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'stop'})}\n\n"
        yield "data: [DONE]\n\n"
