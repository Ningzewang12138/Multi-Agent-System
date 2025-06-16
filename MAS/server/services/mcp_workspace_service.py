"""
MCP 临时操作空间管理服务
为每个设备的每次MCP请求创建独立的工作空间
"""
import os
import shutil
import tempfile
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import asyncio
import uuid

logger = logging.getLogger(__name__)


class MCPWorkspaceService:
    """MCP 工作空间管理服务"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化工作空间服务
        
        Args:
            base_dir: 基础目录，如果不指定则使用系统临时目录
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # 使用项目根目录下的 mcp_workspaces
            current_dir = Path(__file__).parent.parent
            self.base_dir = current_dir / "mcp_workspaces"
        
        # 创建基础目录
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 工作空间映射: session_id -> workspace_path
        self._workspaces: Dict[str, Path] = {}
        
        # 清理任务相关
        self._cleanup_task = None
        self._cleanup_running = False
        
        # 启动清理任务
        self._start_cleanup_task()
        
        logger.info(f"MCP Workspace Service initialized with base dir: {self.base_dir}")
    
    def create_workspace(self, device_id: str, session_id: Optional[str] = None) -> tuple[str, Path]:
        """
        为设备创建临时工作空间
        
        Args:
            device_id: 设备ID
            session_id: 会话ID，如果不提供则自动生成
            
        Returns:
            (session_id, workspace_path)
        """
        # 生成会话ID
        if not session_id:
            session_id = f"{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 创建工作空间目录
        workspace_path = self.base_dir / device_id / session_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 创建元数据文件
        metadata = {
            "device_id": device_id,
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "status": "active"
        }
        
        metadata_file = workspace_path / ".metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 记录工作空间
        self._workspaces[session_id] = workspace_path
        
        logger.info(f"Created workspace for device {device_id}: {workspace_path}")
        return session_id, workspace_path
    
    def get_workspace(self, session_id: str) -> Optional[Path]:
        """获取工作空间路径"""
        workspace = self._workspaces.get(session_id)
        if workspace and workspace.exists():
            # 更新最后访问时间
            self._update_last_accessed(workspace)
            return workspace
        return None
    
    def list_workspaces(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出工作空间
        
        Args:
            device_id: 如果指定，只列出该设备的工作空间
        """
        workspaces = []
        
        # 扫描目录
        if device_id:
            device_dir = self.base_dir / device_id
            if device_dir.exists():
                search_dirs = [device_dir]
            else:
                search_dirs = []
        else:
            search_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        
        for device_dir in search_dirs:
            for session_dir in device_dir.iterdir():
                if session_dir.is_dir():
                    metadata_file = session_dir / ".metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            
                            # 添加文件统计
                            files = list(session_dir.glob("*"))
                            files = [f for f in files if f.name != ".metadata.json"]
                            
                            metadata["file_count"] = len(files)
                            metadata["total_size"] = sum(f.stat().st_size for f in files if f.is_file())
                            metadata["path"] = str(session_dir)
                            
                            workspaces.append(metadata)
                        except Exception as e:
                            logger.error(f"Error reading metadata for {session_dir}: {e}")
        
        return workspaces
    
    def save_file_to_workspace(self, session_id: str, filename: str, content: bytes) -> Optional[Path]:
        """
        保存文件到工作空间
        
        Args:
            session_id: 会话ID
            filename: 文件名
            content: 文件内容
            
        Returns:
            文件路径
        """
        workspace = self.get_workspace(session_id)
        if not workspace:
            logger.error(f"Workspace not found: {session_id}")
            return None
        
        file_path = workspace / filename
        
        # 确保文件名安全
        file_path = workspace / Path(filename).name
        
        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Saved file {filename} to workspace {session_id}")
        return file_path
    
    def save_text_to_workspace(self, session_id: str, filename: str, content: str, encoding: str = 'utf-8') -> Optional[Path]:
        """保存文本文件到工作空间"""
        return self.save_file_to_workspace(session_id, filename, content.encode(encoding))
    
    def read_file_from_workspace(self, session_id: str, filename: str) -> Optional[bytes]:
        """从工作空间读取文件"""
        workspace = self.get_workspace(session_id)
        if not workspace:
            return None
        
        file_path = workspace / filename
        if not file_path.exists():
            return None
        
        with open(file_path, 'rb') as f:
            return f.read()
    
    def list_files_in_workspace(self, session_id: str) -> List[Dict[str, Any]]:
        """列出工作空间中的文件"""
        workspace = self.get_workspace(session_id)
        if not workspace:
            return []
        
        files = []
        for file_path in workspace.iterdir():
            if file_path.name == ".metadata.json":
                continue
            
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_directory": file_path.is_dir()
            })
        
        return files
    
    def delete_workspace(self, session_id: str) -> bool:
        """删除工作空间"""
        workspace = self._workspaces.get(session_id)
        if workspace and workspace.exists():
            try:
                shutil.rmtree(workspace)
                del self._workspaces[session_id]
                logger.info(f"Deleted workspace: {session_id}")
                return True
            except Exception as e:
                logger.error(f"Error deleting workspace {session_id}: {e}")
                return False
        return False
    
    def cleanup_old_workspaces(self, max_age_hours: int = 24):
        """清理超过指定时间的工作空间"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for device_dir in self.base_dir.iterdir():
            if not device_dir.is_dir():
                continue
            
            for session_dir in device_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                
                metadata_file = session_dir / ".metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        last_accessed = datetime.fromisoformat(metadata.get("last_accessed", metadata["created_at"]))
                        
                        if last_accessed < cutoff_time:
                            shutil.rmtree(session_dir)
                            cleaned_count += 1
                            logger.info(f"Cleaned up old workspace: {session_dir}")
                    except Exception as e:
                        logger.error(f"Error processing workspace {session_dir}: {e}")
            
            # 删除空的设备目录
            if not list(device_dir.iterdir()):
                device_dir.rmdir()
        
        logger.info(f"Cleaned up {cleaned_count} old workspaces")
        return cleaned_count
    
    def _update_last_accessed(self, workspace: Path):
        """更新最后访问时间"""
        metadata_file = workspace / ".metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                metadata["last_accessed"] = datetime.now().isoformat()
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error updating last accessed time: {e}")
    
    def _start_cleanup_task(self):
        """启动定期清理任务"""
        async def cleanup_loop():
            self._cleanup_running = True
            logger.info("Cleanup task started")
            while self._cleanup_running:
                try:
                    # 使用较短的间隔以便更快响应关闭信号
                    for _ in range(360):  # 3600秒 = 1小时，每10秒检查一次
                        if not self._cleanup_running:
                            break
                        await asyncio.sleep(10)
                    
                    if self._cleanup_running:  # 再次检查，避免在关闭时执行
                        self.cleanup_old_workspaces()
                except asyncio.CancelledError:
                    logger.info("Cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
            logger.info("Cleanup loop ended")
        
        # 在后台启动清理任务
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(cleanup_loop())
            logger.info("Cleanup task scheduled")
        except RuntimeError:
            # 如果没有事件循环，稍后再启动
            logger.info("Event loop not available, cleanup task will be started later")
            self._cleanup_task = None
    
    async def stop(self):
        """停止服务"""
        self._cleanup_running = False
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping cleanup task: {e}")
        
        logger.info("MCP Workspace Service stopped")


# 全局工作空间服务实例
workspace_service = MCPWorkspaceService()


def start_workspace_service():
    """在事件循环可用后启动工作空间服务"""
    if workspace_service._cleanup_task is None:
        workspace_service._start_cleanup_task()
