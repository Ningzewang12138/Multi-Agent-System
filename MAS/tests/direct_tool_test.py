"""
直接测试简化版工具调用
"""
import asyncio
import aiohttp
import json


async def direct_test():
    """直接测试工具调用格式"""
    base_url = "http://localhost:8000"
    
    print("=== Direct Tool Call Test ===\n")
    
    # 测试1：使用完全匹配调试脚本成功的格式
    print("1. Testing with exact format that worked in debug...")
    
    # 构建与调试时完全相同的系统提示
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
            headers={"X-Device-ID": "direct-test"}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                
                print("Response:")
                if 'choices' in result:
                    content = result['choices'][0]['message']['content']
                    print(f"Content: {content[:300]}...")
                    
                    if '<tool_call>' in content:
                        print("\n✓ Model included tool_call tags!")
                    else:
                        print("\n✗ No tool_call tags found")
                
                if 'tool_execution' in result:
                    print(f"\n✓ Tool execution successful!")
                    print(f"  Tools: {result['tool_execution']['tools_called']}")
                    print(f"  Session: {result['tool_execution']['session_id']}")
                    print(f"  Workspace: {result['tool_execution']['workspace_path']}")
                else:
                    print("\n✗ No tool execution")
                    
                # 打印完整响应用于调试
                print("\nFull response:")
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: {resp.status}")
                print(await resp.text())
    
    # 测试2：验证文件是否创建
    if 'tool_execution' in result and result['tool_execution']['executed']:
        print("\n2. Verifying file creation...")
        session_id = result['tool_execution']['session_id']
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/api/mcp/workspace/{session_id}/files"
            ) as resp:
                if resp.status == 200:
                    files = await resp.json()
                    print(f"Files in workspace: {len(files)} files")
                    for f in files:
                        print(f"  - {f['name']} ({f['size']} bytes)")
                else:
                    print(f"Error: {resp.status}")
    
    # 测试3：不带系统提示的测试
    print("\n3. Testing without system prompt...")
    
    payload2 = {
        "messages": [
            {"role": "user", "content": "Use the write_file tool to create a file named hello.txt with content 'World'"}
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
            json=payload2,
            headers={"X-Device-ID": "direct-test-2"}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                
                if 'tool_execution' in result:
                    print("✓ Tool executed successfully even without manual system prompt!")
                else:
                    print("✗ Tool not executed")
                    if 'choices' in result:
                        print(f"Response: {result['choices'][0]['message']['content'][:200]}...")


if __name__ == "__main__":
    asyncio.run(direct_test())
