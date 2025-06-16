"""
测试MCP工具调用聊天功能
"""
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
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"Failed to get tools: {resp.status}")
                    return []
    
    async def chat(
        self,
        message: str,
        use_tools: bool = True,
        stream: bool = False,
        model: str = None
    ) -> Dict[str, Any]:
        """发送聊天消息"""
        
        # 获取可用工具
        tools = []
        if use_tools:
            tools = await self.get_available_tools()
            print(f"Available tools: {len(tools)} tools")
        
        # 构建请求
        payload = {
            "model": model,  # None will use default
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
                headers={"X-Device-ID": "python-test-client"}
            ) as resp:
                
                if stream:
                    # 处理流式响应
                    events = []
                    async for line in resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                event = json.loads(data_str)
                                events.append(event)
                                
                                # 打印事件
                                if event.get('type') == 'content':
                                    print(event['delta']['content'], end='', flush=True)
                                elif event.get('type') == 'tool_call':
                                    print(f"\n[Tool Call: {event['tool_call']['function']['name']}]")
                                elif event.get('type') == 'tool_result':
                                    print(f"[Tool Result: {'Success' if event['result']['success'] else 'Failed'}]")
                                    
                            except json.JSONDecodeError:
                                continue
                    
                    print()  # 换行
                    return {"events": events}
                else:
                    # 处理标准响应
                    result = await resp.json()
                    
                    # 保存session_id
                    if 'session_id' in result:
                        self.session_id = result['session_id']
                    
                    return result
    
    async def test_basic_chat(self):
        """测试基础聊天（无工具）"""
        print("\n=== Test 1: Basic Chat (No Tools) ===")
        result = await self.chat("Hello, please introduce yourself briefly.", use_tools=False)
        
        if 'choices' in result:
            print(f"Response: {result['choices'][0]['message']['content']}")
            print(f"Model used: {result.get('model', 'unknown')}")
        else:
            print(f"Error: {result}")
    
    async def test_tool_info(self):
        """测试获取工具信息"""
        print("\n=== Test 2: Get Available Tools ===")
        tools = await self.get_available_tools()
        
        print(f"Total tools available: {len(tools)}")
        
        # 按类别分组
        categories = {}
        for tool in tools:
            # OpenAI格式的工具
            if isinstance(tool, dict) and 'type' in tool and tool['type'] == 'function':
                func = tool.get('function', {})
                name = func.get('name', 'unknown')
            else:
                # 直接的函数定义
                name = tool.get('name', 'unknown')
            
            # 简单分类
            if 'file' in name or 'directory' in name:
                category = 'filesystem'
            elif 'fetch' in name or 'web' in name:
                category = 'web'
            elif 'json' in name or 'csv' in name:
                category = 'data'
            elif 'map' in name or 'route' in name:
                category = 'map'
            else:
                category = 'other'
            
            if category not in categories:
                categories[category] = []
            categories[category].append(name)
        
        for cat, tool_names in categories.items():
            print(f"\n{cat.title()} tools ({len(tool_names)}):")
            for name in sorted(tool_names)[:5]:  # 只显示前5个
                print(f"  - {name}")
            if len(tool_names) > 5:
                print(f"  ... and {len(tool_names) - 5} more")
    
    async def test_file_tool(self):
        """测试文件读取工具"""
        print("\n=== Test 3: File Reading Tool ===")
        
        # 先创建一个测试文件
        test_content = "This is a test file created for MCP tool testing.\nIt contains multiple lines.\nLast line."
        
        # 使用工具创建文件
        print("Creating test file...")
        result = await self.chat(
            f"Please create a file named 'test_mcp.txt' in the workspace with this content:\n{test_content}",
            use_tools=True
        )
        
        if 'tool_execution' in result:
            print(f"Tools called: {result['tool_execution']['tools_called']}")
            print(f"Workspace: {result['tool_execution']['workspace_path']}")
        
        # 读取文件
        print("\nReading the file back...")
        result = await self.chat(
            "Please read the file test_mcp.txt from the workspace and tell me what it contains.",
            use_tools=True
        )
        
        if 'choices' in result:
            print(f"Assistant response: {result['choices'][0]['message']['content']}")
    
    async def test_web_tool(self):
        """测试网络工具"""
        print("\n=== Test 4: Web Fetch Tool ===")
        result = await self.chat(
            "Please fetch the content from https://example.com and tell me what the page is about.",
            use_tools=True
        )
        
        if 'choices' in result:
            print(f"Response: {result['choices'][0]['message']['content'][:500]}...")
        
        if 'tool_execution' in result:
            print(f"\nTools used: {result['tool_execution']['tools_called']}")
    
    async def test_json_processing(self):
        """测试JSON处理工具"""
        print("\n=== Test 5: JSON Processing Tool ===")
        
        json_data = {
            "name": "Test Product",
            "price": 29.99,
            "categories": ["electronics", "gadgets"],
            "in_stock": True
        }
        
        result = await self.chat(
            f"Please analyze this JSON data and tell me what it represents:\n{json.dumps(json_data, indent=2)}",
            use_tools=True
        )
        
        if 'choices' in result:
            print(f"Analysis: {result['choices'][0]['message']['content']}")
    
    async def test_stream_with_tools(self):
        """测试流式响应与工具调用"""
        print("\n=== Test 6: Streaming Response with Tools ===")
        print("User: What files are in the current workspace?\n")
        print("Assistant: ", end='', flush=True)
        
        result = await self.chat(
            "What files are in the current workspace? List them for me.",
            use_tools=True,
            stream=True
        )
        
        # 流式响应已经在chat方法中打印了
    
    async def test_multiple_tools(self):
        """测试多工具调用"""
        print("\n=== Test 7: Multiple Tool Calls ===")
        
        result = await self.chat(
            "Create a file called 'data.json' with some sample user data (name, age, email), then read it back and tell me what's in it.",
            use_tools=True
        )
        
        if 'choices' in result:
            print(f"Response: {result['choices'][0]['message']['content']}")
        
        if 'tool_execution' in result:
            print(f"\nTools used: {result['tool_execution']['tools_called']}")
            print(f"Session ID: {result['tool_execution']['session_id']}")


