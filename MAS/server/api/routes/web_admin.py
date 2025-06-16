"""
Web管理界面路由
提供统一的Web管理功能
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

router = APIRouter()

# 设置模板目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # 指向server目录
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 静态文件路径
STATIC_DIR = BASE_DIR / "static"

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """管理面板主页"""
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "title": "Dashboard"}
    )

@router.get("/knowledge", response_class=HTMLResponse)
async def knowledge_management(request: Request):
    """知识库管理页面"""
    return templates.TemplateResponse(
        "admin/knowledge.html",
        {"request": request, "title": "Knowledge Base Management"}
    )

@router.get("/knowledge/{kb_id}/documents", response_class=HTMLResponse)
async def document_management(request: Request, kb_id: str):
    """文档管理页面"""
    return templates.TemplateResponse(
        "admin/documents.html",
        {"request": request, "title": "Document Management", "kb_id": kb_id}
    )

@router.get("/devices", response_class=HTMLResponse)
async def device_management(request: Request):
    """设备管理页面"""
    return templates.TemplateResponse(
        "admin/devices.html",
        {"request": request, "title": "Device Management"}
    )

@router.get("/system", response_class=HTMLResponse)
async def system_info(request: Request):
    """系统信息页面"""
    return templates.TemplateResponse(
        "admin/system.html",
        {"request": request, "title": "System Information"}
    )

@router.get("/test", response_class=HTMLResponse)
async def api_test(request: Request):
    """API测试页面"""
    return templates.TemplateResponse(
        "admin/test.html",
        {"request": request, "title": "API Test Console"}
    )

@router.get("/logs", response_class=HTMLResponse)
async def log_viewer(request: Request):
    """日志查看页面"""
    return templates.TemplateResponse(
        "admin/logs.html",
        {"request": request, "title": "Log Viewer"}
    )

# 静态资源
@router.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    """提供静态文件"""
    file_location = STATIC_DIR / file_path
    if file_location.exists() and file_location.is_file():
        return FileResponse(file_location)
    raise HTTPException(status_code=404, detail="File not found")

# API端点 - 用于AJAX请求
@router.get("/api/stats")
async def get_stats(request: Request):
    """获取系统统计信息"""
    services = request.app.state.services
    
    # 获取知识库统计
    kb_count = 0
    doc_count = 0
    
    try:
        collections = services.vector_db_service.list_collections()
        kb_count = len(collections)
        
        for collection in collections:
            doc_count += collection.get("document_count", 0)
    except:
        pass
    
    # 获取模型信息
    model_count = 0
    try:
        models = services.ollama_service.list_models()
        model_count = len(models)
    except:
        pass
    
    return {
        "knowledge_bases": kb_count,
        "documents": doc_count,
        "models": model_count,
        "embeddings": services.embedding_manager.default_service if services.embedding_manager else "None"
    }

@router.get("/api/recent_activity")
async def get_recent_activity(request: Request):
    """获取最近活动（示例数据）"""
    # 这里可以从日志或数据库中获取真实数据
    return [
        {
            "time": "2025-01-20 10:30:00",
            "action": "Knowledge Base Created",
            "device": "Test Device",
            "status": "Success"
        },
        {
            "time": "2025-01-20 10:25:00",
            "action": "Document Uploaded",
            "device": "Server",
            "status": "Success"
        },
        {
            "time": "2025-01-20 10:20:00",
            "action": "RAG Query",
            "device": "Mobile Client",
            "status": "Success"
        }
    ]
