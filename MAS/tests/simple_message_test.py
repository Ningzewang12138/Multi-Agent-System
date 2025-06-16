"""
简单的消息功能测试
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
        async with aiohttp.ClientSession() as session:
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
            print(f"   Headers: {headers}")
            print(f"   Payload: {payload}")
            
            async with session.post(url, json=payload, headers=headers) as resp:
                print(f"   Response status: {resp.status}")
                response_text = await resp.text()
                print(f"   Response: {response_text}")
                
                if resp.status == 200:
                    data = json.loads(response_text)
                    print(f"   ✓ Message sent! ID: {data.get('message_id')}")
                else:
                    print(f"   ✗ Failed with status {resp.status}")
                    
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    
    print("\n" + "-" * 50 + "\n")
    
    # 2. 测试消息列表API
    print("2. Testing message list API...")
    try:
        async with aiohttp.ClientSession() as session:
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
            print(f"   Headers: {headers}")
            print(f"   Payload: {payload}")
            
            async with session.post(url, json=payload, headers=headers) as resp:
                print(f"   Response status: {resp.status}")
                response_text = await resp.text()
                print(f"   Response: {response_text[:200]}...")  # 只显示前200字符
                
                if resp.status == 200:
                    data = json.loads(response_text)
                    print(f"   ✓ Got {data.get('count', 0)} messages")
                else:
                    print(f"   ✗ Failed with status {resp.status}")
                    
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    
    print("\n" + "-" * 50 + "\n")
    
    # 3. 测试WebSocket连接
    print("3. Testing WebSocket connection...")
    try:
        ws_url = f"{base_url.replace('http', 'ws')}/api/messages/ws/test-device-simple"
        print(f"   URL: {ws_url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                print("   ✓ Connected!")
                
                # 等待连接消息
                msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    print(f"   Received: {data}")
                
                # 发送ping
                await ws.send_json({"type": "ping"})
                print("   Sent ping")
                
                # 关闭连接
                await ws.close()
                print("   ✓ Connection closed normally")
                
    except asyncio.TimeoutError:
        print("   ✗ Timeout waiting for message")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    
    print("\n" + "-" * 50 + "\n")
    
    # 4. 测试设备发现
    print("4. Testing device discovery...")
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{base_url}/api/sync/devices"
            print(f"   URL: {url}")
            
            async with session.get(url) as resp:
                print(f"   Response status: {resp.status}")
                
                if resp.status == 200:
                    devices = await resp.json()
                    print(f"   ✓ Found {len(devices)} devices")
                    for device in devices[:3]:
                        print(f"     - {device.get('name', 'Unknown')} ({device.get('id', 'Unknown')})")
                else:
                    print(f"   ✗ Failed with status {resp.status}")
                    
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    
    print("\n=== Test Complete ===")


async def test_chat_between_clients():
    """测试两个客户端之间的聊天"""
    base_url = "http://localhost:8000"
    
    print("\n=== Testing Chat Between Two Clients ===\n")
    
    client1_id = "alice-device"
    client2_id = "bob-device"
    
    # 1. Client1 发送消息给 Client2
    print(f"1. {client1_id} sending message to {client2_id}...")
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{base_url}/api/messages/send"
            headers = {"X-Device-ID": client1_id}
            payload = {
                "recipient_id": client2_id,
                "content": "Hello Bob! This is Alice.",
                "type": "text"
            }
            
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✓ Message sent! ID: {data['message_id']}")
                else:
                    print(f"   ✗ Failed: {await resp.text()}")
                    
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    await asyncio.sleep(1)
    
    # 2. Client2 查看收到的消息
    print(f"\n2. {client2_id} checking messages...")
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{base_url}/api/messages/list"
            headers = {"X-Device-ID": client2_id}
            payload = {
                "device_id": client1_id,
                "limit": 5
            }
            
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✓ Found {data['count']} messages")
                    for msg in data['messages']:
                        print(f"     - From {msg['sender_name']}: {msg['content']}")
                else:
                    print(f"   ✗ Failed: {await resp.text()}")
                    
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 3. Client2 回复消息
    print(f"\n3. {client2_id} sending reply to {client1_id}...")
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{base_url}/api/messages/send"
            headers = {"X-Device-ID": client2_id}
            payload = {
                "recipient_id": client1_id,
                "content": "Hi Alice! Got your message.",
                "type": "text"
            }
            
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✓ Reply sent! ID: {data['message_id']}")
                else:
                    print(f"   ✗ Failed: {await resp.text()}")
                    
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n=== Chat Test Complete ===")


async def main():
    """主函数"""
    print("Starting message communication tests...\n")
    
    # 基本功能测试
    await test_basic_functionality()
    
    # 客户端聊天测试
    await test_chat_between_clients()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
