"""
多客户端消息通信测试
测试多个客户端之间的实时通信功能
"""
import asyncio
import aiohttp
import json
from datetime import datetime
import random
import string


class TestClient:
    """测试客户端"""
    
    def __init__(self, client_id: str, name: str, base_url: str = "http://localhost:8000"):
        self.client_id = client_id
        self.name = name
        self.base_url = base_url
        self.ws = None
        self.session = None
        self.received_messages = []
    
    async def connect(self):
        """连接WebSocket"""
        self.session = aiohttp.ClientSession()
        ws_url = f"{self.base_url.replace('http', 'ws')}/api/messages/ws/{self.client_id}"
        
        self.ws = await self.session.ws_connect(ws_url)
        print(f"✓ {self.name} connected (ID: {self.client_id})")
        
        # 启动消息接收任务
        asyncio.create_task(self._receive_loop())
    
    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    
                    if data['type'] == 'message':
                        message = data['message']
                        self.received_messages.append(message)
                        print(f"\n[{self.name}] 📨 Received from {message['sender_name']}: {message['content']}")
                    
                    elif data['type'] == 'receipt':
                        if data['status'] == 'delivered':
                            print(f"[{self.name}] ✓ Message delivered")
                        elif data['status'] == 'read':
                            print(f"[{self.name}] ✓✓ Message read")
                            
        except Exception as e:
            print(f"[{self.name}] Error in receive loop: {e}")
    
    async def send_message(self, recipient_id: str, content: str):
        """发送消息"""
        url = f"{self.base_url}/api/messages/send"
        headers = {"X-Device-ID": self.client_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "recipient_id": recipient_id,
                "content": content,
                "type": "text"
            }, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"[{self.name}] → Sent message to {recipient_id}")
                    return result['message_id']
                else:
                    print(f"[{self.name}] ✗ Failed to send: {await resp.text()}")
                    return None
    
    async def close(self):
        """关闭连接"""
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        print(f"[{self.name}] Disconnected")


async def multi_client_test():
    """多客户端测试"""
    print("=== Multi-Client Message Communication Test ===\n")
    
    # 检查服务器
    print("1. Checking server status...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Server is running: {data['message']}")
                else:
                    print("✗ Server is not responding")
                    return
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        print("\nPlease make sure the server is running:")
        print("  cd server")
        print("  python main.py")
        return
    
    # 创建三个测试客户端
    clients = [
        TestClient("client-a-001", "Alice"),
        TestClient("client-b-002", "Bob"),
        TestClient("client-c-003", "Charlie")
    ]
    
    try:
        # 连接所有客户端
        print("\n2. Connecting clients...")
        for client in clients:
            await client.connect()
            await asyncio.sleep(0.5)
        
        print("\n3. Testing message exchange...")
        
        # Alice -> Bob
        print("\n[Test 1] Alice sends message to Bob")
        await clients[0].send_message(clients[1].client_id, "Hello Bob! This is Alice.")
        await asyncio.sleep(1)
        
        # Bob -> Alice
        print("\n[Test 2] Bob replies to Alice")
        await clients[1].send_message(clients[0].client_id, "Hi Alice! Nice to hear from you.")
        await asyncio.sleep(1)
        
        # Charlie -> Alice
        print("\n[Test 3] Charlie sends message to Alice")
        await clients[2].send_message(clients[0].client_id, "Hey Alice, Charlie here!")
        await asyncio.sleep(1)
        
        # Alice -> Charlie
        print("\n[Test 4] Alice replies to Charlie")
        await clients[0].send_message(clients[2].client_id, "Hi Charlie! How are you?")
        await asyncio.sleep(1)
        
        # Broadcast-like: Bob sends to both
        print("\n[Test 5] Bob sends messages to everyone")
        await clients[1].send_message(clients[0].client_id, "Group message: Meeting at 3 PM!")
        await clients[1].send_message(clients[2].client_id, "Group message: Meeting at 3 PM!")
        await asyncio.sleep(1)
        
        # 等待所有消息处理完成
        print("\n4. Waiting for all messages to be delivered...")
        await asyncio.sleep(2)
        
        # 显示统计
        print("\n5. Message Statistics:")
        for client in clients:
            print(f"  {client.name}: Received {len(client.received_messages)} messages")
        
        # 验证消息接收
        print("\n6. Verification:")
        expected_messages = {
            "Alice": 3,  # From Bob, Charlie, Bob(group)
            "Bob": 2,    # From Alice, Alice
            "Charlie": 2 # From Alice, Bob(group)
        }
        
        all_passed = True
        for client in clients:
            expected = expected_messages[client.name]
            actual = len(client.received_messages)
            status = "✓ PASS" if actual == expected else "✗ FAIL"
            print(f"  {client.name}: Expected {expected}, Got {actual} - {status}")
            if actual != expected:
                all_passed = False
        
        print(f"\n{'✓ All tests PASSED!' if all_passed else '✗ Some tests FAILED!'}")
        
    finally:
        # 关闭所有连接
        print("\n7. Closing connections...")
        for client in clients:
            await client.close()


async def stress_test():
    """压力测试"""
    print("=== Message Communication Stress Test ===\n")
    
    num_clients = 5
    messages_per_client = 10
    
    print(f"Creating {num_clients} clients, each sending {messages_per_client} messages...")
    
    # 创建客户端
    clients = []
    for i in range(num_clients):
        client_id = f"stress-client-{i:03d}"
        name = f"Client{i}"
        clients.append(TestClient(client_id, name))
    
    try:
        # 连接所有客户端
        print("\nConnecting all clients...")
        for client in clients:
            await client.connect()
            await asyncio.sleep(0.1)
        
        # 发送消息
        print("\nSending messages...")
        start_time = datetime.now()
        
        tasks = []
        for i, sender in enumerate(clients):
            for j in range(messages_per_client):
                # 随机选择接收者
                recipient = random.choice([c for c in clients if c != sender])
                content = f"Test message {j+1} from {sender.name}"
                
                task = sender.send_message(recipient.client_id, content)
                tasks.append(task)
        
        # 等待所有消息发送完成
        await asyncio.gather(*tasks)
        
        # 等待消息传递
        await asyncio.sleep(3)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 统计结果
        total_sent = num_clients * messages_per_client
        total_received = sum(len(c.received_messages) for c in clients)
        
        print(f"\n=== Stress Test Results ===")
        print(f"Clients: {num_clients}")
        print(f"Messages sent: {total_sent}")
        print(f"Messages received: {total_received}")
        print(f"Success rate: {(total_received/total_sent)*100:.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Messages per second: {total_sent/duration:.1f}")
        
    finally:
        print("\nClosing all connections...")
        for client in clients:
            await client.close()


async def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "stress":
            await stress_test()
        else:
            print("Unknown test mode. Use 'stress' for stress test.")
    else:
        await multi_client_test()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
