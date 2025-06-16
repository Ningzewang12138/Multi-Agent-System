# server/services/knowledge_sync_service.py

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import aiohttp
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()

@dataclass
class SyncMetadata:
    """同步元数据"""
    kb_id: str
    device_id: str
    last_sync: datetime
    document_count: int
    total_size: int
    checksum: str

@dataclass
class SyncConflict:
    """同步冲突"""
    document_id: str
    local_version: dict
    remote_version: dict
    conflict_type: str  # 'modified', 'deleted'
    resolution: Optional[str] = None  # 'keep_local', 'keep_remote', 'merge'

class SyncRecord(Base):
    """同步记录表"""
    __tablename__ = 'sync_records'
    
    id = Column(Integer, primary_key=True)
    sync_id = Column(String(64), unique=True, index=True)
    kb_id = Column(String(64), index=True)
    source_device_id = Column(String(64))
    target_device_id = Column(String(64))
    sync_type = Column(String(20))  # 'push', 'pull', 'bidirectional'
    status = Column(String(20))  # 'pending', 'in_progress', 'completed', 'failed'
    documents_synced = Column(Integer, default=0)
    conflicts_count = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

class DocumentVersion(Base):
    """文档版本表"""
    __tablename__ = 'document_versions'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(String(64), index=True)
    kb_id = Column(String(64), index=True)
    version_hash = Column(String(64))
    content_hash = Column(String(64))
    doc_metadata = Column(Text)  # JSON - 改名避免与SQLAlchemy的metadata冲突
    created_at = Column(DateTime, default=datetime.now)
    device_id = Column(String(64))

