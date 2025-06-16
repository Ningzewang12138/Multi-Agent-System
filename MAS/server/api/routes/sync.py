# server/api/routes/sync.py

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import socket
import json
import asyncio

from server.services.device_discovery_service import discovery_service
from server.services.knowledge_sync_service import sync_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== 数据模型 ==========

class DeviceResponse(BaseModel):
    id: str
    name: str
    type: str
    platform: str
    ip_address: str
    port: int
    version: str
    capabilities: List[str]
    last_seen: str
    status: str

class SyncRequest(BaseModel):
    kb_id: str = Field(..., description="Knowledge base ID")
    target_device_id: str = Field(..., description="Target device ID")
    sync_type: str = Field(default="bidirectional", description="Sync type: push, pull, bidirectional")
    filter_criteria: Optional[Dict[str, Any]] = Field(None, description="Filter for selective sync")

class SyncMetadataRequest(BaseModel):
    filter_criteria: Optional[Dict[str, Any]] = None

class SyncPushRequest(BaseModel):
    documents: List[Dict[str, Any]]

class SyncPullRequest(BaseModel):
    document_ids: List[str]

class SyncStatusResponse(BaseModel):
    sync_id: str
    status: str
    documents_synced: int
    conflicts_count: int
    started_at: str
    completed_at: Optional[str]
    error_message: Optional[str]

# ========== 设备发现端点 ==========

