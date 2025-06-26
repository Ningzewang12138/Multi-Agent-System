from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import sys
from typing import Optional

router = APIRouter()

# 直接使用绝对路径
template_dir = r"D:\Codespace\Python_Codespace\AIagent-dev\MAS\templates"

# 如果不存在，尝试相对路径
if not os.path.exists(template_dir):
    # 获取项目根目录
    current_file = os.path.abspath(__file__)
    # server/api/routes/admin.py -> MAS
    for _ in range(3):
        current_file = os.path.dirname(current_file)
    template_dir = os.path.join(current_file, "templates")

print(f"Template directory: {template_dir}")
print(f"Template directory exists: {os.path.exists(template_dir)}")

if not os.path.exists(template_dir):
    os.makedirs(template_dir, exist_ok=True)
    admin_dir = os.path.join(template_dir, "admin")
    os.makedirs(admin_dir, exist_ok=True)
    print(f"Created template directory: {template_dir}")

templates = Jinja2Templates(directory=template_dir)

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """管理后台首页"""
    try:
        # 尝试使用模板引擎
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "title": "Dashboard"
        })
    except Exception as e:
        print(f"Failed to load template: {e}")
        # 如果模板加载失败，直接读取文件
        admin_html_path = os.path.join(template_dir, "admin.html")
        if os.path.exists(admin_html_path):
            with open(admin_html_path, 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())
        else:
            # 返回简单的HTML
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Admin Dashboard</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    a { margin-right: 20px; }
                </style>
            </head>
            <body>
                <h1>Multi-Agent System Admin</h1>
                <nav>
                    <a href="/admin/">Dashboard</a>
                    <a href="/admin/knowledge">Knowledge Bases</a>
                    <a href="/admin/devices">Devices</a>
                    <a href="/admin/system">System</a>
                </nav>
                <p>Debug: <a href="/admin/debug">View Debug Info</a></p>
            </body>
            </html>
            """)

@router.get("/knowledge", response_class=HTMLResponse)
async def knowledge_management(request: Request):
    """知识库管理页面"""
    return templates.TemplateResponse("admin/knowledge.html", {
        "request": request,
        "title": "Knowledge Base Management"
    })

@router.get("/system", response_class=HTMLResponse)
async def system_status(request: Request):
    """系统状态页面"""
    services = request.app.state.services
    
    status = {
        "ollama": services.ollama_service is not None,
        "vector_db": services.vector_db_service is not None,
        "embedding": services.embedding_manager is not None,
        "document_processor": services.document_processor is not None,
    }
    
    return templates.TemplateResponse("admin/system.html", {
        "request": request,
        "title": "System Status",
        "status": status
    })

@router.get("/devices", response_class=HTMLResponse)
async def device_management(request: Request):
    """设备管理页面"""
    return templates.TemplateResponse("admin/devices.html", {
        "request": request,
        "title": "Device Management"
    })

@router.get("/debug")
async def debug_info(request: Request):
    """调试信息"""
    import os
    template_files = []
    if os.path.exists(template_dir):
        for root, dirs, files in os.walk(template_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), template_dir)
                template_files.append(rel_path.replace('\\', '/'))
    
    return {
        "template_dir": template_dir,
        "exists": os.path.exists(template_dir),
        "files": template_files,
        "current_file": __file__,
        "working_dir": os.getcwd()
    }

@router.get("/knowledge/{kb_id}/documents", response_class=HTMLResponse)
async def document_management(request: Request, kb_id: str):
    """文档管理页面"""
    # 使用模板渲染
    return templates.TemplateResponse("admin/documents.html", {
        "request": request,
        "title": "Document Management",
        "kb_id": kb_id
    })

@router.get("/knowledge/{kb_id}/documents_old", response_class=HTMLResponse)
async def document_management_old(request: Request, kb_id: str):
    """旧版文档管理页面（备用）"""
    # 返回简单的文档管理页面
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Document Management - {kb_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            .btn {{ padding: 5px 10px; margin: 2px; cursor: pointer; }}
            .btn-danger {{ color: red; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Document Management</h1>
            <p>Knowledge Base ID: {kb_id}</p>
            <a href="/admin/">← Back to Dashboard</a>
            
            <div id="documents" style="margin-top: 20px;">
                <p>Loading documents...</p>
            </div>
        </div>
        
        <script>
            const kbId = '{kb_id}';
            
            async function loadDocuments() {{
                try {{
                    const response = await fetch(`/api/knowledge/${{kbId}}/documents`);
                    const data = await response.json();
                    
                    const container = document.getElementById('documents');
                    if (data.documents && data.documents.length > 0) {{
                        let html = '<table><tr><th>ID</th><th>Content Preview</th><th>Created</th><th>Actions</th></tr>';
                        
                        data.documents.forEach(doc => {{
                            html += `
                                <tr>
                                    <td>${{doc.id}}</td>
                                    <td>${{doc.content_preview || 'No preview'}}</td>
                                    <td>${{doc.created_at || 'Unknown'}}</td>
                                    <td>
                                        <button class="btn btn-danger" onclick="deleteDocument('${{doc.id}}')">Delete</button>
                                    </td>
                                </tr>
                            `;
                        }});
                        
                        html += '</table>';
                        container.innerHTML = html;
                    }} else {{
                        container.innerHTML = '<p>No documents found.</p>';
                    }}
                }} catch (error) {{
                    document.getElementById('documents').innerHTML = '<p style="color: red;">Error loading documents: ' + error.message + '</p>';
                }}
            }}
            
            async function deleteDocument(docId) {{
                if (!confirm('Are you sure you want to delete this document?')) return;
                
                try {{
                    const response = await fetch(`/api/knowledge/${{kbId}}/documents/${{docId}}`, {{
                        method: 'DELETE'
                    }});
                    
                    if (response.ok) {{
                        alert('Document deleted successfully');
                        loadDocuments();
                    }} else {{
                        throw new Error('Failed to delete document');
                    }}
                }} catch (error) {{
                    alert('Error: ' + error.message);
                }}
            }}
            
            // Load documents on page load
            loadDocuments();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
