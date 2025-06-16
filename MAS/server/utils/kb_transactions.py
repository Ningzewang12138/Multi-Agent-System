"""
知识库事务性操作
提供备份和恢复机制，确保操作的原子性
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import tempfile
import os

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeBaseBackup:
    """知识库备份数据"""
    kb_id: str
    name: str
    description: str
    metadata: Dict[str, Any]
    documents: List[Dict[str, Any]]
    embeddings: List[List[float]]
    metadatas: List[Dict[str, Any]]
    ids: List[str]


class TransactionalKBOperations:
    """知识库事务性操作管理器"""
    
    def __init__(self, vector_db_service):
        self.vector_db = vector_db_service
        self.backups: Dict[str, KnowledgeBaseBackup] = {}
    
    def backup_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBaseBackup]:
        """
        备份知识库
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            备份数据，如果失败返回None
        """
        try:
            # 获取集合信息
            collection = self.vector_db.client.get_collection(name=kb_id)
            
            # 获取所有文档数据
            results = collection.get(
                include=["embeddings", "documents", "metadatas"]
            )
            
            # 获取集合元数据
            metadata = collection.metadata or {}
            
            # 创建备份
            backup = KnowledgeBaseBackup(
                kb_id=kb_id,
                name=collection.name,
                description=metadata.get("description", ""),
                metadata=metadata,
                documents=results.get("documents", []),
                embeddings=results.get("embeddings", []),
                metadatas=results.get("metadatas", []),
                ids=results.get("ids", [])
            )
            
            # 存储备份
            self.backups[kb_id] = backup
            
            # 同时保存到临时文件以防程序崩溃
            self._save_backup_to_file(backup)
            
            logger.info(f"Created backup for knowledge base {kb_id}")
            return backup
            
        except Exception as e:
            logger.error(f"Failed to backup knowledge base {kb_id}: {e}")
            return None
    
    def restore_knowledge_base(self, kb_id: str) -> bool:
        """
        恢复知识库
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            是否恢复成功
        """
        try:
            # 尝试从内存获取备份
            backup = self.backups.get(kb_id)
            
            # 如果内存中没有，尝试从文件恢复
            if not backup:
                backup = self._load_backup_from_file(kb_id)
                
            if not backup:
                logger.error(f"No backup found for knowledge base {kb_id}")
                return False
            
            # 删除当前集合（如果存在）
            try:
                self.vector_db.delete_collection(kb_id)
            except:
                pass
            
            # 重新创建集合
            self.vector_db.create_collection(
                name=backup.name,
                description=backup.description,
                metadata=backup.metadata,
                collection_id=kb_id
            )
            
            # 恢复文档
            if backup.ids:
                self.vector_db.add_documents(
                    collection_name=kb_id,
                    documents=backup.documents,
                    embeddings=backup.embeddings,
                    metadatas=backup.metadatas,
                    ids=backup.ids
                )
            
            logger.info(f"Restored knowledge base {kb_id} from backup")
            
            # 清理备份
            self.cleanup_backup(kb_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore knowledge base {kb_id}: {e}")
            return False
    
    def cleanup_backup(self, kb_id: str):
        """清理备份"""
        # 从内存删除
        if kb_id in self.backups:
            del self.backups[kb_id]
        
        # 删除备份文件
        backup_file = self._get_backup_filename(kb_id)
        if os.path.exists(backup_file):
            try:
                os.unlink(backup_file)
            except:
                pass
    
    def _get_backup_filename(self, kb_id: str) -> str:
        """获取备份文件名"""
        import tempfile
        temp_dir = tempfile.gettempdir()
        return os.path.join(temp_dir, f"kb_backup_{kb_id}.json")
    
    def _save_backup_to_file(self, backup: KnowledgeBaseBackup):
        """保存备份到文件"""
        try:
            backup_file = self._get_backup_filename(backup.kb_id)
            
            # 转换为可序列化的格式
            data = {
                "kb_id": backup.kb_id,
                "name": backup.name,
                "description": backup.description,
                "metadata": backup.metadata,
                "documents": backup.documents,
                "embeddings": backup.embeddings,
                "metadatas": backup.metadatas,
                "ids": backup.ids
            }
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save backup to file: {e}")
    
    def _load_backup_from_file(self, kb_id: str) -> Optional[KnowledgeBaseBackup]:
        """从文件加载备份"""
        try:
            backup_file = self._get_backup_filename(kb_id)
            
            if not os.path.exists(backup_file):
                return None
            
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return KnowledgeBaseBackup(**data)
            
        except Exception as e:
            logger.warning(f"Failed to load backup from file: {e}")
            return None
    
    def execute_with_rollback(self, kb_id: str, operation_func, *args, **kwargs):
        """
        执行操作，失败时自动回滚
        
        Args:
            kb_id: 知识库ID
            operation_func: 要执行的操作函数
            *args, **kwargs: 操作函数的参数
            
        Returns:
            操作结果
        """
        # 创建备份
        backup = self.backup_knowledge_base(kb_id)
        if not backup:
            raise Exception("Failed to create backup")
        
        try:
            # 执行操作
            result = operation_func(*args, **kwargs)
            
            # 操作成功，清理备份
            self.cleanup_backup(kb_id)
            
            return result
            
        except Exception as e:
            # 操作失败，恢复备份
            logger.error(f"Operation failed, rolling back: {e}")
            
            if self.restore_knowledge_base(kb_id):
                logger.info("Rollback successful")
            else:
                logger.error("Rollback failed!")
            
            raise
