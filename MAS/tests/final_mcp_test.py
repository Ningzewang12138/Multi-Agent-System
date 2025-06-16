"""
最终的MCP工具调用测试
"""
import asyncio
import aiohttp
import json


async def final_test():
    """最终测试工具调用"""
    base_url = "http://localhost:8000"
    
    print("=== Final MCP Tool Call Test ===\n")
    
    # 测试1：简单的文件创建
    print("1. Simple file creation test...")
    
    payload = {
        "messages": [
            {"role": "user", "content": "Create a file named test.txt with content 'Hello World'"}
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
                            "path": {"type": "string", "description": "File path"},
                            "content": {"type": "string", "description": "File content"}
                        },
                        "required": ["path", "content"]
                    }
                }
            }
        ],
        "tool_choice": "required",
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat/completions",
            json=payload,
            headers={"X-Device-ID": "final-test"}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                
                if 'tool_execution' in result:
                    print("✓ Tool executed successfully!")
                    print(f"  Tools: {result['tool_execution']['tools_called']}")
                    print(f"  Workspace: {result['tool_execution']['workspace_path']}")
                    
                    # 获取最终响应
                    if 'choices' in result:
                        print(f"\nAssistant response:")
                        print(result['choices'][0]['message']['content'])
                    
                    return result['tool_execution']['session_id']
                else:
                    print("✗ Tool not executed")
                    if 'choices' in result:
                        print(f"Response: {result['choices'][0]['message']['content'][:200]}...")
            else:
                print(f"Error: {resp.status}")
    
    return None
    
    # 测试2：列出文件
    print("\n2. List files test...")
    
    session_id = await test_file_creation()
    if session_id:
        payload = {
            "messages": [
                {"role": "user", "content": "List all files in the current directory"}
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "list_directory",
                        "description": "List contents of a directory",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "Directory path"}
                            },
                            "required": ["path"]
                        }
                    }
                }
            ],
            "tool_choice": "required",
            "session_id": session_id,
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/chat/completions",
                json=payload,
                headers={"X-Device-ID": "final-test"}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    if 'tool_execution' in result:
                        print("✓ List directory executed!")
                        if 'choices' in result:
                            print("\nFiles found:")
                            print(result['choices'][0]['message']['content'])
                    else:
                        print("✗ Tool not executed")


async def test_file_creation():
    """测试文件创建并返回session_id"""
    base_url = "http://localhost:8000"
    
    payload = {
        "messages": [
            {"role": "user", "content": "Create a file named data.txt with content 'Test data for MCP'"}
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
        "tool_choice": "required",
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat/completions",
            json=payload,
            headers={"X-Device-ID": "final-test"}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                if 'tool_execution' in result:
                    return result['tool_execution']['session_id']
    return None


async def test_interactive():
    """交互式测试"""
    base_url = "http://localhost:8000"
    session_id = None
    
    print("\n=== Interactive Tool Test ===")
    print("Available commands:")
    print("- write <filename> <content>: Create a file")
    print("- list: List files in workspace")
    print("- read <filename>: Read a file")
    print("- quit: Exit")
    print()
    
    tools = [
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
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read file content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "List directory contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            }
        }
    ]
    
    while True:
        cmd = input("\n> ").strip()
        
        if cmd == "quit":
            break
        
        # 构建自然语言请求
        if cmd.startswith("write "):
            parts = cmd[6:].split(maxsplit=1)
            if len(parts) == 2:
                message = f"Create a file named {parts[0]} with content '{parts[1]}'"
            else:
                print("Usage: write <filename> <content>")
                continue
        elif cmd == "list":
            message = "List all files in the current directory"
        elif cmd.startswith("read "):
            filename = cmd[5:].strip()
            message = f"Read the file {filename}"
        else:
            message = cmd
        
        payload = {
            "messages": [{"role": "user", "content": message}],
            "tools": tools,
            "tool_choice": "auto",
            "stream": False
        }
        
        if session_id:
            payload["session_id"] = session_id
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/chat/completions",
                json=payload,
                headers={"X-Device-ID": "interactive-test"}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    if 'tool_execution' in result:
                        print(f"[Tool executed: {', '.join(result['tool_execution']['tools_called'])}]")
                        if not session_id:
                            session_id = result['tool_execution']['session_id']
                            print(f"[Session: {session_id}]")
                    
                    if 'choices' in result:
                        print(result['choices'][0]['message']['content'])
                else:
                    print(f"Error: {resp.status}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(test_interactive())
    else:
        asyncio.run(final_test())
