"""
MCP (Model Context Protocol) API 路由
提供MCP工具调用和管理接口
"""
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import json
from datetime import datetime

from server.mcp.manager import mcp_manager
from server.services.mcp_workspace_service import workspace_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== 数据模型 ==========

class MCPToolInfo(BaseModel):
    """MCP工具信息"""
    name: str
    description: str
    category: str
    parameters: List[Dict[str, Any]]

class MCPServiceInfo(BaseModel):
    """MCP服务信息"""
    name: str
    description: str
    tools: List[MCPToolInfo]
    enabled: bool = True

class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    device_id: str = Field(..., description="设备ID")
    session_id: Optional[str] = Field(None, description="会话ID，如不提供则自动生成")

class ToolCallResponse(BaseModel):
    """工具调用响应"""
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    workspace_info: Optional[Dict[str, Any]] = None

class WorkspaceFileInfo(BaseModel):
    """工作空间文件信息"""
    name: str
    size: int
    modified: str
    is_directory: bool

class CreateWorkspaceRequest(BaseModel):
    """创建工作空间请求"""
    device_id: str = Field(..., description="设备ID")
    session_id: Optional[str] = Field(None, description="会话ID")

# ========== 辅助函数 ==========

def get_mcp_manager(request: Request):
    """获取MCP管理器"""
    # 确保管理器已初始化
    if not mcp_manager._initialized:
        mcp_manager.initialize()
    return mcp_manager

# ========== API 端点 ==========

@router.get("/services", response_model=List[MCPServiceInfo])
async def list_mcp_services(
    request: Request,
    manager = Depends(get_mcp_manager)
):
    """获取可用的MCP服务列表"""
    try:
        # 获取所有工具定义
        all_tools = manager.get_available_tools()
        
        # 按类别组织服务
        services_map = {}
        
        # 获取工具注册表中的分类信息
        for category, tool_names in manager.registry._categories.items():
            if category not in services_map:
                services_map[category] = {
                    "name": category,
                    "description": _get_category_description(category),
                    "tools": [],
                    "enabled": True
                }
            
            # 添加该类别下的工具
            for tool_name in tool_names:
                tool = manager.registry.get_tool(tool_name)
                if tool:
                    tool_def = tool.definition
                    tool_info = MCPToolInfo(
                        name=tool_def.name,
                        description=tool_def.description,
                        category=category,
                        parameters=[{
                            "name": param.name,
                            "type": param.type,
                            "description": param.description,
                            "required": param.required,
                            "default": param.default,
                            "enum": param.enum
                        } for param in tool_def.parameters]
                    )
                    services_map[category]["tools"].append(tool_info)
        
        # 转换为列表
        services = [
            MCPServiceInfo(**service_data)
            for service_data in services_map.values()
        ]
        
        logger.info(f"Listed {len(services)} MCP services with {len(all_tools)} tools")
        return services
        
    except Exception as e:
        logger.error(f"Failed to list MCP services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tools", response_model=List[Dict[str, Any]])
async def list_mcp_tools(
    request: Request,
    category: Optional[str] = None,
    manager = Depends(get_mcp_manager)
):
    """获取MCP工具列表（OpenAI函数格式）"""
    try:
        if category:
            # 获取特定类别的工具
            tool_names = manager.get_tools_by_category(category)
            tools = []
            for name in tool_names:
                tool = manager.registry.get_tool(name)
                if tool:
                    tools.append(tool.definition.to_openai_function())
            return tools
        else:
            # 获取所有工具
            return manager.get_available_tools()
        
    except Exception as e:
        logger.error(f"Failed to list MCP tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute", response_model=ToolCallResponse)
async def execute_mcp_tool(
    request: Request,
    tool_request: ToolCallRequest,
    manager = Depends(get_mcp_manager)
):
    """执行MCP工具"""
    try:
        logger.info(f"Executing MCP tool: {tool_request.tool_name} for device: {tool_request.device_id}")
        
        # 创建或获取工作空间
        session_id, workspace_path = workspace_service.create_workspace(
            device_id=tool_request.device_id,
            session_id=tool_request.session_id
        )
        
        # 如果参数中包含workspace相关的路径，替换为实际工作空间路径
        processed_params = _process_workspace_paths(
            tool_request.parameters,
            workspace_path
        )
        
        # 执行工具
        result = await manager.registry.execute_tool(
            name=tool_request.tool_name,
            parameters=processed_params
        )
        
        # 如果工具产生了文件，保存到工作空间
        if result.success and "output_file" in result.metadata:
            output_file = result.metadata["output_file"]
            if isinstance(output_file, dict):
                filename = output_file.get("name", "output.txt")
                content = output_file.get("content", "")
                
                if isinstance(content, str):
                    workspace_service.save_text_to_workspace(
                        session_id=session_id,
                        filename=filename,
                        content=content
                    )
                elif isinstance(content, bytes):
                    workspace_service.save_file_to_workspace(
                        session_id=session_id,
                        filename=filename,
                        content=content
                    )
        
        # 构建响应
        response = ToolCallResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            metadata=result.metadata,
            session_id=session_id,
            workspace_info={
                "session_id": session_id,
                "workspace_path": str(workspace_path),
                "files": workspace_service.list_files_in_workspace(session_id)
            }
        )
        
        logger.info(f"Tool execution {'succeeded' if result.success else 'failed'}: {tool_request.tool_name}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to execute MCP tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workspace/create")
