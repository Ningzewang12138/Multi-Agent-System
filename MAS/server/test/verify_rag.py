import requests

BASE_URL = "http://localhost:8000"

print("Verifying RAG System Status\n" + "="*40)

# 1. 检查服务
response = requests.get(f"{BASE_URL}/")
features = response.json()["features"]
print(f"✓ Chat Service: {'✓' if features['chat'] else '✗'}")
print(f"✓ Knowledge Base: {'✓' if features['knowledge_base'] else '✗'}")
print(f"✓ Embeddings: {'✓' if features['embeddings'] else '✗'}")

# 2. 检查嵌入服务
response = requests.get(f"{BASE_URL}/api/system/embeddings/status")
if response.ok:
    emb_data = response.json()
    print(f"\n✓ Embedding Service: {emb_data['default_service']}")

# 3. 检查知识库
response = requests.get(f"{BASE_URL}/api/knowledge/")
kbs = response.json()
print(f"\n✓ Knowledge Bases: {len(kbs)}")
for kb in kbs:
    print(f"  - {kb['name']}: {kb['document_count']} documents")

# 4. 快速 RAG 测试
if kbs and kbs[0]['document_count'] > 0:
    kb_id = kbs[0]['id']
    response = requests.post(
        f"{BASE_URL}/api/chat/rag/completions",
        json={
            "knowledge_base_id": kb_id,
            "messages": [{"role": "user", "content": "test"}],
            "stream": False
        }
    )
    print(f"\n✓ RAG Chat: {'Working' if response.status_code == 200 else 'Failed'}")

print("\n✓ All systems operational!" if all(features.values()) else "\n✗ Some systems are not working")