"""
测试意图识别版本的工具调用
"""
import asyncio
import aiohttp
import json


async def test_intent_based():
    """测试基于意图识别的工具调用"""
    base_url = "http://localhost:8000"
    
    print("=== Intent-Based Tool Call Test ===\n")
    
    tests = [
        {
            "name": "Create file test",
            "message": "Create a file named hello.txt with content 'Hello from intent-based system'"
        },
        {
            "name": "List files test", 
            "message": "List all files in the current directory"
        },
        {
            "name": "Read file test",
            "message": "Read the file hello.txt"
        },
        {
            "name": "Natural language test",
            "message": "I need to save some data. Create data.json with content '{\"name\": \"test\", \"value\": 123}'"
        }
    ]
    
    session_id = None
    
    for test in tests:
        print(f"\n{test['name']}:")
        print(f"User: {test['message']}")
        
        payload = {
            "messages": [
                {"role": "user", "content": test['message']}
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
            ],
            "tool_choice": "auto",
            "stream": False
        }
        
        if session_id:
            payload["session_id"] = session_id
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/chat/completions",
                json=payload,
                headers={"X-Device-ID": "intent-test"}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    if 'tool_execution' in result:
                        print("✓ Tool executed successfully!")
                        print(f"  Tools: {result['tool_execution']['tools_called']}")
                        if not session_id:
                            session_id = result['tool_execution']['session_id']
                    else:
                        print("✗ No tool execution")
                    
                    if 'choices' in result:
                        print(f"Assistant: {result['choices'][0]['message']['content']}")
                else:
                    print(f"Error: {resp.status}")
                    print(await resp.text())
        
        await asyncio.sleep(1)  # 短暂延迟


if __name__ == "__main__":
    asyncio.run(test_intent_based())
