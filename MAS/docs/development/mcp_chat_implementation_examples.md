# MCP工具调用实现示例

## 1. 扩展的聊天服务实现

```python
# server/services/tool_enhanced_chat_service.py

from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import logging
import uuid
from fastapi import HTTPException

from server.services.ollama_service import OllamaService
from server.mcp.manager import mcp_manager, ToolCall
from server.services.mcp_workspace_service import workspace_service

logger = logging.getLogger(__name__)


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
        device_id: str = "default"
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
        initial_response = self.ollama.chat(
            model=model,
            messages=enhanced_messages,
            stream=False,
            temperature=temperature
        )
        
        # 检查是否有工具调用
        tool_calls = self._extract_tool_calls(initial_response)
        
        if not tool_calls:
            # 没有工具调用，直接返回
            return self._format_final_response(
                initial_response, 
                model, 
                session_id=session_id
            )
        
        # 执行工具调用
        tool_results = await self._execute_tool_calls(
            tool_calls, 
            session_id, 
            workspace_path
        )
        
        # 构建包含工具结果的消息
        messages_with_results = messages.copy()
        messages_with_results.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls
        })
        
        for tool_call, result in zip(tool_calls, tool_results):
            messages_with_results.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False)
            })
        
        # 第二次LLM调用，生成最终响应
        final_response = self.ollama.chat(
            model=model,
            messages=messages_with_results,
            stream=False,
            temperature=temperature
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
        device_id: str = "default"
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
        tool_calls_buffer = []
        
        # 第一阶段：流式获取初始响应
        for chunk in self.ollama.chat(
            model=model,
            messages=enhanced_messages,
            stream=True,
            temperature=temperature
        ):
            collected_response += chunk
            
            # 检查是否包含工具调用标记
            if self._detect_tool_call_in_chunk(chunk):
                # 开始收集工具调用
                tool_calls_buffer.append(chunk)
            else:
                # 正常内容，直接yield
                yield f"data: {json.dumps({'type': 'content', 'delta': {'content': chunk}})}\n\n"
        
        # 解析完整响应中的工具调用
        if tool_calls_buffer:
            tool_calls = self._parse_tool_calls_from_text(collected_response)
            
            if tool_calls:
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
                    temperature=temperature
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
        
        # 构建系统提示
        tool_descriptions = []
        for tool in tools:
            func = tool["function"]
            tool_descriptions.append(
                f"- {func['name']}: {func['description']}"
            )
        
        system_prompt = f"""You are a helpful assistant with access to the following tools:

{chr(10).join(tool_descriptions)}

When you need to use a tool, respond with a JSON object in this format:
{{
  "tool_calls": [
    {{
      "id": "unique_id",
      "type": "function",
      "function": {{
        "name": "tool_name",
        "arguments": "{{\\"param1\\": \\"value1\\"}}"
      }}
    }}
  ]
}}

Tool choice strategy: {tool_choice}
"""
        
        # 添加系统提示
        enhanced_messages = [{"role": "system", "content": system_prompt}]
        enhanced_messages.extend(messages)
        
        return enhanced_messages
    
    def _extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从LLM响应中提取工具调用"""
        
        message = response.get("message", {})
        content = message.get("content", "")
        
        # 尝试从内容中解析JSON
        try:
            # 查找JSON块
            import re
            json_match = re.search(r'\{.*"tool_calls".*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if "tool_calls" in data:
                    return data["tool_calls"]
        except:
            pass
        
        # 检查是否直接包含tool_calls
        if "tool_calls" in message:
            return message["tool_calls"]
        
        return []
    
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
                func = tool_call["function"]
                tool_name = func["name"]
                arguments = json.loads(func["arguments"])
                
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
    
    def _process_workspace_paths(self, parameters: Dict[str, Any], workspace_path):
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
        
        import time
        
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
    
    def _detect_tool_call_in_chunk(self, chunk: str) -> bool:
        """检测chunk中是否包含工具调用标记"""
        indicators = ["tool_calls", "function", "arguments"]
        return any(ind in chunk for ind in indicators)
    
    def _parse_tool_calls_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中解析工具调用"""
        # 这里需要实现更复杂的解析逻辑
        # 简化示例
        try:
            import re
            json_match = re.search(r'\{.*"tool_calls".*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("tool_calls", [])
        except:
            pass
        return []
    
    def _build_messages_with_tool_results(
        self,
        original_messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """构建包含工具结果的消息列表"""
        
        messages = original_messages.copy()
        
        # 添加助手的工具调用消息
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls
        })
        
        # 添加工具结果消息
        for tool_call, result in zip(tool_calls, tool_results):
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False)
            })
        
        return messages
```