async def create_workspace(
    request: Request,
    workspace_request: CreateWorkspaceRequest
):
    """创建工作空间"""
    try:
        session_id, workspace_path = workspace_service.create_workspace(
            device_id=workspace_request.device_id,
            session_id=workspace_request.session_id
        )
        
        return {
            "session_id": session_id,
            "workspace_path": str(workspace_path),
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workspace/{session_id}/files", response_model=List[WorkspaceFileInfo])
async def list_workspace_files(
    session_id: str,
    request: Request
):
    """列出工作空间中的文件"""
    try:
        files = workspace_service.list_files_in_workspace(session_id)
        
        if not files and not workspace_service.get_workspace(session_id):
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return [WorkspaceFileInfo(**f) for f in files]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list workspace files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workspace/{session_id}/file/{filename}")
async def download_workspace_file(
    session_id: str,
    filename: str,
    request: Request
):
    """下载工作空间中的文件"""
    try:
        content = workspace_service.read_file_from_workspace(session_id, filename)
        
        if content is None:
            raise HTTPException(status_code=404, detail="File not found")
        
        # 尝试解码为文本
        try:
            text_content = content.decode('utf-8')
            return {
                "filename": filename,
                "content": text_content,
                "type": "text"
            }
        except UnicodeDecodeError:
            # 如果不是文本，返回base64编码
            import base64
            return {
                "filename": filename,
                "content": base64.b64encode(content).decode('ascii'),
                "type": "binary"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download workspace file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workspace/{session_id}/upload")
async def upload_to_workspace(
    session_id: str,
    request: Request,
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None)
):
    """上传文件到工作空间"""
    try:
        # 使用提供的文件名或原始文件名
        target_filename = filename or file.filename
        
        # 读取文件内容
        content = await file.read()
        
        # 保存到工作空间
        saved_path = workspace_service.save_file_to_workspace(
            session_id=session_id,
            filename=target_filename,
            content=content
        )
        
        if not saved_path:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return {
            "message": "File uploaded successfully",
            "filename": target_filename,
            "size": len(content),
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file to workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/workspace/{session_id}")
async def delete_workspace(
    session_id: str,
    request: Request
):
    """删除工作空间"""
    try:
        success = workspace_service.delete_workspace(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return {"message": f"Workspace {session_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workspace/list")
async def list_workspaces(
    request: Request,
    device_id: Optional[str] = None
):
    """列出工作空间"""
    try:
        workspaces = workspace_service.list_workspaces(device_id)
        
        return {
            "workspaces": workspaces,
            "total": len(workspaces)
        }
        
    except Exception as e:
        logger.error(f"Failed to list workspaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workspace/cleanup")
async def cleanup_workspaces(
    request: Request,
    max_age_hours: int = 24
):
    """清理旧的工作空间"""
    try:
        cleaned_count = workspace_service.cleanup_old_workspaces(max_age_hours)
        
        return {
            "message": f"Cleaned up {cleaned_count} old workspaces",
            "max_age_hours": max_age_hours
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup workspaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== 辅助函数 ==========

def _get_category_description(category: str) -> str:
    """获取类别描述"""
    descriptions = {
        "filesystem": "文件系统操作工具，包括文件读写、目录管理等",
        "web": "网络相关工具，包括网页获取、API调用等",
        "data": "数据处理工具，包括JSON、CSV处理等",
        "map": "地图服务工具，包括路线规划、地点搜索等",
        "general": "通用工具"
    }
    return descriptions.get(category, f"{category.title()} tools")

def _process_workspace_paths(parameters: Dict[str, Any], workspace_path) -> Dict[str, Any]:
    """处理参数中的工作空间路径"""
    processed = parameters.copy()
    
    # 替换特殊占位符
    for key, value in processed.items():
        if isinstance(value, str):
            # 替换工作空间占位符
            if value.startswith("@workspace/"):
                filename = value[11:]  # 移除 "@workspace/" 前缀
                processed[key] = str(workspace_path / filename)
            elif value == "@workspace":
                processed[key] = str(workspace_path)
    
    return processed
