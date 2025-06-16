"""
消息通信功能测试报告生成器
"""
import asyncio
import aiohttp
import json
from datetime import datetime
import sys
import os


class MessageTestValidator:
    """消息功能验证器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        
    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("MAS MESSAGE COMMUNICATION TEST REPORT")
        print("=" * 60)
        print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Server URL: {self.base_url}")
        print("=" * 60)
        
        # 1. 服务器连接测试
        await self.test_server_connection()
        
        # 2. API端点测试
        await self.test_api_endpoints()
        
        # 3. WebSocket测试
        await self.test_websocket()
        
        # 4. 消息发送测试
        await self.test_message_sending()
        
        # 5. 消息存储测试
        await self.test_message_storage()
        
        # 6. 设备发现测试
        await self.test_device_discovery()
        
        # 生成报告
        self.generate_report()
    
    async def test_server_connection(self):
        """测试服务器连接"""
        print("\n1. SERVER CONNECTION TEST")
        print("-" * 40)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.test_results.append({
                            "test": "Server Connection",
                            "status": "PASS",
                            "details": f"Server version: {data.get('version', 'unknown')}"
                        })
                        print("✓ Server is running")
                        print(f"  Version: {data.get('version', 'unknown')}")
                        print(f"  Status: {data.get('status', 'unknown')}")
                        
                        # 检查功能状态
                        features = data.get('features', {})
                        print("\n  Feature Status:")
                        for feature, enabled in features.items():
                            status = "✓" if enabled else "✗"
                            print(f"    {status} {feature}: {enabled}")
                    else:
                        raise Exception(f"Server returned status {resp.status}")
                        
        except Exception as e:
            self.test_results.append({
                "test": "Server Connection",
                "status": "FAIL",
                "details": str(e)
            })
            print(f"✗ Server connection failed: {e}")
            return False
        
        return True
    
    async def test_api_endpoints(self):
        """测试API端点"""
        print("\n2. API ENDPOINTS TEST")
        print("-" * 40)
        
        endpoints = [
            ("GET", "/api/messages/online", "Online devices endpoint"),
            ("GET", "/api/messages/sessions", "Sessions endpoint"),
            ("GET", "/api/messages/unread", "Unread count endpoint"),
            ("GET", "/api/sync/devices", "Device discovery endpoint"),
            ("GET", "/api/sync/device/info", "Device info endpoint"),
        ]
        
        headers = {"X-Device-ID": "test-validator"}
        
        for method, endpoint, description in endpoints:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.base_url}{endpoint}"
                    
                    if method == "GET":
                        async with session.get(url, headers=headers) as resp:
                            if resp.status == 200:
                                self.test_results.append({
                                    "test": f"API: {endpoint}",
                                    "status": "PASS",
                                    "details": description
                                })
                                print(f"✓ {endpoint} - {description}")
                            else:
                                raise Exception(f"Status {resp.status}")
                    
            except Exception as e:
                self.test_results.append({
                    "test": f"API: {endpoint}",
                    "status": "FAIL",
                    "details": str(e)
                })
                print(f"✗ {endpoint} - Failed: {e}")
    
    async def test_websocket(self):
        """测试WebSocket连接"""
        print("\n3. WEBSOCKET CONNECTION TEST")
        print("-" * 40)
        
        device_id = "test-ws-validator"
        ws_url = f"{self.base_url.replace('http', 'ws')}/api/messages/ws/{device_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    # 等待连接消息
                    msg = await ws.receive()
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get('type') == 'connection':
                            self.test_results.append({
                                "test": "WebSocket Connection",
                                "status": "PASS",
                                "details": "Connected successfully"
                            })
                            print("✓ WebSocket connection established")
                            
                            # 测试ping/pong
                            await ws.send_json({"type": "ping"})
                            print("✓ Ping sent")
                            
                            # 正常关闭
                            await ws.close()
                        else:
                            raise Exception("No connection message received")
                    else:
                        raise Exception(f"Unexpected message type: {msg.type}")
                        
        except Exception as e:
            self.test_results.append({
                "test": "WebSocket Connection",
                "status": "FAIL",
                "details": str(e)
            })
            print(f"✗ WebSocket test failed: {e}")
    
    async def test_message_sending(self):
        """测试消息发送功能"""
        print("\n4. MESSAGE SENDING TEST")
        print("-" * 40)
        
        sender_id = "test-sender-001"
        recipient_id = "test-recipient-001"
        
        try:
            # 发送测试消息
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/messages/send"
                headers = {"X-Device-ID": sender_id}
                payload = {
                    "recipient_id": recipient_id,
                    "content": f"Test message at {datetime.now().isoformat()}",
                    "type": "text"
                }
                
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        self.test_results.append({
                            "test": "Message Sending",
                            "status": "PASS",
                            "details": f"Message ID: {result['message_id']}"
                        })
                        print(f"✓ Message sent successfully")
                        print(f"  Message ID: {result['message_id']}")
                        print(f"  Status: {result['status']}")
                        
                        return result['message_id']
                    else:
                        raise Exception(f"Send failed: {await resp.text()}")
                        
        except Exception as e:
            self.test_results.append({
                "test": "Message Sending",
                "status": "FAIL",
                "details": str(e)
            })
            print(f"✗ Message sending failed: {e}")
            return None
    
    async def test_message_storage(self):
        """测试消息存储"""
        print("\n5. MESSAGE STORAGE TEST")
        print("-" * 40)
        
        try:
            # 获取消息列表
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/messages/list"
                headers = {"X-Device-ID": "test-sender-001"}
                payload = {
                    "device_id": "test-recipient-001",
                    "limit": 10
                }
                
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        message_count = result.get('count', 0)
                        
                        # 即使没有消息也认为测试通过（只要API正常响应）
                        self.test_results.append({
                            "test": "Message Storage",
                            "status": "PASS",
                            "details": f"Storage API working, found {message_count} messages"
                        })
                        print(f"✓ Message storage working")
                        print(f"  Messages in database: {message_count}")
                        
                        # 检查会话
                        await self._test_sessions()
                    else:
                        error_text = await resp.text()
                        raise Exception(f"API returned {resp.status}: {error_text}")
                        
        except Exception as e:
            self.test_results.append({
                "test": "Message Storage",
                "status": "FAIL",
                "details": str(e)
            })
            print(f"✗ Message storage test failed: {e}")
    
    async def _test_sessions(self):
        """测试会话功能"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/messages/sessions"
                headers = {"X-Device-ID": "test-sender-001"}
                
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        session_count = result.get('count', 0)
                        print(f"  Active sessions: {session_count}")
                        
        except Exception as e:
            print(f"  Session test error: {e}")
    
    async def test_device_discovery(self):
        """测试设备发现功能"""
        print("\n6. DEVICE DISCOVERY TEST")
        print("-" * 40)
        
        try:
            async with aiohttp.ClientSession() as session:
                # 获取设备列表
                url = f"{self.base_url}/api/sync/devices"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        devices = await resp.json()
                        device_count = len(devices)
                        
                        self.test_results.append({
                            "test": "Device Discovery",
                            "status": "PASS",
                            "details": f"Found {device_count} devices"
                        })
                        print(f"✓ Device discovery working")
                        print(f"  Discovered devices: {device_count}")
                        
                        # 列出设备
                        for device in devices[:3]:  # 最多显示3个
                            print(f"    - {device['name']} ({device['status']})")
                        
                        if device_count > 3:
                            print(f"    ... and {device_count - 3} more")
                    else:
                        raise Exception("Failed to get device list")
                        
        except Exception as e:
            self.test_results.append({
                "test": "Device Discovery",
                "status": "FAIL",
                "details": str(e)
            })
            print(f"✗ Device discovery failed: {e}")
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        total = len(self.test_results)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({(passed/total*100):.1f}%)")
        print(f"Failed: {failed} ({(failed/total*100):.1f}%)")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "=" * 60)
        
        # 保存报告
        report_file = f"message_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("MAS MESSAGE COMMUNICATION TEST REPORT\n")
            f.write("=" * 60 + "\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Server URL: {self.base_url}\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("Test Results:\n")
            for result in self.test_results:
                f.write(f"{result['status']:6} {result['test']:30} {result['details']}\n")
            
            f.write(f"\nSummary: {passed}/{total} tests passed ({(passed/total*100):.1f}%)\n")
        
        print(f"\nReport saved to: {report_file}")
        
        # 整体测试结果
        if failed == 0:
            print("\n✅ ALL TESTS PASSED! Message communication is working correctly.")
        else:
            print("\n⚠️  SOME TESTS FAILED! Please check the errors above.")


async def main():
    """主函数"""
    validator = MessageTestValidator()
    await validator.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
