"""
简单的消息功能测试（带超时控制）
"""
import asyncio
import aiohttp
import json
import traceback
from datetime import datetime


async def test_basic_functionality():
    """测试基本消息功能"""
    base_url = "http://localhost:8000"
    
    print("=== Basic Message Communication Test ===\n")
    
    # 1. 测试消息发送API
    print("1. Testing message send API...")
    try:
        timeout = aiohttp.ClientTimeout(total=5)  # 5秒超时
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{base_url}/api/messages/send"
            headers = {
                "X-Device-ID": "test-device-simple",
                "Content-Type": "application/json"
            }
            payload = {
                "recipient_id": "test-recipient-simple",
                "content": "Hello, this is a test message!",
                "type": "text"
            }
            
            print(f"   URL: {url}")
            print(f"   Sending message...")
            
            async with session.post(url, json=payload, headers=headers) as resp:
                print(f"   Response status: {resp.status}")
                response_text = await resp.text()
                
                if resp.status == 200:
                    data = json.loads(response_text)
                    print(f"   ✓ Message sent! ID: {data.get('message_id')}")
                elif resp.status == 404:
                    print(f"   ✗ API endpoint not found! Message routes may not be loaded.")
                    print(f"   Response: {response_text}")
                else:
                    print(f"   ✗ Failed with status {resp.status}")
                    print(f"   Response: {response_text}")
                    
    except asyncio.TimeoutError:
        print("   ✗ Request timed out after 5 seconds")
    except aiohttp.ClientConnectorError:
        print("   ✗ Cannot connect to server. Is it running?")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    
    print("\n" + "-" * 50 + "\n")
    
    # 2. 测试消息列表API
    print("2. Testing message list API...")
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{base_url}/api/messages/list"
            headers = {
                "X-Device-ID": "test-device-simple",
                "Content-Type": "application/json"
            }
            payload = {
                "device_id": "test-recipient-simple",
                "limit": 10
            }
            
            print(f"   URL: {url}")
            print(f"   Fetching messages...")
            
            async with session.post(url, json=payload, headers=headers) as resp:
                print(f"   Response status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✓ Got {data.get('count', 0)} messages")
                elif resp.status == 404:
                    print(f"   ✗ API endpoint not found!")
                else:
                    print(f"   ✗ Failed with status {resp.status}")
                    print(f"   Response: {await resp.text()}")
                    
    except asyncio.TimeoutError:
        print("   ✗ Request timed out after 5 seconds")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {str(e)}")
    
    print("\n" + "-" * 50 + "\n")
    
    # 3. 测试WebSocket连接（带超时）
    print("3. Testing WebSocket connection (5 second timeout)...")
    try:
        ws_url = f"{base_url.replace('http', 'ws')}/api/messages/ws/test-device-simple"
        print(f"   URL: {ws_url}")
        
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print("   Connecting...")
            
            try:
                async with session.ws_connect(ws_url) as ws:
                    print("   ✓ Connected!")
                    
                    # 等待连接消息（最多2秒）
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            print(f"   Received: {data.get('type', 'unknown')} message")
                    except asyncio.TimeoutError:
                        print("   ! No connection message received (timeout)")
                    
                    # 发送ping
                    await ws.send_json({"type": "ping"})
                    print("   Sent ping")
                    
                    # 等待pong（最多1秒）
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get('type') == 'pong':
                                print("   ✓ Received pong")
                    except asyncio.TimeoutError:
                        print("   ! No pong received (timeout)")
                    
                    # 关闭连接
                    await ws.close()
                    print("   ✓ Connection closed")
                    
            except aiohttp.WSServerHandshakeError as e:
                if e.status == 404:
                    print("   ✗ WebSocket endpoint not found!")
                else:
                    print(f"   ✗ WebSocket handshake failed: {e}")
                    
    except asyncio.TimeoutError:
        print("   ✗ Connection timed out after 5 seconds")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {str(e)}")
    
    print("\n" + "-" * 50 + "\n")
    
    # 4. 快速检查API状态
    print("4. Quick API check...")
    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 检查服务器根路径
            async with session.get(base_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print("   ✓ Server is running")
                    print(f"   Version: {data.get('version', 'unknown')}")
                    
            # 检查messages API是否存在
            test_endpoints = [
                "/api/messages/online",
                "/api/messages/sessions",
                "/api/messages/unread"
            ]
            
            print("\n   Checking message endpoints:")
            for endpoint in test_endpoints:
                try:
                    async with session.get(f"{base_url}{endpoint}", 
                                         headers={"X-Device-ID": "test"}) as resp:
                        if resp.status == 200:
                            print(f"   ✓ {endpoint} - OK")
                        elif resp.status == 404:
                            print(f"   ✗ {endpoint} - NOT FOUND")
                        else:
                            print(f"   ! {endpoint} - Status {resp.status}")
                except Exception as e:
                    print(f"   ✗ {endpoint} - Error: {e}")
                    
    except Exception as e:
        print(f"   ✗ Server check failed: {e}")
    
    print("\n=== Test Complete ===")
    print("\nIf you see 404 errors, the message routes are not loaded.")
    print("Please restart the server for changes to take effect.")


async def main():
    """主函数"""
    print("Starting message communication test with timeouts...\n")
    print("Each test has a maximum timeout of 5 seconds.\n")
    
    try:
        # 设置总超时时间为30秒
        await asyncio.wait_for(test_basic_functionality(), timeout=30)
    except asyncio.TimeoutError:
        print("\n\n✗ Test suite timed out after 30 seconds!")
        print("This usually means the server is not responding.")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # 运行事件循环
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    
    print("\n\nPress Enter to exit...")
    input()
