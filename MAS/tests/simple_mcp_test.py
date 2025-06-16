"""
简单的MCP工具调用测试
"""
import asyncio
import aiohttp
import json


async def simple_test():
    """简单测试工具调用"""
    base_url = "http://localhost:8000"
    
    print("=== Simple MCP Tool Test ===\n")
    
    # 测试1：使用明确的指令格式
    print("1. Testing with clear ACTION/ARGS format...")
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "I need you to create a file. Use this format:\nACTION: write_file\nARGS: {\"path\": \"hello.txt\", \"content\": \"Hello from MCP!\"}"
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["path", "content"]
                    }
                }
            }
        ],
        "tool_choice": "auto",
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat/completions",
            json=payload,
            headers={"X-Device-ID": "simple-test"}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                
                print("Response received:")
                if 'choices' in result:
                    print(f"Content: {result['choices'][0]['message']['content'][:200]}...")
                
                if 'tool_execution' in result:
                    print(f"\n✓ Tool execution successful!")
                    print(f"  Tools called: {result['tool_execution']['tools_called']}")
                    print(f"  Session ID: {result['tool_execution']['session_id']}")
                else:
                    print("\n✗ No tool execution detected")
            else:
                print(f"Error: {resp.status}")
                print(await resp.text())
    
    # 测试2：检查工作空间中的文件
    print("\n2. Checking workspace files...")
    
    if 'tool_execution' in result:
        session_id = result['tool_execution']['session_id']
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/api/mcp/workspace/{session_id}/files"
            ) as resp:
                if resp.status == 200:
                    files = await resp.json()
                    print(f"Files in workspace: {files}")
                else:
                    print(f"Error getting files: {resp.status}")
    
    # 测试3：使用自然语言
    print("\n3. Testing with natural language...")
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Create a JSON file named 'data.json' with a simple user object containing name 'John' and age 30"
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["path", "content"]
                    }
                }
            }
        ],
        "tool_choice": "required",  # 强制使用工具
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat/completions",
            json=payload,
            headers={"X-Device-ID": "simple-test"}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                
                print("Response received:")
                if 'choices' in result:
                    content = result['choices'][0]['message']['content']
                    print(f"Content preview: {content[:200]}...")
                    
                    # 检查是否包含ACTION格式
                    if "ACTION:" in content:
                        print("\n✓ Model used ACTION format!")
                    else:
                        print("\n✗ Model did not use ACTION format")
                
                if 'tool_execution' in result:
                    print(f"\n✓ Tool execution successful!")
                    print(f"  Tools called: {result['tool_execution']['tools_called']}")
                else:
                    print("\n✗ No tool execution detected")
            else:
                print(f"Error: {resp.status}")


if __name__ == "__main__":
    asyncio.run(simple_test())
