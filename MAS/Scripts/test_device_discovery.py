"""
设备发现测试工具
用于诊断设备发现服务的网络问题
"""

import socket
import json
import time
import sys
from datetime import datetime

def test_udp_broadcast():
    """测试UDP广播功能"""
    print("=== UDP Broadcast Test ===")
    
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(5.0)  # 5秒超时
    
    # 准备测试消息
    test_message = {
        'type': 'device_announcement',
        'device': {
            'id': 'test-device-123',
            'name': 'Test Device',
            'type': 'desktop',
            'platform': 'windows',
            'ip_address': '127.0.0.1',
            'port': 8000,
            'version': '1.0.0',
            'capabilities': ['test'],
            'last_seen': datetime.now().isoformat(),
            'status': 'online'
        }
    }
    
    # 发送广播
    try:
        data = json.dumps(test_message).encode('utf-8')
        sock.sendto(data, ('<broadcast>', 8001))
        print(f"✓ Broadcast sent successfully ({len(data)} bytes)")
    except Exception as e:
        print(f"✗ Failed to send broadcast: {e}")
        return
    
    # 尝试接收响应
    print("\nListening for responses...")
    try:
        while True:
            data, addr = sock.recvfrom(4096)
            message = json.loads(data.decode('utf-8'))
            if message['type'] == 'device_announcement':
                device = message['device']
                print(f"✓ Received announcement from {device['name']} ({addr[0]}:{addr[1]})")
                print(f"  - Type: {device['type']}")
                print(f"  - Platform: {device['platform']}")
                print(f"  - ID: {device['id']}")
    except socket.timeout:
        print("⏱ Timeout - no responses received")
    except Exception as e:
        print(f"✗ Error receiving: {e}")
    finally:
        sock.close()

def test_api_endpoints():
    """测试API端点"""
    print("\n=== API Endpoints Test ===")
    
    import requests
    
    base_url = "http://localhost:8000"
    
    # 测试设备信息端点
    try:
        response = requests.get(f"{base_url}/api/sync/device/info")
        if response.status_code == 200:
            device = response.json()
            print(f"✓ Current device: {device['name']} ({device['id']})")
        else:
            print(f"✗ Device info failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        return
    
    # 测试设备列表端点
    try:
        response = requests.get(f"{base_url}/api/sync/devices")
        if response.status_code == 200:
            devices = response.json()
            print(f"✓ Found {len(devices)} devices")
            for device in devices:
                print(f"  - {device['name']} ({device['ip_address']}): {device['status']}")
        else:
            print(f"✗ Device list failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error getting device list: {e}")
    
    # 测试手动扫描端点
    try:
        response = requests.post(f"{base_url}/api/sync/devices/scan")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Manual scan triggered: {result['message']}")
        else:
            print(f"✗ Scan failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error triggering scan: {e}")

def check_network_interfaces():
    """检查网络接口"""
    print("\n=== Network Interfaces ===")
    
    import netifaces
    
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        addrs = netifaces.ifaddresses(interface)
        
        # 只显示有IPv4地址的接口
        if netifaces.AF_INET in addrs:
            print(f"\nInterface: {interface}")
            for addr in addrs[netifaces.AF_INET]:
                ip = addr['addr']
                netmask = addr.get('netmask', 'N/A')
                broadcast = addr.get('broadcast', 'N/A')
                print(f"  IP: {ip}")
                print(f"  Netmask: {netmask}")
                print(f"  Broadcast: {broadcast}")

def check_firewall_instructions():
    """显示防火墙配置说明"""
    print("\n=== Firewall Configuration ===")
    print("Make sure the following ports are open:")
    print("- Port 8000 (TCP) - API server")
    print("- Port 8001 (UDP) - Device discovery")
    print("\nWindows Firewall:")
    print("1. Open Windows Defender Firewall")
    print("2. Click 'Allow an app or feature'")
    print("3. Add Python.exe or your specific app")
    print("4. Enable both Private and Public networks")
    print("\nOr use PowerShell (Admin):")
    print('New-NetFirewallRule -DisplayName "MAS Discovery" -Direction Inbound -Protocol UDP -LocalPort 8001 -Action Allow')
    print('New-NetFirewallRule -DisplayName "MAS API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow')

def main():
    """主函数"""
    print("MAS Device Discovery Diagnostic Tool")
    print("====================================")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--broadcast":
            test_udp_broadcast()
        elif sys.argv[1] == "--api":
            test_api_endpoints()
        elif sys.argv[1] == "--network":
            check_network_interfaces()
        elif sys.argv[1] == "--firewall":
            check_firewall_instructions()
        else:
            print("Unknown option")
    else:
        # 运行所有测试
        check_network_interfaces()
        test_api_endpoints()
        test_udp_broadcast()
        check_firewall_instructions()

if __name__ == "__main__":
    main()