class KnowledgeSyncService:
    """知识库同步服务"""
    
    def __init__(self, db_url: str = "sqlite:///sync.db"):
        # 初始化数据库
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # 同步配置
        self.chunk_size = 100  # 每批同步的文档数
        self.conflict_resolution = 'ask'  # 'keep_local', 'keep_remote', 'keep_latest', 'ask'
        
    async def initiate_sync(
        self,
        kb_id: str,
        source_device_id: str,
        target_device_id: str,
        target_url: str,
        sync_type: str = 'bidirectional',
        filter_criteria: Optional[dict] = None
    ) -> str:
        """发起同步"""
        sync_id = self._generate_sync_id(kb_id, source_device_id, target_device_id)
        
        # 创建同步记录
        with self.SessionLocal() as session:
            sync_record = SyncRecord(
                sync_id=sync_id,
                kb_id=kb_id,
                source_device_id=source_device_id,
                target_device_id=target_device_id,
                sync_type=sync_type,
                status='pending'
            )
            session.add(sync_record)
            session.commit()
        
        # 异步执行同步
        asyncio.create_task(self._perform_sync(
            sync_id, kb_id, source_device_id, target_device_id, 
            target_url, sync_type, filter_criteria
        ))
        
        return sync_id
    
    async def _perform_sync(
        self,
        sync_id: str,
        kb_id: str,
        source_device_id: str,
        target_device_id: str,
        target_url: str,
        sync_type: str,
        filter_criteria: Optional[dict]
    ):
        """执行同步"""
        try:
            # 更新状态为进行中
            self._update_sync_status(sync_id, 'in_progress')
            
            # 获取本地文档元数据
            local_metadata = await self._get_local_metadata(kb_id, filter_criteria)
            
            # 获取远程文档元数据
            remote_metadata = await self._get_remote_metadata(
                target_url, kb_id, filter_criteria
            )
            
            # 计算差异
            to_push, to_pull, conflicts = self._calculate_diff(
                local_metadata, remote_metadata, sync_type
            )
            
            # 处理冲突
            if conflicts:
                resolved_conflicts = await self._resolve_conflicts(conflicts)
                # 根据解决方案更新推拉列表
                to_push, to_pull = self._apply_conflict_resolutions(
                    to_push, to_pull, resolved_conflicts
                )
            
            # 执行推送
            if to_push and sync_type in ['push', 'bidirectional']:
                await self._push_documents(target_url, kb_id, to_push)
            
            # 执行拉取
            if to_pull and sync_type in ['pull', 'bidirectional']:
                await self._pull_documents(target_url, kb_id, to_pull)
            
            # 更新同步记录
            total_synced = len(to_push) + len(to_pull)
            self._update_sync_status(
                sync_id, 'completed', 
                documents_synced=total_synced,
                conflicts_count=len(conflicts)
            )
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self._update_sync_status(sync_id, 'failed', error_message=str(e))
    
    async def _get_local_metadata(
        self, 
        kb_id: str, 
        filter_criteria: Optional[dict]
    ) -> Dict[str, dict]:
        """获取本地文档元数据"""
        # TODO: 从向量数据库获取文档元数据
        # 这里需要与 VectorDBService 集成
        from server.services.vector_db_service import VectorDBService
        
        vector_db = VectorDBService()
        documents = {}
        
        try:
            # 获取集合中的所有文档
            # 注意：这是一个简化实现，实际需要更高效的方法
            collection = vector_db._get_collection(kb_id)
            if collection:
                results = collection.get()
                
                for i, doc_id in enumerate(results['ids']):
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    content = results['documents'][i] if results['documents'] else ""
                    
                    # 计算内容哈希
                    content_hash = hashlib.sha256(content.encode()).hexdigest()
                    
                    documents[doc_id] = {
                        'id': doc_id,
                        'content_hash': content_hash,
                        'metadata': metadata,
                        'modified_at': metadata.get('modified_at', metadata.get('added_at', ''))
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get local metadata: {e}")
            
        return documents
    
    async def _get_remote_metadata(
        self, 
        target_url: str, 
        kb_id: str,
        filter_criteria: Optional[dict]
    ) -> Dict[str, dict]:
        """获取远程文档元数据"""
        async with aiohttp.ClientSession() as session:
            url = f"{target_url}/api/knowledge/{kb_id}/sync/metadata"
            
            try:
                async with session.get(url, json=filter_criteria) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['documents']
                    else:
                        raise Exception(f"Failed to get remote metadata: {response.status}")
                        
            except Exception as e:
                logger.error(f"Failed to get remote metadata: {e}")
                raise
    
    def _calculate_diff(
        self,
        local_docs: Dict[str, dict],
        remote_docs: Dict[str, dict],
        sync_type: str
    ) -> Tuple[List[str], List[str], List[SyncConflict]]:
        """计算文档差异"""
        to_push = []
        to_pull = []
        conflicts = []
        
        # 找出需要推送的文档（本地有但远程没有，或本地更新）
        if sync_type in ['push', 'bidirectional']:
            for doc_id, local_doc in local_docs.items():
                if doc_id not in remote_docs:
                    to_push.append(doc_id)
                elif local_doc['content_hash'] != remote_docs[doc_id]['content_hash']:
                    # 检查是否是冲突
                    local_time = datetime.fromisoformat(local_doc['modified_at'])
                    remote_time = datetime.fromisoformat(remote_docs[doc_id]['modified_at'])
                    
                    if abs((local_time - remote_time).total_seconds()) > 60:
                        # 时间差超过1分钟，认为是冲突
                        conflicts.append(SyncConflict(
                            document_id=doc_id,
                            local_version=local_doc,
                            remote_version=remote_docs[doc_id],
                            conflict_type='modified'
                        ))
                    elif local_time > remote_time:
                        to_push.append(doc_id)
        
        # 找出需要拉取的文档（远程有但本地没有，或远程更新）
        if sync_type in ['pull', 'bidirectional']:
            for doc_id, remote_doc in remote_docs.items():
                if doc_id not in local_docs:
                    to_pull.append(doc_id)
                elif remote_doc['content_hash'] != local_docs[doc_id]['content_hash']:
                    # 如果没有在冲突列表中，且远程更新
                    if not any(c.document_id == doc_id for c in conflicts):
                        remote_time = datetime.fromisoformat(remote_doc['modified_at'])
                        local_time = datetime.fromisoformat(local_docs[doc_id]['modified_at'])
                        
                        if remote_time > local_time:
                            to_pull.append(doc_id)
        
        return to_push, to_pull, conflicts
    
    async def _resolve_conflicts(
        self, 
        conflicts: List[SyncConflict]
    ) -> List[SyncConflict]:
        """解决冲突"""
        resolved = []
        
        for conflict in conflicts:
            if self.conflict_resolution == 'keep_latest':
                # 保留最新版本
                local_time = datetime.fromisoformat(
                    conflict.local_version['modified_at']
                )
                remote_time = datetime.fromisoformat(
                    conflict.remote_version['modified_at']
                )
                
                if local_time > remote_time:
                    conflict.resolution = 'keep_local'
                else:
                    conflict.resolution = 'keep_remote'
                    
            elif self.conflict_resolution == 'keep_local':
                conflict.resolution = 'keep_local'
                
            elif self.conflict_resolution == 'keep_remote':
                conflict.resolution = 'keep_remote'
                
            else:  # 'ask'
                # TODO: 实现询问用户的机制
                # 暂时默认保留本地版本
                conflict.resolution = 'keep_local'
            
            resolved.append(conflict)
            
        return resolved
    
    def _apply_conflict_resolutions(
        self,
        to_push: List[str],
        to_pull: List[str],
        resolved_conflicts: List[SyncConflict]
    ) -> Tuple[List[str], List[str]]:
        """应用冲突解决方案"""
        for conflict in resolved_conflicts:
            if conflict.resolution == 'keep_local':
                # 保留本地版本，需要推送
                if conflict.document_id not in to_push:
                    to_push.append(conflict.document_id)
                # 从拉取列表中移除
                if conflict.document_id in to_pull:
                    to_pull.remove(conflict.document_id)
                    
            elif conflict.resolution == 'keep_remote':
                # 保留远程版本，需要拉取
                if conflict.document_id not in to_pull:
                    to_pull.append(conflict.document_id)
                # 从推送列表中移除
                if conflict.document_id in to_push:
                    to_push.remove(conflict.document_id)
        
        return to_push, to_pull
    
    async def _push_documents(
        self,
        target_url: str,
        kb_id: str,
        document_ids: List[str]
    ):
        """推送文档到远程"""
        # TODO: 实现文档推送
        # 需要分批推送以避免请求过大
        from server.services.vector_db_service import VectorDBService
        
        vector_db = VectorDBService()
        
        for i in range(0, len(document_ids), self.chunk_size):
            batch_ids = document_ids[i:i + self.chunk_size]
            
            # 获取文档内容
            documents = []
            for doc_id in batch_ids:
                doc = vector_db.get_document(kb_id, doc_id)
                if doc:
                    documents.append(doc)
            
            # 发送到远程
            async with aiohttp.ClientSession() as session:
                url = f"{target_url}/api/knowledge/{kb_id}/sync/push"
                
                async with session.post(url, json={'documents': documents}) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to push documents: {response.status}")
    
    async def _pull_documents(
        self,
        target_url: str,
        kb_id: str,
        document_ids: List[str]
    ):
        """从远程拉取文档"""
        # TODO: 实现文档拉取
        # 需要分批拉取以避免请求过大
        from server.services.vector_db_service import VectorDBService
        from server.services.embedding_manager import EmbeddingManager
        
        vector_db = VectorDBService()
        embedding_manager = EmbeddingManager()
        
        for i in range(0, len(document_ids), self.chunk_size):
            batch_ids = document_ids[i:i + self.chunk_size]
            
            # 从远程获取文档
            async with aiohttp.ClientSession() as session:
                url = f"{target_url}/api/knowledge/{kb_id}/sync/pull"
                
                async with session.post(url, json={'document_ids': batch_ids}) as response:
                    if response.status == 200:
                        data = await response.json()
                        documents = data['documents']
                        
                        # 生成嵌入并保存
                        texts = [doc['content'] for doc in documents]
                        embeddings = embedding_manager.embed_texts(texts)
                        metadatas = [doc['metadata'] for doc in documents]
                        
                        # 添加到本地数据库
                        vector_db.add_documents(
                            collection_name=kb_id,
                            documents=texts,
                            embeddings=embeddings,
                            metadatas=metadatas,
                            ids=[doc['id'] for doc in documents]
                        )
                    else:
                        raise Exception(f"Failed to pull documents: {response.status}")
    
    def _generate_sync_id(
        self, 
        kb_id: str, 
        source_device_id: str, 
        target_device_id: str
    ) -> str:
        """生成同步ID"""
        timestamp = datetime.now().isoformat()
        data = f"{kb_id}:{source_device_id}:{target_device_id}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _update_sync_status(
        self,
        sync_id: str,
        status: str,
        documents_synced: int = 0,
        conflicts_count: int = 0,
        error_message: Optional[str] = None
    ):
        """更新同步状态"""
        with self.SessionLocal() as session:
            sync_record = session.query(SyncRecord).filter_by(sync_id=sync_id).first()
            if sync_record:
                sync_record.status = status
                sync_record.documents_synced = documents_synced
                sync_record.conflicts_count = conflicts_count
                
                if status == 'completed':
                    sync_record.completed_at = datetime.now()
                    
                if error_message:
                    sync_record.error_message = error_message
                    
                session.commit()
    
    def get_sync_history(
        self, 
        kb_id: Optional[str] = None,
        device_id: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        """获取同步历史"""
        with self.SessionLocal() as session:
            query = session.query(SyncRecord)
            
            if kb_id:
                query = query.filter_by(kb_id=kb_id)
            if device_id:
                query = query.filter(
                    (SyncRecord.source_device_id == device_id) |
                    (SyncRecord.target_device_id == device_id)
                )
            
            records = query.order_by(SyncRecord.started_at.desc()).limit(limit).all()
            
            return [
                {
                    'sync_id': r.sync_id,
                    'kb_id': r.kb_id,
                    'source_device_id': r.source_device_id,
                    'target_device_id': r.target_device_id,
                    'sync_type': r.sync_type,
                    'status': r.status,
                    'documents_synced': r.documents_synced,
                    'conflicts_count': r.conflicts_count,
                    'started_at': r.started_at.isoformat(),
                    'completed_at': r.completed_at.isoformat() if r.completed_at else None,
                    'error_message': r.error_message
                }
                for r in records
            ]

# 全局实例
sync_service = KnowledgeSyncService()
