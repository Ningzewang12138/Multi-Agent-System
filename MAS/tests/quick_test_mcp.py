"""
快速测试MCP工具调用集成
"""
import sys
import os

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

import asyncio
from tests.test_mcp_chat_integration import MASChatClient


async def quick_test():
    """快速测试工具调用功能"""
    client = MASChatClient()
    
    print("Quick MCP Integration Test")
    print("=" * 50)
    
    # 测试1：无工具的普通聊天
    print("\n1. Testing normal chat without tools...")
    result = await client.chat("What is 2 + 2?", use_tools=False)
    if 'choices' in result:
        print(f"Response: {result['choices'][0]['message']['content']}")
    
    # 测试2：使用工具创建文件
    print("\n2. Testing file creation with tools...")
    result = await client.chat(
        "Create a file called hello.txt with the content 'Hello from MCP tools!'",
        use_tools=True
    )
    if 'choices' in result:
        print(f"Response: {result['choices'][0]['message']['content']}")
    if 'tool_execution' in result:
        print(f"Tools used: {result['tool_execution']['tools_called']}")
    
    # 测试3：读取文件
    print("\n3. Testing file reading...")
    result = await client.chat(
        "Read the file hello.txt and tell me what it says",
        use_tools=True
    )
    if 'choices' in result:
        print(f"Response: {result['choices'][0]['message']['content']}")
    
    print("\n" + "=" * 50)
    print("Quick test completed!")


if __name__ == "__main__":
    # 确保服务器正在运行
    print("Make sure the MAS server is running on http://localhost:8000")
    print("You can start it with: python quickstart.py")
    print()
    
    asyncio.run(quick_test())
