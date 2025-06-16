"""
元数据处理工具
统一处理ChromaDB元数据的类型转换和验证
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MetadataHandler:
    """元数据处理器"""
    
    # ChromaDB支持的元数据类型
    SUPPORTED_TYPES = (str, int, float, bool)
    
    # 需要特殊处理的布尔字段
    BOOLEAN_FIELDS = [
        'is_draft',
        'is_synced',
        'is_published',
        'is_deleted',
        'is_active'
    ]
    
    @staticmethod
    def clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理和转换元数据，确保与ChromaDB兼容
        
        Args:
            metadata: 原始元数据
            
        Returns:
            清理后的元数据
        """
        if not metadata:
            return {}
        
        cleaned = {}
        
        for key, value in metadata.items():
            # 跳过None值
            if value is None:
                continue
            
            # 处理布尔值
            if key in MetadataHandler.BOOLEAN_FIELDS:
                # ChromaDB可能将布尔值存储为整数
                if isinstance(value, int):
                    cleaned[key] = bool(value)
                elif isinstance(value, str):
                    cleaned[key] = value.lower() in ('true', '1', 'yes')
                else:
                    cleaned[key] = bool(value)
            
            # 处理其他类型
            elif isinstance(value, MetadataHandler.SUPPORTED_TYPES):
                cleaned[key] = value
            
            # 将复杂类型转换为字符串
            else:
                try:
                    import json
                    cleaned[key] = json.dumps(value, ensure_ascii=False)
                except:
                    cleaned[key] = str(value)
                    
        return cleaned
    
    @staticmethod
    def restore_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        恢复元数据类型，将ChromaDB存储的值转换回原始类型
        
        Args:
            metadata: ChromaDB返回的元数据
            
        Returns:
            恢复后的元数据
        """
        if not metadata:
            return {}
        
        restored = {}
        
        for key, value in metadata.items():
            # 恢复布尔值
            if key in MetadataHandler.BOOLEAN_FIELDS:
                if isinstance(value, int):
                    restored[key] = bool(value)
                elif isinstance(value, str):
                    restored[key] = value.lower() in ('true', '1', 'yes')
                else:
                    restored[key] = bool(value)
            
            # 尝试恢复JSON字符串
            elif isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                try:
                    import json
                    restored[key] = json.loads(value)
                except:
                    restored[key] = value
            
            else:
                restored[key] = value
                
        return restored
    
    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证元数据是否符合ChromaDB要求
        
        Args:
            metadata: 要验证的元数据
            
        Returns:
            (是否有效, 错误信息)
        """
        if not isinstance(metadata, dict):
            return False, "Metadata must be a dictionary"
        
        for key, value in metadata.items():
            # 检查键类型
            if not isinstance(key, str):
                return False, f"Metadata key must be string, got {type(key)}"
            
            # 检查值类型
            if value is not None and not isinstance(value, MetadataHandler.SUPPORTED_TYPES):
                # 尝试转换
                try:
                    if isinstance(value, (list, dict)):
                        import json
                        json.dumps(value)
                    else:
                        str(value)
                except:
                    return False, f"Metadata value for key '{key}' cannot be serialized"
        
        return True, None
    
    @staticmethod
    def merge_metadata(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并元数据，更新值会覆盖基础值
        
        Args:
            base: 基础元数据
            updates: 更新的元数据
            
        Returns:
            合并后的元数据
        """
        merged = base.copy() if base else {}
        
        if updates:
            for key, value in updates.items():
                if value is None and key in merged:
                    # 如果更新值为None，删除该键
                    del merged[key]
                else:
                    merged[key] = value
        
        # 清理合并后的元数据
        return MetadataHandler.clean_metadata(merged)


# 创建全局实例
metadata_handler = MetadataHandler()
