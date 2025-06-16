"""
诊断复杂元数据测试失败的原因
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_complex_metadata_issue():
    """测试复杂元数据问题"""
    print("=== 诊断复杂元数据测试失败 ===\n")
    
    # 1. 先创建一个简单的知识库
    print("1. 创建简单知识库（不含复杂元数据）...")
    kb_data = {
        "name": "复杂元数据测试",
        "description": "测试列表和字典等复杂类型",
        "device_id": "test_device_002",
        "device_name": "测试设备2",
        "is_draft": False  # 注意：这里是False，可能是问题所在
    }
    
    response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 400:
        print("错误内容:")
        print(response.text)
        try:
            error_data = response.json()
            if "detail" in error_data:
                detail = error_data["detail"]
                if isinstance(detail, dict):
                    print(f"\n错误: {detail.get('error')}")
                    print(f"消息: {detail.get('message')}")
                    print(f"建议: {detail.get('suggestion')}")
                else:
                    print(f"错误详情: {detail}")
        except:
            pass
        
        # 尝试创建草稿版本
        print("\n2. 尝试创建草稿版本...")
        kb_data["is_draft"] = True
        response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
        print(f"状态码: {response.status_code}")
        
    if response.status_code == 200:
        kb = response.json()
        kb_id = kb.get("id")
        print(f"创建成功: {kb_id}")
        
        # 测试添加包含复杂元数据的文档
        print("\n3. 测试添加复杂元数据的文档...")
        
        # 先测试简单元数据
        doc_data = {
            "content": "测试文档内容",
            "metadata": {
                "source": "test",
                "is_important": True,
                "score": 4.5
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/knowledge/{kb_id}/documents", json=doc_data)
        print(f"简单元数据状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 测试包含列表的元数据
            print("\n4. 测试列表元数据...")
            doc_data = {
                "content": "测试文档内容2",
                "metadata": {
                    "tags": ["tag1", "tag2", "tag3"]
                }
            }
            
            response = requests.post(f"{BASE_URL}/api/knowledge/{kb_id}/documents", json=doc_data)
            print(f"列表元数据状态码: {response.status_code}")
            if response.status_code != 200:
                print(f"错误: {response.text}")
            
            # 测试包含字典的元数据
            print("\n5. 测试字典元数据...")
            doc_data = {
                "content": "测试文档内容3",
                "metadata": {
                    "properties": {"key1": "value1", "key2": 123}
                }
            }
            
            response = requests.post(f"{BASE_URL}/api/knowledge/{kb_id}/documents", json=doc_data)
            print(f"字典元数据状态码: {response.status_code}")
            if response.status_code != 200:
                print(f"错误: {response.text}")
        
        # 清理
        try:
            # 如果是公开知识库，需要管理员权限删除
            if not kb_data["is_draft"]:
                response = requests.delete(
                    f"{BASE_URL}/api/knowledge/{kb_id}",
                    headers={"x-admin-key": "mas-server-admin"}
                )
            else:
                response = requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}")
            print(f"\n清理状态: {response.status_code}")
        except:
            pass

def check_existing_public_kb():
    """检查是否存在同名的公开知识库"""
    print("\n6. 检查现有知识库...")
    response = requests.get(f"{BASE_URL}/api/knowledge/")
    if response.status_code == 200:
        kbs = response.json()
        for kb in kbs:
            if "复杂元数据测试" in kb.get("name", ""):
                print(f"找到知识库: {kb['name']} (ID: {kb['id']}, 草稿: {kb.get('is_draft', False)})")

if __name__ == "__main__":
    test_complex_metadata_issue()
    check_existing_public_kb()
