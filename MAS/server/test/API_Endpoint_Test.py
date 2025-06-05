import requests
import json
import time

base_url = "http://localhost:11434"

print("=== Testing Ollama API Endpoints ===\n")

# 1. 获取版本信息
print("1. Testing version endpoint...")
for endpoint in ["/api/version", "/version", "/"]:
    try:
        response = requests.get(f"{base_url}{endpoint}", timeout=5)
        print(f"GET {endpoint} -> Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.text[:100]}")
    except Exception as e:
        print(f"GET {endpoint} -> Error: {type(e).__name__}")
print()

# 2. 列出模型
print("2. Testing list models...")
for endpoint in ["/api/tags", "/api/models", "/v1/models"]:
    try:
        response = requests.get(f"{base_url}{endpoint}", timeout=5)
        print(f"GET {endpoint} -> Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if "models" in data:
                print(f"Found {len(data['models'])} models")
                if data['models']:
                    print(f"First model: {data['models'][0].get('name', 'unknown')}")
            elif "data" in data:
                print(f"Found {len(data['data'])} models")
    except Exception as e:
        print(f"GET {endpoint} -> Error: {type(e).__name__}")
print()

# 3. 测试 generate API
print("3. Testing generate API...")
generate_payload = {
    "model": "deepseek-r1",
    "prompt": "Say hello",
    "stream": False
}

for endpoint in ["/api/generate", "/generate", "/v1/completions"]:
    try:
        print(f"\nPOST {endpoint}")
        response = requests.post(
            f"{base_url}{endpoint}", 
            json=generate_payload,
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            if "response" in data:
                print(f"Response text: {data['response'][:50]}...")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)[:100]}")

# 4. 测试 chat API
print("\n4. Testing chat API...")
chat_payload = {
    "model": "deepseek-r1",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": False
}

for endpoint in ["/api/chat", "/chat", "/v1/chat/completions"]:
    try:
        print(f"\nPOST {endpoint}")
        response = requests.post(
            f"{base_url}{endpoint}",
            json=chat_payload,
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            if "message" in data:
                print(f"Message: {data['message']}")
        else:
            print(f"Error response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)[:100]}")

# 5. 测试具体模型的信息
print("\n5. Testing model info...")
model_name = "deepseek-r1"
for endpoint in [f"/api/show", f"/api/tags/{model_name}"]:
    try:
        payload = {"name": model_name} if "show" in endpoint else None
        if payload:
            response = requests.post(f"{base_url}{endpoint}", json=payload, timeout=10)
        else:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
        print(f"{endpoint} -> Status: {response.status_code}")
    except Exception as e:
        print(f"{endpoint} -> Error: {type(e).__name__}")