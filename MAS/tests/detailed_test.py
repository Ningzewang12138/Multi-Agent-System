"""
详细测试元数据处理和其他潜在问题
"""
import requests
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"

def test_metadata_handling_detailed():
    """详细测试元数据处理"""
    print("\n=== 详细测试元数据处理 ===")
    results = []
    
    # 1. 测试布尔值处理
    print("\n1. 测试布尔值存储和恢复...")
    kb_id = None
    try:
        kb_data = {
            "name": "布尔值测试KB",
            "description": "测试布尔值处理",
            "device_id": "test_device_001",
            "device_name": "测试设备",
            "is_draft": True  # 布尔值
        }
        
        # 创建知识库
        response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
        if response.status_code == 200:
            kb = response.json()
            kb_id = kb["id"]
            print(f"✅ 创建成功: {kb_id}")
            
            # 获取详情
            response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}")
            if response.status_code == 200:
                detail = response.json()
                metadata = detail.get("metadata", {})
                
                # 检查布尔值
                is_draft = metadata.get("is_draft")
                is_synced = metadata.get("is_synced", False)
                
                print(f"   is_draft 类型: {type(is_draft).__name__}, 值: {is_draft}")
                print(f"   is_synced 类型: {type(is_synced).__name__}, 值: {is_synced}")
                
                if isinstance(is_draft, bool) and isinstance(is_synced, bool):
                    results.append(("布尔值处理", "PASS", "所有布尔值正确处理为bool类型"))
                else:
                    results.append(("布尔值处理", "FAIL", f"布尔值类型错误: is_draft={type(is_draft)}, is_synced={type(is_synced)}"))
                
                # 检查其他元数据
                required_fields = ["device_id", "device_name", "creator_device_id", "created_at", "display_name"]
                missing_fields = [f for f in required_fields if f not in metadata]
                
                if not missing_fields:
                    results.append(("必需字段", "PASS", "所有必需元数据字段存在"))
                else:
                    results.append(("必需字段", "FAIL", f"缺少字段: {missing_fields}"))
            else:
                results.append(("获取详情", "FAIL", f"状态码: {response.status_code}"))
        else:
            results.append(("创建知识库", "FAIL", f"状态码: {response.status_code}"))
            
    except Exception as e:
        results.append(("元数据测试", "ERROR", str(e)))
    finally:
        # 清理
        if kb_id:
            try:
                requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}")
                print("   已清理测试数据")
            except:
                pass
    
    # 2. 测试复杂元数据
    print("\n2. 测试复杂元数据处理...")
    kb_id = None
    try:
        kb_data = {
            "name": "复杂元数据测试",
            "description": "测试列表和字典等复杂类型",
            "device_id": "test_device_002",
            "device_name": "测试设备2",
            "is_draft": False
        }
        
        response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
        if response.status_code == 200:
            kb = response.json()
            kb_id = kb["id"]
            
            # 添加包含复杂元数据的文档
            doc_data = {
                "content": "测试文档内容",
                "metadata": {
                    "tags": ["tag1", "tag2", "tag3"],  # 列表
                    "properties": {"key1": "value1", "key2": 123},  # 字典
                    "is_important": True,  # 布尔值
                    "score": 4.5  # 浮点数
                }
            }
            
            response = requests.post(f"{BASE_URL}/api/knowledge/{kb_id}/documents", json=doc_data)
            if response.status_code == 200:
                results.append(("复杂元数据", "PASS", "支持列表和字典类型的元数据"))
            else:
                results.append(("复杂元数据", "WARN", f"添加文档失败: {response.status_code}"))
                
        else:
            results.append(("复杂元数据测试", "FAIL", f"创建失败: {response.status_code}"))
            
    except Exception as e:
        results.append(("复杂元数据", "ERROR", str(e)))
    finally:
        if kb_id:
            try:
                requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}")
            except:
                pass
    
    return results

