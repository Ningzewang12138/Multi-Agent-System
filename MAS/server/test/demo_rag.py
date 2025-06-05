import requests
import json
import time

BASE_URL = "http://localhost:8000"

def demo_rag_system():
    print("=== RAG System Demo ===\n")
    
    # 使用现有的知识库
    response = requests.get(f"{BASE_URL}/api/knowledge/")
    kbs = response.json()
    
    if not kbs:
        print("No knowledge bases found. Please create one first.")
        return
    
    # 选择第一个有文档的知识库
    kb_id = None
    for kb in kbs:
        if kb['document_count'] > 0:
            kb_id = kb['id']
            print(f"Using knowledge base: {kb['name']} ({kb['document_count']} documents)")
            break
    
    if not kb_id:
        print("No knowledge base with documents found.")
        return
    
    # 演示查询
    queries = [
        "What is Python and who created it?",
        "Explain the main features of FastAPI",
        "How does machine learning work?",
        "What are the benefits of RAG?",
        "Compare vector databases with traditional databases"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{i}. Question: {query}")
        print("-" * 50)
        
        # RAG 查询
        response = requests.post(
            f"{BASE_URL}/api/chat/rag/completions",
            json={
                "knowledge_base_id": kb_id,
                "messages": [{"role": "user", "content": query}],
                "stream": False,
                "search_limit": 3
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # 显示搜索结果
            if 'search_results' in data:
                print(f"\nRetrieved {data['search_results']['count']} relevant documents:")
                for j, doc in enumerate(data['search_results']['documents'], 1):
                    print(f"  [{j}] {doc['content'][:100]}...")
            
            # 显示 AI 响应
            print(f"\nAI Response:")
            answer = data['choices'][0]['message']['content']
            print(f"{answer}\n")
            
            time.sleep(1)  # 避免请求过快
        else:
            print(f"Error: {response.status_code}")

def interactive_rag():
    """交互式 RAG 演示"""
    print("\n=== Interactive RAG Chat ===")
    print("Type 'quit' to exit\n")
    
    # 选择知识库
    response = requests.get(f"{BASE_URL}/api/knowledge/")
    kbs = response.json()
    
    if not kbs:
        print("No knowledge bases available.")
        return
    
    print("Available knowledge bases:")
    for i, kb in enumerate(kbs):
        print(f"  {i+1}. {kb['name']} ({kb['document_count']} docs)")
    
    kb_index = int(input("\nSelect knowledge base (number): ")) - 1
    kb_id = kbs[kb_index]['id']
    
    print(f"\nUsing: {kbs[kb_index]['name']}")
    print("You can now ask questions. The system will search the knowledge base and provide answers.\n")
    
    while True:
        question = input("\nYour question: ")
        if question.lower() == 'quit':
            break
        
        print("\nSearching knowledge base...")
        
        response = requests.post(
            f"{BASE_URL}/api/chat/rag/completions",
            json={
                "knowledge_base_id": kb_id,
                "messages": [{"role": "user", "content": question}],
                "stream": False,
                "search_limit": 5
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if 'search_results' in data and data['search_results']['count'] > 0:
                print(f"\nFound {data['search_results']['count']} relevant documents")
            
            print("\nAnswer:")
            print(data['choices'][0]['message']['content'])
        else:
            print(f"Error: {response.status_code}")

if __name__ == "__main__":
    # 运行演示
    demo_rag_system()
    
    # 询问是否进入交互模式
    if input("\nWould you like to try interactive mode? (y/n): ").lower() == 'y':
        interactive_rag()