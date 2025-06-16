"""
诊断MCP工具调用问题
"""
import asyncio
import aiohttp
import json


async def diagnose_mcp():
    """诊断MCP系统"""
    base_url = "http://localhost:8000"
    
    print("=== MCP Diagnostic Test ===\n")
    
    # 1. 检查MCP服务是否正常
    print("1. Checking MCP services...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/api/mcp/services") as resp:
            if resp.status == 200:
                services = await resp.json()
                print(f"✓ MCP services available: {len(services)} services")
                for svc in services:
                    print(f"  - {svc['name']}: {len(svc.get('tools', []))} tools")
            else:
                print(f"✗ MCP services error: {resp.status}")
    
    # 2. 直接测试MCP工具执行
    print("\n2. Testing direct MCP tool execution...")
    tool_request = {
        "tool_name": "write_file",
        "parameters": {
            "path": "test_direct.txt",
            "content": "Direct MCP test successful!"
        },
        "device_id": "diagnostic"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/mcp/execute",
            json=tool_request
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                if result['success']:
                    print("✓ Direct MCP execution successful")
                    print(f"  Session: {result['session_id']}")
                else:
                    print(f"✗ MCP execution failed: {result.get('error')}")
            else:
                print(f"✗ MCP API error: {resp.status}")
    
    # 3. 测试聊天API基础功能
    print("\n3. Testing basic chat API...")
    payload = {
        "messages": [{"role": "user", "content": "Say hello"}],
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
                    print("✓ Chat API working")
                    print(f"  Model: {result.get('model', 'unknown')}")
                else:
                    print("✗ Chat API response missing choices")
            else:
                print(f"✗ Chat API error: {resp.status}")
    
    # 4. 测试带工具的聊天（最简单的情况）
    print("\n4. Testing chat with tools (forced)...")
    payload = {
        "messages": [{"role": "user", "content": "Create a file named test.txt with content 'Hello'"}],
        "tools": [{
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
        }],
        "tool_choice": "required",  # 强制使用工具
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat/completions",
            json=payload,
            headers={"X-Device-ID": "diagnostic"}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                
                # 检查工具执行
                if 'tool_execution' in result:
                    print("✓ Tool execution detected!")
                    print(f"  Tools: {result['tool_execution']['tools_called']}")
                    print(f"  Session: {result['tool_execution']['session_id']}")
                else:
                    print("✗ No tool execution detected")
                    
                # 显示响应内容
                if 'choices' in result:
                    content = result['choices'][0]['message']['content']
                    print(f"\nResponse preview: {content[:200]}...")
                    
                # 检查session_id
                if 'session_id' in result:
                    print(f"\nSession ID in response: {result['session_id']}")
                    
            else:
                print(f"✗ Request failed: {resp.status}")
                error_text = await resp.text()
                print(f"Error: {error_text}")
    
    # 5. 检查服务器日志提示
    print("\n5. Check server logs for:")
    print("  - 'Analyzing intent for message:'")
    print("  - 'Available tools:'")
    print("  - 'Detected intent' or 'No tool intent detected'")
    print("\nRun this command to see logs:")
    print("  grep -i 'intent\\|tool' server.log | tail -20")


if __name__ == "__main__":
    asyncio.run(diagnose_mcp())
