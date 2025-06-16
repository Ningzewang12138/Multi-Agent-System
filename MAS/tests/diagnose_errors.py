"""
诊断服务器错误
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def diagnose_issues():
    """诊断服务器问题"""
    print("=== 诊断服务器问题 ===\n")
    
    # 1. 检查服务器基本状态
    print("1. 检查服务器状态...")
    try:
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 服务器运行正常")
            print(f"   功能状态: {json.dumps(data.get('features', {}), indent=2)}")
        else:
            print(f"❌ 服务器响应异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接服务器: {e}")
        return
    
    # 2. 创建简单的知识库测试
    print("\n2. 测试创建知识库...")
    kb_id = None
    try:
        kb_data = {
            "name": "诊断测试KB",
            "description": "诊断问题",
            "device_id": "test_device",
            "device_name": "测试设备",
            "is_draft": True
        }
        
        response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
        print(f"   创建状态码: {response.status_code}")
        
        if response.status_code == 200:
            kb = response.json()
            kb_id = kb.get("id")
            print(f"   ✅ 创建成功: ID = {kb_id}")
            
            # 尝试获取详情
            print("\n3. 测试获取知识库详情...")
            response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}")
            print(f"   获取详情状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   ❌ 错误: {response.text}")
            else:
                detail = response.json()
                print(f"   ✅ 获取成功")
                print(f"   元数据: {json.dumps(detail.get('metadata', {}), indent=2)}")
        else:
            print(f"   ❌ 创建失败: {response.text}")
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    finally:
        # 清理
        if kb_id:
            try:
                requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}")
                print(f"\n   已清理测试数据")
            except:
                pass
    
    # 3. 检查列表接口
    print("\n4. 测试列出知识库...")
    try:
        response = requests.get(f"{BASE_URL}/api/knowledge/")
        print(f"   列表状态码: {response.status_code}")
        
        if response.status_code == 200:
            kbs = response.json()
            print(f"   ✅ 知识库数量: {len(kbs)}")
        else:
            print(f"   ❌ 错误: {response.text}")
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    
    # 4. 检查嵌入服务
    print("\n5. 检查嵌入服务...")
    try:
        response = requests.get(f"{BASE_URL}/api/system/embeddings/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ 嵌入服务状态: {status.get('status')}")
            health = status.get('health', {})
            if health:
                print(f"   健康服务: {health.get('healthy_services')}/{health.get('total_services')}")
        else:
            print(f"   ❌ 获取状态失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    
    # 5. 检查重命名接口
    print("\n6. 测试重命名接口...")
    kb_id = None
    try:
        # 先创建一个知识库
        kb_data = {
            "name": "重命名测试",
            "description": "测试重命名",
            "device_id": "rename_test",
            "device_name": "重命名设备",
            "is_draft": True
        }
        
        response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
        if response.status_code == 200:
            kb = response.json()
            kb_id = kb.get("id")
            print(f"   创建成功: {kb_id}")
            
            # 尝试重命名
            rename_url = f"{BASE_URL}/api/knowledge/{kb_id}/rename"
            params = {
                "device_id": "rename_test",
                "new_name": "新名称"
            }
            response = requests.post(rename_url, params=params)
            print(f"   重命名状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   ❌ 重命名错误: {response.text}")
        
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    finally:
        if kb_id:
            try:
                requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}")
            except:
                pass

if __name__ == "__main__":
    diagnose_issues()
