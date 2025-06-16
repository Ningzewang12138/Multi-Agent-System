"""
清理重复的公开知识库
"""
import requests

BASE_URL = "http://localhost:8000"

def cleanup_duplicate_kb():
    """清理重复的公开知识库"""
    print("=== 清理重复的公开知识库 ===\n")
    
    # 1. 获取所有知识库
    response = requests.get(f"{BASE_URL}/api/knowledge/")
    if response.status_code != 200:
        print(f"获取知识库列表失败: {response.status_code}")
        return
    
    kbs = response.json()
    print(f"找到 {len(kbs)} 个知识库\n")
    
    # 2. 查找名为"复杂元数据测试 (测试设备2)"的公开知识库
    target_name = "复杂元数据测试 (测试设备2)"
    to_delete = []
    
    for kb in kbs:
        if kb.get("name") == target_name and not kb.get("is_draft", False):
            to_delete.append(kb)
            print(f"找到公开知识库: {kb['name']} (ID: {kb['id']})")
    
    if not to_delete:
        print("没有找到需要清理的重复知识库")
        return
    
    # 3. 删除知识库
    print(f"\n准备删除 {len(to_delete)} 个知识库...")
    
    for kb in to_delete:
        kb_id = kb["id"]
        # 使用管理员权限删除
        response = requests.delete(
            f"{BASE_URL}/api/knowledge/{kb_id}",
            headers={"x-admin-key": "mas-server-admin"}
        )
        
        if response.status_code == 200:
            print(f"✅ 删除成功: {kb_id}")
        else:
            print(f"❌ 删除失败: {kb_id} - {response.status_code}")
            print(f"   错误: {response.text}")
    
    print("\n清理完成!")

if __name__ == "__main__":
    cleanup_duplicate_kb()