## 2. 更新后的聊天路由

```python
# server/api/routes/chat.py (修改部分)

from server.services.tool_enhanced_chat_service import ToolEnhancedChatService

# 添加到路由函数
def get_tool_chat_service(request: Request) -> ToolEnhancedChatService:
    """获取工具增强的聊天服务"""
    ollama_service = request.app.state.services.ollama_service
    if not hasattr(request.app.state.services, 'tool_chat_service'):
        request.app.state.services.tool_chat_service = ToolEnhancedChatService(
            ollama_service
        )
    return request.app.state.services.tool_chat_service

@router.post("/completions")
async def chat_completions(
    request: Request,
    chat_request: ChatRequest,
    ollama: OllamaService = Depends(get_ollama_service),
    tool_chat: ToolEnhancedChatService = Depends(get_tool_chat_service)
):
    """处理聊天请求（支持工具调用）"""
    
    # 检查是否需要工具调用
    if chat_request.tools and len(chat_request.tools) > 0:
        # 使用工具增强的聊天服务
        logger.info(f"Processing chat with {len(chat_request.tools)} tools available")
        
        try:
            messages = [{"role": msg.role, "content": msg.content} 
                       for msg in chat_request.messages]
            
            if chat_request.stream:
                # 流式响应
                async def generate():
                    async for chunk in tool_chat.chat_with_tools_stream(
                        model=chat_request.model or ollama.get_default_model(),
                        messages=messages,
                        tools=chat_request.tools,
                        tool_choice=chat_request.tool_choice,
                        temperature=chat_request.temperature,
                        session_id=getattr(chat_request, 'session_id', None),
                        device_id=request.headers.get('X-Device-ID', 'default')
                    ):
                        yield chunk
                
                return StreamingResponse(
                    generate(),
                    media_type="text/event-stream",
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                    }
                )
            else:
                # 非流式响应
                result = await tool_chat.chat_with_tools(
                    model=chat_request.model or ollama.get_default_model(),
                    messages=messages,
                    tools=chat_request.tools,
                    tool_choice=chat_request.tool_choice,
                    temperature=chat_request.temperature,
                    session_id=getattr(chat_request, 'session_id', None),
                    device_id=request.headers.get('X-Device-ID', 'default')
                )
                return result
                
        except Exception as e:
            logger.error(f"Tool-enhanced chat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 原有的聊天逻辑（不带工具）
    # ... 保持原有代码不变 ...
```

## 3. 客户端示例实现

