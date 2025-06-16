"""
测试客户端间消息通信功能
"""
import asyncio
import aiohttp
import json
from datetime import datetime
import sys


class MessageTestClient:
    """消息测试客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", device_id: str = "test-client"):
        self.base_url = base_url
        self.device_id = device_id
        self.ws = None
        self.session = None
    
    async def connect_websocket(self):
        """连接WebSocket"""
        self.session = aiohttp.ClientSession()
        ws_url = f"{self.base_url.replace('http', 'ws')}/api/messages/ws/{self.device_id}"
        
        try:
            self.ws = await self.session.ws_connect(ws_url)
            print(f"✓ WebSocket connected for device: {self.device_id}")
            
            # 启动接收消息的任务
            asyncio.create_task(self.receive_messages())
            
        except Exception as e:
            print(f"✗ Failed to connect WebSocket: {e}")
            raise
    
    async def receive_messages(self):
        """接收WebSocket消息"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    
                    if data['type'] == 'message':
                        print(f"\n📨 New message from {data['message']['sender_name']}:")
                        print(f"   {data['message']['content']}")
                        print(f"   Time: {data['message']['created_at']}")
                    
                    elif data['type'] == 'receipt':
                        print(f"\n✓ Message {data['message_id']} status: {data['status']}")
                    
                    elif data['type'] == 'connection':
                        print(f"✓ Connection status: {data['status']}")
                    
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f'WebSocket error: {self.ws.exception()}')
                    
        except Exception as e:
            print(f"Error receiving messages: {e}")
    
    async def send_message(self, recipient_id: str, content: str):
        """发送消息"""
        url = f"{self.base_url}/api/messages/send"
        headers = {"X-Device-ID": self.device_id}
        
        payload = {
            "recipient_id": recipient_id,
            "content": content,
            "type": "text"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✓ Message sent: {result['message_id']}")
                    print(f"  Status: {result['status']}")
                    print(f"  Delivered: {result['delivered']}")
                else:
                    print(f"✗ Failed to send message: {await resp.text()}")
    
    async def get_sessions(self):
        """获取会话列表"""
        url = f"{self.base_url}/api/messages/sessions"
        headers = {"X-Device-ID": self.device_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"\n📋 Sessions ({result['count']} total):")
                    for session in result['sessions']:
                        participant = [p for p in session['participant_names'] 
                                     if p != self.device_id][0] if session['participant_names'] else "Unknown"
                        last_msg = session.get('last_message')
                        if last_msg:
                            print(f"  • {participant}: {last_msg['content'][:30]}...")
                        else:
                            print(f"  • {participant}: (no messages)")
                else:
                    print(f"✗ Failed to get sessions: {await resp.text()}")
    
    async def get_messages(self, device_id: str, limit: int = 10):
        """获取与特定设备的消息历史"""
        url = f"{self.base_url}/api/messages/list"
        headers = {"X-Device-ID": self.device_id}
        
        payload = {
            "device_id": device_id,
            "limit": limit
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"\n💬 Messages with {device_id} ({result['count']} messages):")
                    for msg in result['messages']:
                        sender = "You" if msg['sender_id'] == self.device_id else msg['sender_name']
                        print(f"  [{msg['created_at']}] {sender}: {msg['content']}")
                else:
                    print(f"✗ Failed to get messages: {await resp.text()}")
    
    async def get_online_devices(self):
        """获取在线设备"""
        url = f"{self.base_url}/api/messages/online"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"\n🟢 Online devices ({result['count']} total):")
                    for device in result['online_devices']:
                        print(f"  • {device['name']} ({device['id']}) - {device['type']}/{device['platform']}")
                else:
                    print(f"✗ Failed to get online devices: {await resp.text()}")
    
    async def close(self):
        """关闭连接"""
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()


async def test_messaging():
    """测试消息功能"""
    print("=== Message Communication Test ===\n")
    
    # 获取设备信息
    print("1. Getting current device info...")
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8000/api/sync/device/info") as resp:
            if resp.status == 200:
                server_info = await resp.json()
                print(f"✓ Server device: {server_info['name']} ({server_info['id']})")
            else:
                print("✗ Failed to get server info")
                return
    
    # 创建测试客户端
    client1 = MessageTestClient(device_id="test-device-1")
    
    try:
        # 连接WebSocket
        print("\n2. Connecting WebSocket...")
        await client1.connect_websocket()
        
        # 等待连接建立
        await asyncio.sleep(1)
        
        # 获取在线设备
        print("\n3. Checking online devices...")
        await client1.get_online_devices()
        
        # 发送消息到服务器
        print("\n4. Sending test message to server...")
        await client1.send_message(
            server_info['id'], 
            f"Hello from test client at {datetime.now().strftime('%H:%M:%S')}"
        )
        
        # 等待消息处理
        await asyncio.sleep(1)
        
        # 获取会话列表
        print("\n5. Getting sessions...")
        await client1.get_sessions()
        
        # 获取消息历史
        print("\n6. Getting message history...")
        await client1.get_messages(server_info['id'])
        
        # 保持连接一段时间以接收消息
        print("\n7. Waiting for incoming messages (10 seconds)...")
        await asyncio.sleep(10)
        
    finally:
        await client1.close()
        print("\n✓ Test completed")


async def interactive_chat():
    """交互式聊天客户端"""
    print("=== Interactive Chat Client ===\n")
    
    # 获取设备名称
    device_name = input("Enter your device name: ").strip() or "test-client"
    device_id = f"{device_name}-{datetime.now().strftime('%H%M%S')}"
    
    client = MessageTestClient(device_id=device_id)
    
    try:
        # 连接WebSocket
        await client.connect_websocket()
        await asyncio.sleep(1)
        
        # 显示在线设备
        await client.get_online_devices()
        
        print("\nCommands:")
        print("  /list - List online devices")
        print("  /sessions - Show chat sessions")
        print("  /history <device_id> - Show message history")
        print("  /quit - Exit")
        print("\nTo send a message: <device_id> <message>")
        print("-" * 50)
        
        # 创建输入任务
        async def handle_input():
            while True:
                try:
                    # 使用 asyncio 的方式读取输入
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, input, "\n> "
                    )
                    
                    if user_input.startswith('/'):
                        command = user_input.split()[0]
                        
                        if command == '/quit':
                            break
                        elif command == '/list':
                            await client.get_online_devices()
                        elif command == '/sessions':
                            await client.get_sessions()
                        elif command == '/history':
                            parts = user_input.split(maxsplit=1)
                            if len(parts) > 1:
                                await client.get_messages(parts[1])
                            else:
                                print("Usage: /history <device_id>")
                    else:
                        # 发送消息
                        parts = user_input.split(maxsplit=1)
                        if len(parts) == 2:
                            recipient_id, message = parts
                            await client.send_message(recipient_id, message)
                        else:
                            print("Usage: <device_id> <message>")
                            
                except Exception as e:
                    print(f"Error: {e}")
                    break
        
        # 运行输入处理
        await handle_input()
        
    finally:
        await client.close()


async def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "chat":
        await interactive_chat()
    else:
        await test_messaging()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
