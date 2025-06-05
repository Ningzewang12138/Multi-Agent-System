import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing Embedding Services\n" + "="*50)

# 1. 获取嵌入服务状态
print("\n1. Embedding Services Status:")
response = requests.get(f"{BASE_URL}/api/system/embeddings/status")
print(json.dumps(response.json(), indent=2))

# 2. 测试默认嵌入服务
print("\n2. Test Default Embedding Service:")
response = requests.post(
    f"{BASE_URL}/api/system/embeddings/test",
    params={"text": "这是一个测试文本。This is a test text."}
)
if response.status_code == 200:
    data = response.json()
    print(f"Service: {data.get('service', 'default')}")
    print(f"Dimension: {data.get('embedding_dimension')}")
    print(f"Sample: {data.get('embedding_sample', [])[:5]}...")

# 3. 比较所有嵌入服务
print("\n3. Compare All Embedding Services:")
response = requests.post(
    f"{BASE_URL}/api/system/embeddings/test",
    params={"text": "Compare embeddings"}
)
if response.status_code == 200:
    print(json.dumps(response.json(), indent=2))