```python
# client_example.py

import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional


class MASChatClient:
    """MAS聊天客户端，支持工具调用"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/mcp/tools") as resp:
                return await resp.json()
    
    async def chat(
        self,
        message: str,
        use_tools: bool = True,
        stream: bool = False
    ) -> Dict[str, Any]:
        """发送聊天消息"""
        
        # 获取可用工具
        tools = []
        if use_tools:
            tools = await self.get_available_tools()
        
        # 构建请求
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": message}],
            "tools": tools,
            "tool_choice": "auto" if tools else "none",
            "stream": stream,
            "session_id": self.session_id
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat/completions",
                json=payload,
                headers={"X-Device-ID": "python-client"}
            ) as resp:
                
                if stream:
                    # 处理流式响应
                    async for line in resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                event = json.loads(data_str)
                                yield event
                            except json.JSONDecodeError:
                                continue
                else:
                    # 处理标准响应
                    result = await resp.json()
                    
                    # 保存session_id
                    if 'session_id' in result:
                        self.session_id = result['session_id']
                    
                    return result
    
    async def chat_interactive(self):
        """交互式聊天"""
        print("MAS Chat Client (输入 'quit' 退出)")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\n您: ")
                if user_input.lower() == 'quit':
                    break
                
                print("\n助手: ", end="", flush=True)
                
                # 使用流式响应
                async for event in self.chat(user_input, stream=True):
                    if event.get('type') == 'content':
                        print(event['delta']['content'], end="", flush=True)
                    elif event.get('type') == 'tool_call':
                        print(f"\n[调用工具: {event['tool_call']['function']['name']}]")
                    elif event.get('type') == 'tool_result':
                        print(f"[工具执行{'成功' if event['result']['success'] else '失败'}]")
                
                print()  # 换行
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n错误: {e}")


# 使用示例
async def main():
    client = MASChatClient()
    
    # 示例1：简单聊天
    print("示例1：简单聊天")
    result = await client.chat("你好，请介绍一下自己")
    print(f"回复: {result['choices'][0]['message']['content']}")
    
    # 示例2：使用工具
    print("\n示例2：使用工具")
    result = await client.chat("请读取当前目录下的README.md文件")
    print(f"回复: {result['choices'][0]['message']['content']}")
    
    if 'tool_execution' in result:
        print(f"工具调用信息: {result['tool_execution']}")
    
    # 示例3：交互式聊天
    print("\n示例3：交互式聊天")
    await client.chat_interactive()


if __name__ == "__main__":
    asyncio.run(main())
```

## 4. Flutter客户端集成示例

```dart
// flutter_client_example.dart

import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class MASChatService {
  final String baseUrl;
  String? sessionId;
  
  MASChatService({this.baseUrl = 'http://localhost:8000'});
  
  Future<List<Map<String, dynamic>>> getAvailableTools() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/mcp/tools'),
    );
    
    if (response.statusCode == 200) {
      return List<Map<String, dynamic>>.from(json.decode(response.body));
    } else {
      throw Exception('Failed to load tools');
    }
  }
  
  Stream<ChatEvent> chatWithTools({
    required String message,
    bool useTools = true,
    String model = 'llama3.2',
  }) async* {
    // 获取可用工具
    List<Map<String, dynamic>> tools = [];
    if (useTools) {
      tools = await getAvailableTools();
    }
    
    // 构建请求
    final request = http.Request(
      'POST',
      Uri.parse('$baseUrl/api/chat/completions'),
    );
    
    request.headers['Content-Type'] = 'application/json';
    request.headers['X-Device-ID'] = 'flutter-client';
    
    request.body = json.encode({
      'model': model,
      'messages': [
        {'role': 'user', 'content': message}
      ],
      'tools': tools,
      'tool_choice': tools.isNotEmpty ? 'auto' : 'none',
      'stream': true,
      'session_id': sessionId,
    });
    
    // 发送请求并处理流式响应
    final client = http.Client();
    final response = await client.send(request);
    
    await for (final chunk in response.stream.transform(utf8.decoder)) {
      final lines = chunk.split('\n');
      
      for (final line in lines) {
        if (line.startsWith('data: ')) {
          final data = line.substring(6);
          if (data == '[DONE]') {
            break;
          }
          
          try {
            final event = json.decode(data);
            
            // 更新session_id
            if (event['session_id'] != null) {
              sessionId = event['session_id'];
            }
            
            // 生成相应的事件
            if (event['type'] == 'content') {
              yield ContentEvent(event['delta']['content']);
            } else if (event['type'] == 'tool_call') {
              yield ToolCallEvent(
                event['tool_call']['function']['name'],
                event['tool_call']['id'],
              );
            } else if (event['type'] == 'tool_result') {
              yield ToolResultEvent(
                event['tool_call_id'],
                event['result']['success'],
                event['result'],
              );
            } else if (event['type'] == 'done') {
              yield DoneEvent(event['finish_reason']);
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
    
    client.close();
  }
}

// 事件类定义
abstract class ChatEvent {}

class ContentEvent extends ChatEvent {
  final String content;
  ContentEvent(this.content);
}

class ToolCallEvent extends ChatEvent {
  final String toolName;
  final String callId;
  ToolCallEvent(this.toolName, this.callId);
}

class ToolResultEvent extends ChatEvent {
  final String callId;
  final bool success;
  final Map<String, dynamic> result;
  ToolResultEvent(this.callId, this.success, this.result);
}

class DoneEvent extends ChatEvent {
  final String reason;
  DoneEvent(this.reason);
}

// 使用示例
class ChatScreen extends StatefulWidget {
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final MASChatService chatService = MASChatService();
  final List<ChatMessage> messages = [];
  final TextEditingController controller = TextEditingController();
  
  void sendMessage() async {
    final userMessage = controller.text;
    if (userMessage.isEmpty) return;
    
    // 添加用户消息
    setState(() {
      messages.add(ChatMessage(
        role: 'user',
        content: userMessage,
      ));
    });
    
    controller.clear();
    
    // 准备助手消息
    final assistantMessage = ChatMessage(
      role: 'assistant',
      content: '',
      isStreaming: true,
    );
    
    setState(() {
      messages.add(assistantMessage);
    });
    
    // 处理流式响应
    await for (final event in chatService.chatWithTools(message: userMessage)) {
      if (event is ContentEvent) {
        setState(() {
          assistantMessage.content += event.content;
        });
      } else if (event is ToolCallEvent) {
        setState(() {
          assistantMessage.addToolCall(event.toolName);
        });
      } else if (event is DoneEvent) {
        setState(() {
          assistantMessage.isStreaming = false;
        });
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    // UI实现...
  }
}
```

