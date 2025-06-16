"""
测试修复后的错误处理和元数据处理
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_embedding_health():
    """测试嵌入服务健康检查"""
    print("\n=== 测试嵌入服务健康状态 ===")
    
    # 获取状态
    response = requests.get(f"{BASE_URL}/api/system/embeddings/status")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # 执行健康检查
    print("\n执行健康检查...")
    response = requests.post(f"{BASE_URL}/api/system/embeddings/check")
    print(f"Check Results: {json.dumps(response.json(), indent=2)}")

def test_metadata_handling():
    """测试元数据处理"""
    print("\n=== 测试元数据处理 ===")
    
    # 创建测试知识库
    kb_data = {
        "name": "元数据测试KB",
        "description": "测试布尔值和复杂元数据处理",
        "device_id": "test_device_001",
        "device_name": "测试设备",
        "is_draft": True
    }
    
    print("创建知识库...")
    response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
    if response.status_code == 200:
        kb = response.json()
        kb_id = kb["id"]
        print(f"创建成功: {kb_id}")
        
        # 获取知识库详情
        print("\n获取知识库详情...")
        response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}")
        kb_detail = response.json()
        print(f"元数据: {json.dumps(kb_detail.get('metadata', {}), indent=2)}")
        
        # 验证布尔值
        metadata = kb_detail.get("metadata", {})
        print(f"\nis_draft 类型: {type(metadata.get('is_draft'))}")
        print(f"is_draft 值: {metadata.get('is_draft')}")
        
        # 清理测试数据
        print("\n清理测试数据...")
        response = requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}")
        print(f"删除状态: {response.status_code}")
    else:
        print(f"创建失败: {response.json()}")

def test_transactional_operations():
    """测试事务性操作"""
    print("\n=== 测试事务性操作 ===")
    
    # 创建测试知识库
    kb_data = {
        "name": "事务测试KB",
        "description": "测试发布和重命名的回滚机制",
        "device_id": "test_device_001",
        "device_name": "测试设备",
        "is_draft": True
    }
    
    response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
    if response.status_code == 200:
        kb = response.json()
        kb_id = kb["id"]
        print(f"创建成功: {kb_id}")
        
        # 添加一些测试文档
        print("\n添加测试文档...")
        doc_data = {
            "content": "这是一个测试文档，用于验证事务性操作。",
            "metadata": {
                "source": "test",
                "type": "transaction_test"
            }
        }
        response = requests.post(f"{BASE_URL}/api/knowledge/{kb_id}/documents", json=doc_data)
        print(f"添加文档状态: {response.status_code}")
        
        # 测试重命名
        print("\n测试重命名...")
        rename_url = f"{BASE_URL}/api/knowledge/{kb_id}/rename"
        rename_data = {
            "new_name": "重命名后的KB"
        }
        response = requests.post(f"{rename_url}?device_id=test_device_001&new_name=重命名后的KB", json=rename_data)
        print(f"重命名状态: {response.status_code}")
        if response.status_code == 200:
            print(f"新名称: {response.json().get('new_name')}")
        
        # 验证文档还在
        print("\n验证文档...")
        response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}/documents")
        if response.status_code == 200:
            docs = response.json()
            print(f"文档数量: {docs.get('total', 0)}")
        
        # 清理
        print("\n清理测试数据...")
        response = requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}")
        print(f"删除状态: {response.status_code}")
    else:
        print(f"创建失败: {response.json()}")

def test_error_messages():
    """测试改进的错误消息"""
    print("\n=== 测试错误消息 ===")
    
    # 测试无效请求
    print("\n测试创建知识库时缺少必需字段...")
    kb_data = {
        "name": "错误测试KB"
        # 缺少 device_id 和 device_name
    }
    response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_detail = error_data.get("detail", {})
            
            if isinstance(error_detail, dict):
                print(f"错误: {error_detail.get('error', '')}")
                print(f"消息: {error_detail.get('message', '')}")
                print(f"建议: {error_detail.get('suggestion', '')}")
                
                # 显示详细信息
                details = error_detail.get('details', {})
                if details:
                    print(f"详细信息: {json.dumps(details, indent=2)}")
            else:
                # 如果是旧格式的错误
                print(f"错误 (旧格式): {error_detail}")
        except:
            print(f"无法解析错误响应: {response.text}")

def main():
    """主测试函数"""
    print("开始测试错误处理和元数据处理改进...")
    
    # 等待服务器启动
    time.sleep(2)
    
    try:
        # 运行各项测试
        test_embedding_health()
        test_metadata_handling()
        test_transactional_operations()
        test_error_messages()
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
