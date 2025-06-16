"""
快速测试异常处理器
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_validation_error():
    """测试验证错误的友好消息"""
    print("=== 测试验证错误处理 ===\n")
    
    # 测试缺少必需字段
    print("1. 测试缺少必需字段...")
    kb_data = {
        "name": "测试KB"
        # 故意缺少 device_id 和 device_name
    }
    
    response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 422:
        data = response.json()
        detail = data.get("detail", {})
        
        if isinstance(detail, dict) and "error" in detail:
            print("✅ 使用了新的友好错误格式")
            print(f"错误: {detail.get('error')}")
            print(f"消息: {detail.get('message')}")
            print(f"建议: {detail.get('suggestion')}")
            
            details = detail.get('details', {})
            if 'missing_fields' in details:
                print(f"缺少字段: {details['missing_fields']}")
        else:
            print("❌ 仍在使用旧的错误格式")
            print(f"错误详情: {json.dumps(detail, indent=2)}")
    
    print("\n" + "-"*50 + "\n")
    
    # 测试字段类型错误
    print("2. 测试字段类型错误...")
    kb_data = {
        "name": "测试KB",
        "device_id": "test_device",
        "device_name": "测试设备",
        "is_draft": "yes"  # 应该是布尔值
    }
    
    response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 422:
        data = response.json()
        detail = data.get("detail", {})
        
        if isinstance(detail, dict) and "error" in detail:
            print("✅ 使用了新的友好错误格式")
            print(f"错误: {detail.get('error')}")
            print(f"消息: {detail.get('message')}")
            print(f"建议: {detail.get('suggestion')}")
        else:
            print("❌ 仍在使用旧的错误格式")

def test_server_error():
    """测试服务器错误处理"""
    print("\n=== 测试服务器错误处理 ===\n")
    
    # 测试不存在的知识库
    print("测试访问不存在的知识库...")
    response = requests.get(f"{BASE_URL}/api/knowledge/nonexistent_kb_id")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 404:
        data = response.json()
        detail = data.get("detail")
        
        if isinstance(detail, dict) and "error" in detail:
            print("✅ 使用了新的友好错误格式")
            print(f"错误: {detail.get('error')}")
            print(f"消息: {detail.get('message')}")
            print(f"建议: {detail.get('suggestion')}")
        else:
            print("ℹ️ 使用了标准错误格式")
            print(f"错误: {detail}")

def main():
    print("快速测试异常处理器\n")
    
    # 检查服务器
    try:
        response = requests.get(BASE_URL, timeout=2)
        if response.status_code != 200:
            print("❌ 服务器响应异常")
            return
    except:
        print("❌ 服务器未运行")
        print("请先启动服务器: cd server && python main.py")
        return
    
    # 运行测试
    test_validation_error()
    test_server_error()
    
    print("\n测试完成！")
    print("\n注意：如果仍显示旧格式错误，请重启服务器以加载新的异常处理器。")

if __name__ == "__main__":
    main()
