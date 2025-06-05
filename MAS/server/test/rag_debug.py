import requests
import json

BASE_URL = "http://localhost:8000"

# 1. 首先检查 RAG 端点是否存在
print("1. Checking if RAG endpoint exists...")
response = requests.options(f"{BASE_URL}/api/chat/rag/completions")
print(f"OPTIONS request status: {response.status_code}")

# 2. 检查普通聊天是否工作
print("\n2. Testing normal chat...")
response = requests.post(
    f"{BASE_URL}/api/chat/completions",
    json={
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False
    }
)
print(f"Normal chat status: {response.status_code}")
if response.ok:
    print("Normal chat works!")

# 3. 列出知识库
print("\n3. Listing knowledge bases...")
response = requests.get(f"{BASE_URL}/api/knowledge/")
print(f"List KB status: {response.status_code}")
if response.ok:
    kbs = response.json()
    print(f"Found {len(kbs)} knowledge bases")
    if kbs:
        print(f"First KB: {kbs[0]['id']}")
        
        # 4. 尝试简单的 RAG 请求
        print("\n4. Testing simple RAG request...")
        kb_id = kbs[0]['id']
        
        # 先确保知识库有内容
        response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}/stats")
        if response.ok:
            stats = response.json()
            print(f"KB has {stats['document_count']} documents")
        
        # 尝试 RAG 请求
        rag_url = f"{BASE_URL}/api/chat/rag/completions"
        rag_data = {
            "knowledge_base_id": kb_id,
            "messages": [{"role": "user", "content": "test"}],
            "stream": False,
            "search_limit": 1
        }
        
        print(f"RAG URL: {rag_url}")
        print(f"RAG Data: {json.dumps(rag_data, indent=2)}")
        
        response = requests.post(rag_url, json=rag_data)
        print(f"RAG status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'Not set')}")
        print(f"Response length: {len(response.text)}")
        
        if response.text:
            print(f"First 200 chars: {response.text[:200]}")
        else:
            print("Empty response!")