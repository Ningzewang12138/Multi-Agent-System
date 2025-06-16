# API文档

## 概述

MAS项目提供RESTful API，支持以下功能：
- 聊天对话
- 知识库管理
- RAG查询
- 设备同步

## 基础URL

```
http://localhost:8000
```

## 认证

当前版本暂不需要认证。

## API端点列表

### 系统
- `GET /` - 获取系统状态
- `GET /api/system/info` - 系统信息
- `GET /api/system/embeddings/status` - 嵌入服务状态

### 聊天
- `POST /api/chat/completions` - 发送聊天消息
- `GET /api/chat/models` - 获取可用模型列表
- `POST /api/chat/rag/completions` - RAG增强聊天

### 知识库
- `GET /api/knowledge/` - 列出知识库
- `POST /api/knowledge/` - 创建知识库
- `GET /api/knowledge/{kb_id}` - 获取知识库详情
- `DELETE /api/knowledge/{kb_id}` - 删除知识库
- `POST /api/knowledge/{kb_id}/documents` - 添加文档
- `POST /api/knowledge/{kb_id}/documents/upload` - 上传文件
- `POST /api/knowledge/{kb_id}/search` - 搜索知识库
- `POST /api/knowledge/{kb_id}/publish` - 发布知识库

### 同步
- `GET /api/sync/device/info` - 获取设备信息
- `GET /api/sync/knowledge/synced` - 获取已同步知识库

## 详细文档

每个API端点的详细文档请参考：
- [聊天API](./chat.md)
- [知识库API](./knowledge.md)
- [RAG API](./rag.md)
- [同步API](./sync.md)
