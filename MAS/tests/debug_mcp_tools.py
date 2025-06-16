"""
MCP工具调用调试脚本
"""
import asyncio
import aiohttp
import json
from typing import List, Dict, Any


async def debug_tools():
    """调试工具系统"""
    base_url = "http://localhost:8000"
    
    print("=== MCP Tool Debug ===\n")
    
    # 1. 获取工具列表
    print("1. Fetching available tools...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/api/mcp/tools") as resp:
            if resp.status == 200:
                tools = await resp.json()
                print(f"   Found {len(tools)} tools")
                
                # 显示第一个工具的结构
                if tools:
                    print(f"\n   First tool structure:")
                    print(json.dumps(tools[0], indent=2))
                    
                # 显示所有工具名称
                print(f"\n   All tool names:")
                for tool in tools:
                    if isinstance(tool, dict):
                        if 'function' in tool:
                            name = tool['function'].get('name', 'unknown')
                        else:
                            name = tool.get('name', 'unknown')
                        print(f"   - {name}")
            else:
                print(f"   Error: {resp.status}")
                return
    
    # 2. 测试简单的工具调用
    print("\n2. Testing tool call with explicit instructions...")
    
    # 只使用文件写入工具
    file_tools = [
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "content": {"type": "string", "description": "File content"}
                    },
                    "required": ["path", "content"]
                }
            }
        }
    ]
    
    payload = {
        "model": None,  # Use default
        "messages": [
            {
                "role": "user",
                "content": "Use the write_file tool to create a file named 'hello.txt' with content 'Hello World'"
            }
        ],
        "tools": file_tools,
        "tool_choice": "auto",
        "stream": False
    }
    
    print("\n   Sending request with tools:")
    print(json.dumps(file_tools, indent=2))
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat/completions",
            json=payload,
            headers={"X-Device-ID": "debug-client"}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                
                print("\n   Response:")
                if 'choices' in result:
                    print(f"   Content: {result['choices'][0]['message']['content']}")
                
                if 'tool_execution' in result:
                    print(f"\n   Tool execution detected!")
                    print(f"   Tools called: {result['tool_execution']['tools_called']}")
                    print(f"   Session ID: {result['tool_execution']['session_id']}")
                else:
                    print("\n   No tool execution detected")
                    
                # 显示完整响应用于调试
                print("\n   Full response structure:")
                print(json.dumps(result, indent=2))
            else:
                print(f"   Error: {resp.status}")
                error_text = await resp.text()
                print(f"   Error details: {error_text}")
    
    # 3. 测试直接的MCP工具执行
    print("\n3. Testing direct MCP tool execution...")
    
    tool_request = {
        "tool_name": "write_file",
        "parameters": {
            "path": "@workspace/test_direct.txt",
            "content": "Direct tool test"
        },
        "device_id": "debug-client"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/mcp/execute",
            json=tool_request
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   Direct execution result: {result}")
            else:
                print(f"   Error: {resp.status}")


async def test_model_with_tools():
    """测试模型是否支持工具调用"""
    base_url = "http://localhost:8000"
    
    print("\n4. Testing if model understands tool format...")
    
    # 创建一个非常简单明确的提示
    system_prompt = """You have access to a tool called write_file.

When you need to use it, respond EXACTLY like this:
<tool_call>
{
  "tool_calls": [
    {
      "id": "call_1",
      "type": "function",
      "function": {
        "name": "write_file",
        "arguments": "{\\"path\\": \\"filename.txt\\", \\"content\\": \\"file content\\"}"
      }
    }
  ]
}
</tool_call>"""
    
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Create a file named test.txt with content 'Hello'"}
        ],
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat/completions",
            json=payload
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                if 'choices' in result:
                    content = result['choices'][0]['message']['content']
                    print(f"\n   Model response:\n{content}")
                    
                    # 检查是否包含工具调用格式
                    if '<tool_call>' in content or 'tool_calls' in content:
                        print("\n   ✓ Model generated tool call format!")
                    else:
                        print("\n   ✗ Model did not generate tool call format")


if __name__ == "__main__":
    asyncio.run(debug_tools())
    asyncio.run(test_model_with_tools())
