import requests
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

print("Testing Knowledge Base API\n" + "="*50)

# 1. 创建知识库
print("\n1. Creating Knowledge Base...")
response = requests.post(
    f"{BASE_URL}/api/knowledge",
    json={
        "name": "test_kb_demo",
        "description": "Test knowledge base for RAG"
    }
)
if response.status_code == 200:
    kb_data = response.json()
    kb_id = kb_data["id"]
    print(f"Created KB: {kb_id}")
else:
    print(f"Error: {response.status_code} - {response.text}")
    # 如果创建失败，尝试使用现有的
    response = requests.get(f"{BASE_URL}/api/knowledge/")
    if response.status_code == 200:
        kbs = response.json()
        if kbs:
            kb_id = kbs[0]["id"]
            print(f"Using existing KB: {kb_id}")
        else:
            print("No knowledge bases available")
            exit(1)
    else:
        exit(1)

# 2. 添加文档
print("\n2. Adding Documents...")
documents = [
    {
        "content": "Python is a high-level programming language. It was created by Guido van Rossum and first released in 1991. Python emphasizes code readability and simplicity.",
        "metadata": {"source": "manual", "topic": "programming"}
    },
    {
        "content": "Machine learning is a subset of artificial intelligence. It enables systems to learn and improve from experience without being explicitly programmed. Common algorithms include neural networks, decision trees, and support vector machines.",
        "metadata": {"source": "manual", "topic": "AI"}
    },
    {
        "content": "FastAPI is a modern web framework for building APIs with Python. It's based on standard Python type hints and is very fast. It includes automatic API documentation.",
        "metadata": {"source": "manual", "topic": "web development"}
    }
]

for i, doc in enumerate(documents):
    response = requests.post(
        f"{BASE_URL}/api/knowledge/{kb_id}/documents",
        json=doc
    )
    if response.status_code == 200:
        result = response.json()
        print(f"  Added document {i+1}: {result['chunk_count']} chunks")
    else:
        print(f"  Error adding document {i+1}: {response.status_code}")

# 3. 搜索知识库
print("\n3. Searching Knowledge Base...")
queries = ["What is Python?", "Tell me about machine learning", "How fast is FastAPI?"]

for query in queries:
    print(f"\n  Query: '{query}'")
    response = requests.post(
        f"{BASE_URL}/api/knowledge/{kb_id}/search",
        json={
            "query": query,
            "limit": 3
        }
    )
    if response.status_code == 200:
        results = response.json()
        print(f"  Found {len(results)} results")
        for i, result in enumerate(results[:2]):
            print(f"    Result {i+1} (score: {result['score']:.3f}): {result['content'][:100]}...")
    else:
        print(f"  Search error: {response.status_code}")

# 4. 测试 RAG 聊天
print("\n4. Testing RAG Chat...")
response = requests.post(
    f"{BASE_URL}/api/chat/rag/completions",
    json={
        "knowledge_base_id": kb_id,
        "messages": [
            {"role": "user", "content": "What programming language was created by Guido van Rossum?"}
        ],
        "stream": False,
        "search_limit": 3
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"  Model: {data['model']}")
    print(f"  Answer: {data['choices'][0]['message']['content']}")
    if 'search_results' in data:
        print(f"  Search results used: {data['search_results']['count']}")
        # 显示使用的文档
        for i, doc in enumerate(data['search_results']['documents']):
            print(f"    Doc {i+1}: {doc['content'][:80]}...")
else:
    print(f"  Error: {response.status_code} - {response.text}")

# 5. 测试流式 RAG
print("\n5. Testing Streaming RAG Chat...")
response = requests.post(
    f"{BASE_URL}/api/chat/rag/completions",
    json={
        "knowledge_base_id": kb_id,
        "messages": [
            {"role": "user", "content": "Explain machine learning algorithms"}
        ],
        "stream": True,
        "search_limit": 3
    },
    stream=True
)

if response.status_code == 200:
    print("  Streaming response: ", end="", flush=True)
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    print("\n  Stream completed")
                    break
                try:
                    json_data = json.loads(data)
                    if json_data.get('type') == 'content':
                        print(json_data['content'], end="", flush=True)
                    elif json_data.get('type') == 'search_results':
                        print(f"\n  [Found {json_data['count']} relevant documents]")
                except:
                    pass

# 6. 获取知识库统计
print("\n\n6. Knowledge Base Stats...")
response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}/stats")
if response.status_code == 200:
    stats = response.json()
    print(f"  Document count: {stats['document_count']}")
    print(f"  Embedding service: {stats['embedding_service']}")
    print(f"  Embedding dimension: {stats['embedding_dimension']}")

print("\n=== Test Complete ===")