## 5. 测试脚本

```python
# test_tool_chat.py

import pytest
import asyncio
import json
from server.services.tool_enhanced_chat_service import ToolEnhancedChatService
from server.services.ollama_service import OllamaService
from server.mcp.manager import mcp_manager


class TestToolEnhancedChat:
    """工具增强聊天测试"""
    
    @pytest.fixture
    async def chat_service(self):
        ollama = OllamaService()
        return ToolEnhancedChatService(ollama)
    
    @pytest.mark.asyncio
    async def test_chat_without_tools(self, chat_service):
        """测试不使用工具的聊天"""
        result = await chat_service.chat_with_tools(
            model="llama3.2",
            messages=[{"role": "user", "content": "你好"}],
            tools=None
        )
        
        assert result["choices"][0]["message"]["role"] == "assistant"
        assert result["choices"][0]["message"]["content"] is not None
    
    @pytest.mark.asyncio
    async def test_chat_with_file_tool(self, chat_service):
        """测试使用文件工具的聊天"""
        tools = [{
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            }
        }]
        
        result = await chat_service.chat_with_tools(
            model="llama3.2",
            messages=[{"role": "user", "content": "读取test.txt文件"}],
            tools=tools,
            tool_choice="auto"
        )
        
        assert "tool_execution" in result
        assert result["tool_execution"]["executed"] == True
        assert "read_file" in result["tool_execution"]["tools_called"]
    
    @pytest.mark.asyncio
    async def test_stream_chat_with_tools(self, chat_service):
        """测试流式工具聊天"""
        tools = [{
            "type": "function",
            "function": {
                "name": "fetch",
                "description": "获取网页内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"}
                    },
                    "required": ["url"]
                }
            }
        }]
        
        events = []
        async for chunk in chat_service.chat_with_tools_stream(
            model="llama3.2",
            messages=[{"role": "user", "content": "获取https://example.com的内容"}],
            tools=tools
        ):
            if chunk.startswith("data: "):
                data = chunk[6:]
                if data != "[DONE]":
                    events.append(json.loads(data))
        
        # 验证事件序列
        event_types = [e["type"] for e in events]
        assert "tool_call" in event_types or "content" in event_types
        assert event_types[-1] == "done"


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_chat_without_tools())
    asyncio.run(test_chat_with_file_tool())
    asyncio.run(test_stream_chat_with_tools())
```
