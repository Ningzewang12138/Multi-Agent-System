# MCP (Model Context Protocol) 使用指南

## 概述

MCP（Model Context Protocol）是MAS系统中的工具调用框架，允许AI模型通过标准化的接口调用各种工具，实现文件操作、网络请求、数据处理等功能。

## 核心概念

### 1. 工具（Tool）
每个工具都是一个独立的功能单元，具有：
- 名称和描述
- 输入参数定义
- 执行逻辑
- 返回结果格式

### 2. 工作空间（Workspace）
- 每个设备的每次MCP请求都有独立的临时工作空间
- 工具可以在工作空间中读写文件
- 工作空间会自动清理（默认24小时后）

### 3. 工具类别
- `filesystem`：文件系统操作
- `web`：网络请求和网页抓取
- `data`：数据处理和转换
- `maps`：地图服务（需要API密钥）

## API 端点

### 1. 获取可用服务
```http
GET /api/mcp/services
```
返回按类别组织的所有可用MCP服务列表。

### 2. 获取工具列表
```http
GET /api/mcp/tools?category=filesystem
```
返回OpenAI函数格式的工具定义。

### 3. 执行工具
```http
POST /api/mcp/execute
{
  "tool_name": "write_file",
  "parameters": {
    "path": "@workspace/output.txt",
    "content": "Hello World"
  },
  "device_id": "device_001",
  "session_id": "optional_session_id"
}
```

### 4. 工作空间管理
- 创建：`POST /api/mcp/workspace/create`
- 列出文件：`GET /api/mcp/workspace/{session_id}/files`
- 下载文件：`GET /api/mcp/workspace/{session_id}/file/{filename}`
- 上传文件：`POST /api/mcp/workspace/{session_id}/upload`
- 删除：`DELETE /api/mcp/workspace/{session_id}`

## 内置工具列表

### 文件系统工具
1. **read_file** - 读取文件内容
2. **write_file** - 写入文件
3. **list_directory** - 列出目录内容
4. **create_directory** - 创建目录
5. **delete_file** - 删除文件或目录

### 网络工具
1. **http_request** - 发送HTTP请求
2. **web_scrape** - 抓取网页内容

### 数据处理工具
1. **json_process** - JSON数据处理
2. **csv_process** - CSV数据处理
3. **text_analysis** - 文本分析
4. **data_convert** - 数据格式转换

## 使用示例

### 1. 创建并写入文件
```python
import requests

# 执行写文件工具
response = requests.post("http://localhost:8000/api/mcp/execute", json={
    "tool_name": "write_file",
    "parameters": {
        "path": "@workspace/report.txt",
        "content": "这是一份分析报告..."
    },
    "device_id": "my_device"
})

session_id = response.json()["session_id"]
```

### 2. 处理CSV数据
```python
csv_data = """name,score
Alice,95
Bob,87
Charlie,92"""

response = requests.post("http://localhost:8000/api/mcp/execute", json={
    "tool_name": "csv_process",
    "parameters": {
        "data": csv_data,
        "operation": "aggregate",
        "aggregate_column": "score",
        "aggregate_function": "mean"
    },
    "device_id": "my_device"
})
```

### 3. 数据格式转换
```python
response = requests.post("http://localhost:8000/api/mcp/execute", json={
    "tool_name": "data_convert",
    "parameters": {
        "data": json.dumps({"name": "test", "value": 123}),
        "from_format": "json",
        "to_format": "yaml",
        "options": {
            "save_to_workspace": True,
            "filename": "config.yaml"
        }
    },
    "device_id": "my_device"
})
```

## 扩展MCP工具

### 1. 创建新工具类
```python
from server.mcp.base import MCPTool, ToolDefinition, ToolParameter, ToolResult

class MyCustomTool(MCPTool):
    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_custom_tool",
            description="My custom tool description",
            parameters=[
                ToolParameter(
                    name="input_text",
                    type="string",
                    description="Input text to process"
                )
            ],
            returns="string"
        )
    
    async def execute(self, input_text: str) -> ToolResult:
        try:
            # 实现工具逻辑
            result = input_text.upper()
            
            return ToolResult(
                success=True,
                result=result,
                metadata={"length": len(result)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )
```

### 2. 注册工具
```python
def register_my_tools(registry):
    registry.register(MyCustomTool(), category="custom")
```

### 3. 在管理器中添加
编辑 `server/mcp/manager.py`：
```python
from .tools.my_tools import register_my_tools

def initialize(self):
    # ... 现有代码 ...
    register_my_tools(self.registry)
```

## 配置第三方服务

### 1. 设置API密钥
复制 `server/config/api_keys.json.template` 为 `api_keys.json`，填入实际的API密钥：
```json
{
  "amap_api_key": "your_actual_api_key_here"
}
```

### 2. 环境变量方式
```bash
export AMAP_API_KEY=your_api_key_here
```

## 最佳实践

1. **工作空间路径**：使用 `@workspace/` 前缀自动指向工作空间
2. **错误处理**：工具应该返回清晰的错误信息
3. **文件输出**：需要保存的结果使用 `output_file` 元数据
4. **异步执行**：所有工具都应该支持异步执行
5. **参数验证**：在执行前验证所有必需参数

## 安全注意事项

1. **API密钥保护**：永远不要将API密钥提交到版本控制
2. **路径限制**：文件操作应限制在工作空间内
3. **网络请求**：注意限制请求频率和超时设置
4. **数据大小**：对大文件和大数据集设置合理限制

## 故障排除

### 工具执行失败
- 检查参数是否正确
- 查看服务器日志获取详细错误信息
- 确认所需的依赖已安装

### 工作空间问题
- 确保有足够的磁盘空间
- 检查文件权限
- 定期清理旧的工作空间

### API密钥错误
- 确认密钥格式正确
- 检查密钥是否过期
- 验证服务是否可访问

## 未来计划

1. 支持更多第三方服务（OpenAI、百度地图等）
2. 工具链功能（多个工具串联执行）
3. 工具结果缓存机制
4. 更强大的权限控制
5. 工具使用统计和监控
