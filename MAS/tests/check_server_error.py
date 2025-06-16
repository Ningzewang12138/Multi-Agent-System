"""
查看服务器的实际错误
"""
import requests
import json
import traceback

BASE_URL = "http://localhost:8000"

def test_error_details():
    """测试并获取详细错误信息"""
    
    print("1. 测试创建知识库...")
    kb_data = {
        "name": "错误测试KB",
        "description": "查看错误",
        "device_id": "test_device",
        "device_name": "测试设备",
        "is_draft": True
    }
    
    response = requests.post(f"{BASE_URL}/api/knowledge/", json=kb_data)
    print(f"创建状态: {response.status_code}")
    
    if response.status_code == 200:
        kb = response.json()
        kb_id = kb.get("id")
        print(f"创建成功: {kb_id}")
        
        # 测试获取详情
        print("\n2. 测试获取详情...")
        response = requests.get(f"{BASE_URL}/api/knowledge/{kb_id}")
        print(f"获取详情状态: {response.status_code}")
        
        if response.status_code != 200:
            print("错误内容:")
            print(response.text)
            
            # 尝试解析JSON错误
            try:
                error_data = response.json()
                if "detail" in error_data:
                    detail = error_data["detail"]
                    if isinstance(detail, dict):
                        print(f"\n错误类型: {detail.get('error')}")
                        print(f"错误消息: {detail.get('message')}")
                        print(f"建议: {detail.get('suggestion')}")
                        if "debug_info" in detail:
                            print(f"调试信息: {detail.get('debug_info')}")
                    else:
                        print(f"错误详情: {detail}")
            except:
                pass
        else:
            print("获取成功")
            detail = response.json()
            print(f"元数据: {json.dumps(detail.get('metadata', {}), indent=2)}")
        
        # 清理
        try:
            requests.delete(f"{BASE_URL}/api/knowledge/{kb_id}")
        except:
            pass
    else:
        print("创建失败:")
        print(response.text)

if __name__ == "__main__":
    test_error_details()
