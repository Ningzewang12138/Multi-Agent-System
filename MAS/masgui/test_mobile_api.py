import requests
import json
import socket

# 配置
PC_IP = "192.168.1.3"  # 替换为你的 PC IP
BASE_URL = f"http://{PC_IP}:8000"

def get_local_ip():
    """获取本机IP地址"""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except:
        return "Unknown"

def test_mobile_connectivity():
    print(f"Testing connectivity from mobile to PC ({PC_IP})...\n")
    
    # 1. 测试基础连接
    print("1. Testing basic connection...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✓ Successfully connected to PC server")
            print(f"  Response: {response.json()}")
        else:
            print("✗ Connection failed")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # 2. 测试聊天 API
    print("\n2. Testing chat API...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello from mobile"}],
                "stream": False
            }
        )
        if response.status_code == 200:
            print("✓ Chat API working")
            content = response.json()['choices'][0]['message']['content']
            print(f"  Response: {content[:100]}...")
        else:
            print("✗ Chat API failed")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 3. 测试知识库 API
    print("\n3. Testing knowledge base API...")
    try:
        response = requests.get(f"{BASE_URL}/api/knowledge/")
        if response.status_code == 200:
            kbs = response.json()
            print(f"✓ Found {len(kbs)} knowledge bases")
            for kb in kbs[:3]:
                print(f"  - {kb['name']}: {kb['document_count']} docs")
        else:
            print("✗ Knowledge base API failed")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 4. 测试模型列表 API
    print("\n4. Testing models API...")
    try:
        response = requests.get(f"{BASE_URL}/api/chat/models")
        if response.status_code == 200:
            models = response.json()['data']
            print(f"✓ Found {len(models)} models")
            for model in models[:3]:
                print(f"  - {model['id']}")
        else:
            print("✗ Models API failed")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n✓ All tests completed!")
    print(f"\nTo use in Flutter app:")
    print(f"1. Update app_config.dart with server URL: http://{PC_IP}:8000")
    print(f"2. Make sure both devices are on the same network")
    print(f"3. Run 'flutter run' in the masgui directory")

if __name__ == "__main__":
    # 获取本机 IP
    local_ip = get_local_ip()
    print(f"Your PC IP address: {local_ip}")
    print("Make sure this matches the IP in your Flutter app configuration.\n")
    
    # 如果获取到的IP与配置的不同，提示用户
    if local_ip != PC_IP and local_ip != "Unknown":
        print(f"⚠️  WARNING: Detected IP ({local_ip}) differs from configured IP ({PC_IP})")
        print(f"   Update PC_IP in this script and app_config.dart to: {local_ip}\n")
    
    test_mobile_connectivity()