async def run_all_tests():
    """运行所有测试"""
    client = MASChatClient()
    
    print("MAS MCP Tool Integration Test Suite")
    print("=" * 50)
    
    try:
        # 测试基础功能
        await client.test_basic_chat()
        await asyncio.sleep(1)
        
        # 测试工具信息
        await client.test_tool_info()
        await asyncio.sleep(1)
        
        # 测试具体工具
        await client.test_file_tool()
        await asyncio.sleep(1)
        
        await client.test_web_tool()
        await asyncio.sleep(1)
        
        await client.test_json_processing()
        await asyncio.sleep(1)
        
        # 测试高级功能
        await client.test_stream_with_tools()
        await asyncio.sleep(1)
        
        await client.test_multiple_tools()
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


async def interactive_mode():
    """交互式聊天模式"""
    client = MASChatClient()
    
    print("MAS Chat Client - Interactive Mode")
    print("Commands: 'quit' to exit, 'tools off/on' to toggle tools, 'stream on/off' for streaming")
    print("=" * 50)
    
    use_tools = True
    use_stream = False
    
    while True:
        try:
            user_input = input("\nYou: ")
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'tools off':
                use_tools = False
                print("Tools disabled")
                continue
            elif user_input.lower() == 'tools on':
                use_tools = True
                print("Tools enabled")
                continue
            elif user_input.lower() == 'stream on':
                use_stream = True
                print("Streaming enabled")
                continue
            elif user_input.lower() == 'stream off':
                use_stream = False
                print("Streaming disabled")
                continue
            
            print("\nAssistant: ", end='', flush=True)
            
            result = await client.chat(
                user_input,
                use_tools=use_tools,
                stream=use_stream
            )
            
            if not use_stream and 'choices' in result:
                print(result['choices'][0]['message']['content'])
                
                if 'tool_execution' in result:
                    print(f"\n[Tools used: {', '.join(result['tool_execution']['tools_called'])}]")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_mode())
    else:
        asyncio.run(run_all_tests())