@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices(
    status: Optional[str] = None
):
    """列出发现的设备"""
    try:
        if status == "online":
            devices = discovery_service.get_online_devices()
        else:
            devices = discovery_service.get_all_devices()
        
        return [
            DeviceResponse(
                id=device.id,
                name=device.name,
                type=device.type,
                platform=device.platform,
                ip_address=device.ip_address,
                port=device.port,
                version=device.version,
                capabilities=device.capabilities,
                last_seen=device.last_seen.isoformat(),
                status=device.status
            )
            for device in devices
        ]
        
    except Exception as e:
        logger.error(f"Failed to list devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str):
    """获取特定设备信息"""
    device = discovery_service.get_device_by_id(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return DeviceResponse(
        id=device.id,
        name=device.name,
        type=device.type,
        platform=device.platform,
        ip_address=device.ip_address,
        port=device.port,
        version=device.version,
        capabilities=device.capabilities,
        last_seen=device.last_seen.isoformat(),
        status=device.status
    )

@router.post("/devices/scan")
async def scan_devices():
    """手动触发设备扫描"""
    try:
        # 手动发送一次广播
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # 更新设备信息
        discovery_service.device_info.last_seen = datetime.now()
        
        # 创建广播消息
        message = {
            'type': 'device_announcement',
            'device': discovery_service.device_info.to_dict()
        }
        
        # 发送广播
        data = json.dumps(message).encode('utf-8')
        sock.sendto(data, ('<broadcast>', discovery_service.discovery_port))
        sock.close()
        
        logger.info("Manual broadcast sent")
        
        # 等待一小段时间让其他设备响应
        await asyncio.sleep(1)
        
        return {
            "message": "Device scan initiated",
            "device_count": len(discovery_service.get_all_devices()),
            "online_devices": len(discovery_service.get_online_devices())
        }
        
    except Exception as e:
        logger.error(f"Failed to scan devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/device/register")
async def register_device(request: Request):
    """注册设备（HTTP方式）"""
    try:
        data = await request.json()
        device_data = data.get('device', {})
        
        # 获取客户端的真实IP
        client_ip = request.client.host
        if 'x-forwarded-for' in request.headers:
            client_ip = request.headers['x-forwarded-for'].split(',')[0].strip()
        elif 'x-real-ip' in request.headers:
            client_ip = request.headers['x-real-ip']
        
        # 更新IP地址
        device_data['ip_address'] = client_ip
        
        # 处理设备注册
        discovery_service._handle_device_announcement(device_data, client_ip)
        
        return {
            "message": "Device registered successfully",
            "device_id": device_data.get('id'),
            "registered_ip": client_ip
        }
        
    except Exception as e:
        logger.error(f"Failed to register device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/device/info")
async def get_current_device_info():
    """获取当前设备信息"""
    device = discovery_service.device_info
    
    return DeviceResponse(
        id=device.id,
        name=device.name,
        type=device.type,
        platform=device.platform,
        ip_address=device.ip_address,
        port=device.port,
        version=device.version,
        capabilities=device.capabilities,
        last_seen=device.last_seen.isoformat(),
        status="online"
    )

# ========== 同步端点 ==========

@router.post("/sync/initiate")
async def initiate_sync(
    request: Request,
    sync_request: SyncRequest
):
    """发起同步"""
    try:
        # 获取源设备ID
        source_device_id = discovery_service.device_id
        
        # 获取目标设备信息
        target_device = discovery_service.get_device_by_id(sync_request.target_device_id)
        if not target_device:
            raise HTTPException(status_code=404, detail="Target device not found")
        
        if target_device.status != "online":
            raise HTTPException(status_code=400, detail="Target device is offline")
        
        # 构建目标URL
        target_url = f"http://{target_device.ip_address}:{target_device.port}"
        
        # 发起同步
        sync_id = await sync_service.initiate_sync(
            kb_id=sync_request.kb_id,
            source_device_id=source_device_id,
            target_device_id=sync_request.target_device_id,
            target_url=target_url,
            sync_type=sync_request.sync_type,
            filter_criteria=sync_request.filter_criteria
        )
        
        return {
            "sync_id": sync_id,
            "message": "Sync initiated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sync/status/{sync_id}", response_model=SyncStatusResponse)
async def get_sync_status(sync_id: str):
    """获取同步状态"""
    history = sync_service.get_sync_history(limit=1)
    
    for record in history:
        if record['sync_id'] == sync_id:
            return SyncStatusResponse(
                sync_id=record['sync_id'],
                status=record['status'],
                documents_synced=record['documents_synced'],
                conflicts_count=record['conflicts_count'],
                started_at=record['started_at'],
                completed_at=record['completed_at'],
                error_message=record['error_message']
            )
    
    raise HTTPException(status_code=404, detail="Sync record not found")

@router.get("/sync/history")
async def get_sync_history(
    kb_id: Optional[str] = None,
    device_id: Optional[str] = None,
    limit: int = 50
):
    """获取同步历史"""
    try:
        history = sync_service.get_sync_history(
            kb_id=kb_id,
            device_id=device_id,
            limit=limit
        )
        
        # 补充设备名称信息
        for record in history:
            source_device = discovery_service.get_device_by_id(record['source_device_id'])
            target_device = discovery_service.get_device_by_id(record['target_device_id'])
            
            record['source_device_name'] = source_device.name if source_device else "Unknown"
            record['target_device_name'] = target_device.name if target_device else "Unknown"
        
        return history
        
    except Exception as e:
        logger.error(f"Failed to get sync history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== 同步数据交换端点 ==========

@router.get("/knowledge/{kb_id}/sync/metadata")
async def get_sync_metadata(
    kb_id: str,
    request: Request,
    metadata_request: SyncMetadataRequest
):
    """获取知识库同步元数据"""
    try:
        documents = await sync_service._get_local_metadata(
            kb_id, 
            metadata_request.filter_criteria
        )
        
        return {
            "kb_id": kb_id,
            "document_count": len(documents),
            "documents": documents
        }
        
    except Exception as e:
        logger.error(f"Failed to get sync metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/{kb_id}/sync/push")
async def receive_pushed_documents(
    kb_id: str,
    request: Request,
    push_request: SyncPushRequest
):
    """接收推送的文档"""
    try:
        from server.services.vector_db_service import VectorDBService
        from server.services.embedding_manager import EmbeddingManager
        
        services = request.app.state.services
        vector_db = services.vector_db_service
        embedding_manager = services.embedding_manager
        
        # 处理接收到的文档
        for doc in push_request.documents:
            # 生成嵌入
            embedding = embedding_manager.embed_text(doc['content'])
            
            # 添加或更新文档
            vector_db.add_documents(
                collection_name=kb_id,
                documents=[doc['content']],
                embeddings=[embedding],
                metadatas=[doc['metadata']],
                ids=[doc['id']]
            )
        
        return {
            "message": "Documents received successfully",
            "document_count": len(push_request.documents)
        }
        
    except Exception as e:
        logger.error(f"Failed to receive pushed documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/{kb_id}/sync/pull")
async def send_pulled_documents(
    kb_id: str,
    request: Request,
    pull_request: SyncPullRequest
):
    """发送被拉取的文档"""
    try:
        services = request.app.state.services
        vector_db = services.vector_db_service
        
        documents = []
        for doc_id in pull_request.document_ids:
            doc = vector_db.get_document(kb_id, doc_id)
            if doc:
                documents.append({
                    'id': doc['id'],
                    'content': doc['document'],
                    'metadata': doc['metadata']
                })
        
        return {
            "documents": documents,
            "document_count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Failed to send pulled documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== 同步设置端点 ==========

@router.get("/sync/settings")
async def get_sync_settings():
    """获取同步设置"""
    return {
        "conflict_resolution": sync_service.conflict_resolution,
        "chunk_size": sync_service.chunk_size,
        "auto_sync_enabled": False,  # TODO: 实现自动同步
        "sync_interval": 300  # 秒
    }

@router.put("/sync/settings")
async def update_sync_settings(
    conflict_resolution: Optional[str] = None,
    chunk_size: Optional[int] = None
):
    """更新同步设置"""
    if conflict_resolution:
        if conflict_resolution not in ['keep_local', 'keep_remote', 'keep_latest', 'ask']:
            raise HTTPException(status_code=400, detail="Invalid conflict resolution mode")
        sync_service.conflict_resolution = conflict_resolution
    
    if chunk_size:
        if chunk_size < 1 or chunk_size > 1000:
            raise HTTPException(status_code=400, detail="Chunk size must be between 1 and 1000")
        sync_service.chunk_size = chunk_size
    
    return {"message": "Settings updated successfully"}

# ========== 简化的知识库同步端点 ==========

@router.get("/knowledge/synced")
async def list_synced_knowledge_bases(
    request: Request
):
    """列出所有已同步的知识库"""
    try:
        services = request.app.state.services
        
        if not services.vector_db_service:
            logger.error("Vector DB service not available")
            return []
        
        collections = services.vector_db_service.list_collections()
        
        synced_kbs = []
        for collection in collections:
            try:
                collection_obj = services.vector_db_service.client.get_collection(name=collection["id"])
                metadata = collection_obj.metadata or {}
                
                if metadata.get("is_synced", False):
                    synced_kbs.append({
                        "id": collection["id"],
                        "name": metadata.get("original_kb_name", collection["name"]),
                        "description": collection.get("description", ""),
                        "document_count": collection.get("document_count", 0),
                        "device_id": metadata.get("device_id"),
                        "device_name": metadata.get("device_name"),
                        "original_kb_id": metadata.get("original_kb_id"),
                        "synced_at": metadata.get("synced_at")
                    })
            except Exception as e:
                logger.warning(f"Error processing collection {collection['id']}: {e}")
                continue
        
        logger.info(f"Found {len(synced_kbs)} synced knowledge bases")
        return synced_kbs
        
    except Exception as e:
        logger.error(f"Failed to list synced knowledge bases: {e}")
        raise HTTPException(status_code=500, detail=str(e))