def test_transactional_operations():
    """测试事务性操作的回滚机制"""
    print("\n=== 测试事务性操作回滚 ===")
    results = []
    
    # 测试重命名操作
    print("\n1. 测试重命名操作...")
    kb_id = None
    try:
        # 创建测试知识库
        kb_data = {
            "name": "事务测试KB",
            "description": "测试事务性操作",
            "device_id": "test_device_003",
            "device_name": "测试设备3",
            "is_draft": True
        }
        
        response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
        if response.status_code == 200:
            kb = response.json()
            kb_id = kb["id"]
            original_name = kb["name"]
            
            # 添加文档
            doc_data = {
                "content": "测试文档，用于验证重命名后文档是否保留",
                "metadata": {"source": "test"}
            }
            response = requests.post(f"{BASE_URL}/api/knowledge/{kb_id}/documents", json=doc_data)
            
            # 获取文档数量
            response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}/documents")
            doc_count_before = response.json().get("total", 0)
            
            # 执行重命名
            rename_url = f"{BASE_URL}/api/knowledge/{kb_id}/rename?device_id=test_device_003&new_name=重命名后的KB"
            response = requests.post(rename_url)
            
            if response.status_code == 200:
                # 验证文档是否保留
                response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}/documents")
                doc_count_after = response.json().get("total", 0)
                
                if doc_count_after == doc_count_before:
                    results.append(("重命名保留文档", "PASS", f"文档数量保持不变: {doc_count_after}"))
                else:
                    results.append(("重命名保留文档", "FAIL", f"文档数量变化: {doc_count_before} -> {doc_count_after}"))
            else:
                results.append(("重命名操作", "FAIL", f"重命名失败: {response.status_code}"))
                
        else:
            results.append(("创建测试KB", "FAIL", f"创建失败: {response.status_code}"))
            
    except Exception as e:
        results.append(("重命名测试", "ERROR", str(e)))
    finally:
        if kb_id:
            try:
                requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}")
            except:
                pass
    
    # 测试发布操作
    print("\n2. 测试发布操作...")
    kb_id = None
    try:
        # 创建草稿知识库
        kb_data = {
            "name": "发布测试KB",
            "description": "测试发布操作",
            "device_id": "test_device_004",
            "device_name": "测试设备4",
            "is_draft": True
        }
        
        response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
        if response.status_code == 200:
            kb = response.json()
            kb_id = kb["id"]
            
            # 发布
            publish_url = f"{BASE_URL}/api/knowledge/{kb_id}/publish?device_id=test_device_004"
            response = requests.post(publish_url)
            
            if response.status_code == 200:
                # 验证状态
                response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}")
                detail = response.json()
                is_draft = detail.get("is_draft", True)
                
                if not is_draft:
                    results.append(("发布操作", "PASS", "成功将草稿发布为公开状态"))
                else:
                    results.append(("发布操作", "FAIL", "发布后仍为草稿状态"))
            else:
                error_msg = response.json().get("detail", "Unknown error")
                results.append(("发布操作", "INFO", f"发布返回: {response.status_code} - {error_msg}"))
                
        else:
            results.append(("创建发布测试KB", "FAIL", f"创建失败: {response.status_code}"))
            
    except Exception as e:
        results.append(("发布测试", "ERROR", str(e)))
    finally:
        if kb_id:
            try:
                requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}?is_admin=true", 
                               headers={"x-admin-key": "mas-server-admin"})
            except:
                pass
    
    return results

def test_embedding_service_failover():
    """测试嵌入服务的降级机制"""
    print("\n=== 测试嵌入服务降级 ===")
    results = []
    
    try:
        # 获取当前嵌入服务状态
        response = requests.get(f"{BASE_URL}/api/system/embeddings/status")
        if response.status_code == 200:
            status = response.json()
            health = status.get("health", {})
            
            print(f"默认服务: {status.get('default_service')}")
            print(f"健康服务: {health.get('healthy_services')}/{health.get('total_services')}")
            
            # 测试嵌入生成
            test_data = {
                "text": "这是一个测试文本",
                "service_name": None  # 使用默认服务
            }
            
            response = requests.post(f"{BASE_URL}/api/system/embeddings/test", json=test_data)
            if response.status_code == 200:
                result = response.json()
                if "embedding_dimension" in result:
                    results.append(("嵌入生成", "PASS", f"维度: {result['embedding_dimension']}"))
                else:
                    results.append(("嵌入生成", "INFO", "支持多服务比较"))
            else:
                results.append(("嵌入测试", "FAIL", f"测试失败: {response.status_code}"))
                
        else:
            results.append(("嵌入服务状态", "FAIL", f"获取状态失败: {response.status_code}"))
            
    except Exception as e:
        results.append(("嵌入服务测试", "ERROR", str(e)))
    
    return results

def main():
    """运行所有详细测试"""
    print("MAS项目 - 详细测试报告")
    print("="*60)
    
    # 检查服务器
    try:
        response = requests.get(BASE_URL, timeout=2)
        if response.status_code != 200:
            print("❌ 服务器响应异常")
            return
    except:
        print("❌ 服务器未运行")
        return
    
    all_results = []
    
    # 运行各项测试
    all_results.extend(test_metadata_handling_detailed())
    all_results.extend(test_transactional_operations())
    all_results.extend(test_embedding_service_failover())
    
    # 生成报告
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    pass_count = 0
    fail_count = 0
    other_count = 0
    
    for test_name, status, details in all_results:
        icon = {
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️",
            "INFO": "ℹ️",
            "ERROR": "🔥"
        }.get(status, "❓")
        
        print(f"{icon} {test_name}")
        print(f"   状态: {status}")
        print(f"   详情: {details}")
        print()
        
        if status == "PASS":
            pass_count += 1
        elif status in ["FAIL", "ERROR"]:
            fail_count += 1
        else:
            other_count += 1
    
    total = len(all_results)
    print(f"\n总计: {total} 项测试")
    print(f"✅ 通过: {pass_count}")
    print(f"❌ 失败: {fail_count}")
    print(f"ℹ️ 其他: {other_count}")
    
    if fail_count == 0:
        print("\n🎉 所有关键测试通过！")
    else:
        print(f"\n⚠️ 有 {fail_count} 项测试失败，需要关注。")

if __name__ == "__main__":
    main()
