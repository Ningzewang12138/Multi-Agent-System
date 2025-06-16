"""
测试元数据处理器修复
"""
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server'))

try:
    from utils.metadata_handler import metadata_handler
    print("✅ 成功导入 metadata_handler")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    exit(1)

# 测试数据
test_metadata = {
    "device_id": "test_device",
    "device_name": "测试设备",
    "is_draft": True,
    "is_synced": 0,  # 整数形式的布尔值
    "count": 123,  # 整数
    "score": 4.5,  # 浮点数
    "tags": ["tag1", "tag2"],  # 列表
    "properties": {"key": "value"}  # 字典
}

print("\n原始元数据:")
for k, v in test_metadata.items():
    print(f"  {k}: {v} (类型: {type(v).__name__})")

# 测试清理
print("\n测试 clean_metadata...")
cleaned = metadata_handler.clean_metadata(test_metadata)
print("清理后的元数据:")
for k, v in cleaned.items():
    print(f"  {k}: {v} (类型: {type(v).__name__})")

# 测试恢复
print("\n测试 restore_metadata...")
# 模拟ChromaDB存储后的数据
stored_metadata = {
    "device_id": "test_device",
    "device_name": "测试设备", 
    "is_draft": 1,  # 布尔值被存储为整数
    "is_synced": 0,
    "count": 123,
    "score": 4.5,
    "tags": '["tag1", "tag2"]',  # JSON字符串
    "properties": '{"key": "value"}'
}

restored = metadata_handler.restore_metadata(stored_metadata)
print("恢复后的元数据:")
for k, v in restored.items():
    print(f"  {k}: {v} (类型: {type(v).__name__})")

# 验证布尔值
print("\n验证布尔值处理:")
print(f"  is_draft 是布尔值: {isinstance(restored.get('is_draft'), bool)}")
print(f"  is_synced 是布尔值: {isinstance(restored.get('is_synced'), bool)}")

print("\n✅ 元数据处理器测试完成")
