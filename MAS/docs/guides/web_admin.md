# Web管理界面使用指南

## 概述

MAS项目提供了一个统一的Web管理界面，整合了所有的管理功能，包括知识库管理、文档管理、设备监控、系统信息查看和API测试。

## 访问方式

### 1. 启动服务器

```bash
# 使用快速启动
python quickstart.py
# 选择 4 - 启动服务器

# 或手动启动
cd server
python main.py
```

### 2. 访问Web界面

打开浏览器访问以下地址：

- **主管理界面**: http://localhost:8000/admin/
- **新Web界面**: http://localhost:8000/web/

## 功能模块

### 1. 仪表板 (Dashboard)

- **路径**: `/web/` 或 `/admin/`
- **功能**:
  - 系统状态概览
  - 知识库统计
  - 连接设备数量
  - 最近活动日志
  - 快速操作按钮

### 2. 知识库管理

- **路径**: `/web/knowledge`
- **功能**:
  - 查看所有知识库（公开和草稿）
  - 创建新知识库
  - 删除知识库
  - 按设备筛选
  - 搜索知识库
  - 查看知识库详情

### 3. 文档管理

- **路径**: `/web/knowledge/{kb_id}/documents`
- **功能**:
  - 查看知识库中的所有文档
  - 上传新文档（支持PDF、DOCX、TXT等）
  - 批量删除文档
  - 按时间删除旧文档
  - 搜索文档内容
  - 查看文档统计信息
  - 清空知识库

### 4. 设备管理

- **路径**: `/web/devices`
- **功能**:
  - 查看所有连接的设备
  - 设备在线状态
  - 设备详细信息
  - 广播设备发现
  - Ping测试设备连接

### 5. 系统信息

- **路径**: `/web/system`
- **功能**:
  - 服务器状态
  - 嵌入服务状态
  - 向量数据库状态
  - Ollama服务状态
  - 可用模型列表
  - 系统资源使用情况
  - API端点列表

### 6. API测试控制台

- **路径**: `/web/test`
- **功能**:
  - **聊天测试**: 测试普通聊天功能和流式响应
  - **RAG测试**: 测试基于知识库的增强问答
  - **自定义API测试**: 测试任意API端点

## 使用示例

### 创建和管理知识库

1. 访问 `/web/knowledge`
2. 点击 "Create New" 按钮
3. 输入知识库名称和描述
4. 创建后，点击 "Documents" 管理文档

### 上传文档

1. 进入文档管理页面
2. 点击 "Upload Document"
3. 选择文件并设置元数据
4. 上传完成后可以搜索和管理

### 测试RAG功能

1. 访问 `/web/test`
2. 在RAG测试部分选择知识库
3. 输入问题
4. 查看检索结果和AI回答

## 高级功能

### 批量操作

- **批量删除文档**: 勾选多个文档后点击 "Delete Selected"
- **按时间清理**: 输入天数，删除指定天数前的文档
- **模式匹配删除**: 输入源模式，删除匹配的文档

### 数据导出

虽然界面不直接提供导出功能，但可以通过API获取数据：

```bash
# 导出知识库列表
curl http://localhost:8000/api/knowledge/ > knowledge_bases.json

# 导出文档列表
curl http://localhost:8000/api/knowledge/{kb_id}/documents > documents.json
```

## 旧版界面迁移

### 从旧HTML文件迁移

| 旧文件/功能 | 新界面位置 |
|------------|-----------|
| document_manage.html | `/web/knowledge/{kb_id}/documents` |
| admin.html | `/web/` 或 `/admin/` |
| API测试（手动） | `/web/test` |

### 已移除的文件

以下文件已移动到 `old_web_files/` 目录：
- `server/document_manage.html`
- `server/templates/admin.html`

## 故障排查

### 页面无法访问

1. 确认服务器正在运行
2. 检查端口8000是否被占用
3. 查看服务器日志中的错误信息

### 功能不工作

1. 打开浏览器开发者工具（F12）
2. 查看Console中的错误信息
3. 检查Network标签中的API请求

### 知识库无法创建

1. 确保提供了设备ID和设备名称
2. 检查知识库名称是否重复
3. 查看服务器日志

## 安全建议

1. **生产环境**: 添加身份验证和授权
2. **网络访问**: 使用防火墙限制访问
3. **HTTPS**: 配置SSL证书
4. **备份**: 定期备份知识库数据

## API集成

Web界面使用的所有功能都通过API实现，可以直接调用这些API进行集成：

```python
import requests

# 获取知识库列表
response = requests.get("http://localhost:8000/api/knowledge/")
kbs = response.json()

# 创建知识库
data = {
    "name": "My KB",
    "description": "Test",
    "device_id": "server",
    "device_name": "Server"
}
response = requests.post("http://localhost:8000/api/knowledge/", json=data)
```

## 更新日志

### v2.0 (2025-01-20)
- 整合所有管理功能到统一界面
- 新增API测试控制台
- 改进文档管理功能
- 添加设备管理界面
- 优化用户体验
