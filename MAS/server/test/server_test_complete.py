import requests
import json
import time
import sys
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
TEST_RESULTS = []

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def test_case(name, func):
    """执行测试用例并记录结果"""
    print(f"\n[TEST] {name}")
    try:
        result = func()
        if result:
            print(f"✓ PASSED")
            TEST_RESULTS.append((name, "PASSED", None))
        else:
            print(f"✗ FAILED")
            TEST_RESULTS.append((name, "FAILED", "Test returned False"))
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        TEST_RESULTS.append((name, "FAILED", str(e)))
        return False
    return True

# ========== 测试用例 ==========

def test_server_root():
    """测试服务器根路径"""
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    print(f"  Server: {data['message']} v{data['version']}")
    return True

def test_health_check():
    """测试健康检查"""
    response = requests.get(f"{BASE_URL}/api/system/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "ollama_connected" in data
    print(f"  Status: {data['status']}")
    print(f"  Ollama Connected: {data['ollama_connected']}")
    print(f"  Model Count: {data.get('model_count', 0)}")
    return data["status"] == "healthy"

def test_system_info():
    """测试系统信息"""
    response = requests.get(f"{BASE_URL}/api/system/info")
    assert response.status_code == 200
    data = response.json()
    print(f"  Platform: {data.get('platform', 'Unknown')}")
    print(f"  Python: {data.get('python_version', 'Unknown')}")
    print(f"  CPU Usage: {data.get('cpu_percent', 0):.1f}%")
    print(f"  Memory Usage: {data.get('memory', {}).get('percent', 0):.1f}%")
    return True

def test_list_models():
    """测试模型列表"""
    response = requests.get(f"{BASE_URL}/api/chat/models")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    print(f"  Available models: {len(data['data'])}")
    if data.get('default_model'):
        print(f"  Default model: {data['default_model']}")
    for model in data['data'][:3]:  # 显示前3个模型
        print(f"    - {model['name']}")
    return len(data['data']) > 0

def test_refresh_models():
    """测试刷新模型列表"""
    response = requests.post(f"{BASE_URL}/api/chat/refresh-models")
    assert response.status_code == 200
    data = response.json()
    print(f"  Model count: {data.get('model_count', 0)}")
    print(f"  Default model: {data.get('default_model', 'None')}")
    return True

def test_chat_non_stream():
    """测试非流式聊天"""
    # 1. 使用自动选择模型
    print("\n  Testing with auto model selection...")
    response = requests.post(
        f"{BASE_URL}/api/chat/completions",
        json={
            "messages": [
                {"role": "user", "content": "Say 'Hello World' and nothing else"}
            ],
            "stream": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
    content = data["choices"][0]["message"]["content"]
    print(f"  Response: {content[:100]}...")
    print(f"  Used model: {data.get('model', 'Unknown')}")
    
    # 2. 使用指定模型
    models_response = requests.get(f"{BASE_URL}/api/chat/models")
    if models_response.status_code == 200:
        models_data = models_response.json()
        if models_data["data"]:
            specific_model = models_data["data"][0]["name"]
            print(f"\n  Testing with specific model: {specific_model}")
            response = requests.post(
                f"{BASE_URL}/api/chat/completions",
                json={
                    "model": specific_model,
                    "messages": [
                        {"role": "user", "content": "Reply with OK"}
                    ],
                    "stream": False
                }
            )
            assert response.status_code == 200
    
    return True

def test_chat_stream():
    """测试流式聊天"""
    response = requests.post(
        f"{BASE_URL}/api/chat/completions",
        json={
            "messages": [
                {"role": "user", "content": "Count from 1 to 3"}
            ],
            "stream": True
        },
        stream=True
    )
    assert response.status_code == 200
    
    print("  Streaming response: ", end="", flush=True)
    content_received = False
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    json_data = json.loads(data)
                    if "content" in json_data:
                        print(json_data["content"], end="", flush=True)
                        content_received = True
                except:
                    pass
    print()  # 新行
    return content_received

def test_multi_turn_conversation():
    """测试多轮对话"""
    messages = [
        {"role": "user", "content": "My name is Alice. Remember this."},
        {"role": "assistant", "content": "Hello Alice! I'll remember your name."},
        {"role": "user", "content": "What's my name?"}
    ]
    
    response = requests.post(
        f"{BASE_URL}/api/chat/completions",
        json={
            "messages": messages,
            "stream": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    content = data["choices"][0]["message"]["content"].lower()
    print(f"  Response: {data['choices'][0]['message']['content'][:100]}...")
    # 检查是否提到了 Alice
    return "alice" in content

def test_temperature_variation():
    """测试温度参数"""
    prompt = "Generate a random number between 1 and 10"
    responses = []
    
    for temp in [0.1, 0.7, 1.5]:
        response = requests.post(
            f"{BASE_URL}/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": temp
            }
        )
        assert response.status_code == 200
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        responses.append(content)
        print(f"  Temperature {temp}: {content[:50]}...")
    
    return True

def test_error_handling():
    """测试错误处理"""
    # 1. 测试无效的模型名
    print("\n  Testing invalid model...")
    response = requests.post(
        f"{BASE_URL}/api/chat/completions",
        json={
            "model": "non-existent-model-12345",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }
    )
    # 应该自动回退到默认模型或返回错误
    print(f"  Status code: {response.status_code}")
    
    # 2. 测试空消息
    print("\n  Testing empty messages...")
    response = requests.post(
        f"{BASE_URL}/api/chat/completions",
        json={
            "messages": [],
            "stream": False
        }
    )
    print(f"  Status code: {response.status_code}")
    
    return True

def test_concurrent_requests():
    """测试并发请求"""
    import concurrent.futures
    
    def make_request(i):
        response = requests.post(
            f"{BASE_URL}/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": f"Say the number {i}"}],
                "stream": False
            }
        )
        return response.status_code == 200
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(make_request, i) for i in range(3)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    print(f"  Concurrent requests successful: {sum(results)}/3")
    return all(results)

def test_knowledge_base_endpoints():
    """测试知识库端点（即使未实现）"""
    response = requests.get(f"{BASE_URL}/api/knowledge/")
    print(f"  Knowledge base status: {response.status_code}")
    return response.status_code in [200, 501]  # 200 或 501 (未实现) 都可接受

# ========== 主测试流程 ==========

def run_all_tests():
    """运行所有测试"""
    print_header("Multi-Agent System Complete Test Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    
    # 基础测试
    print_header("Basic Connectivity Tests")
    test_case("Server Root Endpoint", test_server_root)
    test_case("Health Check", test_health_check)
    test_case("System Information", test_system_info)
    
    # 模型管理测试
    print_header("Model Management Tests")
    test_case("List Models", test_list_models)
    test_case("Refresh Models", test_refresh_models)
    
    # 聊天功能测试
    print_header("Chat Functionality Tests")
    test_case("Non-Streaming Chat", test_chat_non_stream)
    test_case("Streaming Chat", test_chat_stream)
    test_case("Multi-turn Conversation", test_multi_turn_conversation)
    test_case("Temperature Variation", test_temperature_variation)
    
    # 错误处理和边界测试
    print_header("Error Handling Tests")
    test_case("Error Handling", test_error_handling)
    
    # 性能测试
    print_header("Performance Tests")
    test_case("Concurrent Requests", test_concurrent_requests)
    
    # 其他端点测试
    print_header("Additional Endpoints")
    test_case("Knowledge Base Endpoints", test_knowledge_base_endpoints)
    
    # 测试结果总结
    print_header("Test Summary")
    passed = sum(1 for _, status, _ in TEST_RESULTS if status == "PASSED")
    failed = sum(1 for _, status, _ in TEST_RESULTS if status == "FAILED")
    total = len(TEST_RESULTS)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    if failed > 0:
        print("\nFailed Tests:")
        for name, status, error in TEST_RESULTS:
            if status == "FAILED":
                print(f"  - {name}: {error}")
    
    return failed == 0

if __name__ == "__main__":
    try:
        # 确保服务器正在运行
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not responding properly")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running?")
        print(f"   Please start the server and try again.")
        print(f"   URL: {BASE_URL}")
        sys.exit(1)
    
    # 运行所有测试
    success = run_all_tests()
    
    if success:
        print("\n✅ All tests passed! The system is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    sys.exit(0 if success else 1)