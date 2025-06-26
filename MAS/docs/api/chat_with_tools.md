# 聊天API工具调用使用指南

## 概述

MAS项目的聊天API (`/api/chat/completions`) 现已完全支持MCP工具调用，提供三种不同的工具调用模式：

1. **自动工具检测模式** - 自动从自然语言中检测并执行工具
2. **标准OpenAI模式** - 使用OpenAI格式的显式工具定义
3. **隐式智能模式** - 根据消息内容智能判断是否需要工具

## API端点

```
POST /api/chat/completions
```

## 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| model | string | 否 | 模型名称，默认自动选择 |
| messages | array | 是 | 对话消息列表 |
| stream | boolean | 否 | 是否流式响应，默认false |
| temperature | float | 否 | 温度参数，默认0.7 |
| max_tokens | integer | 否 | 最大生成令牌数 |
| tools | array | 否 | 可用工具列表（OpenAI格式） |
| tool_choice | string | 否 | 工具选择策略：auto/none/required |
| session_id | string | 否 | 会话ID，用于工作空间管理 |
| use_mcp | boolean | 否 | 启用MCP工具（将弃用，建议使用auto_tools） |
| auto_tools | boolean | 否 | 启用自动工具检测 |

## 使用模式

### 1. 自动工具检测模式

最简单的使用方式，系统自动从用户消息中检测需要的工具并执行。

```json
{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "创建一个test.txt文件，内容是'Hello World'"
    }
  ],
  "auto_tools": true
}
```

响应示例：
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "llama3.2",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "我已经成功创建了test.txt文件，内容为'Hello World'。文件已保存在您的工作空间中。"
    },
    "finish_reason": "stop"
  }],
  "tool_execution": {
    "executed": true,
    "tools_called": ["write_file"],
    "session_id": "chat_abc123",
    "Codespace_path": "/mcp_Codespaces/default/chat_abc123"
  }
}
```

### 2. 标准OpenAI工具调用模式

使用OpenAI格式显式定义工具，适合需要精确控制的场景。

```json
{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "获取当前目录的文件列表"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "list_directory",
        "description": "列出目录中的文件和子目录",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string",
              "description": "目录路径"
            }
          },
          "required": ["path"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

### 3. 隐式智能模式

不需要任何额外参数，系统自动判断是否需要工具。

```json
{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "读取config.json文件的内容"
    }
  ]
}
```

系统会自动检测到需要使用`read_file`工具并执行。

## 获取可用工具

### 获取所有工具
```bash
GET /api/mcp/tools
```

### 获取特定类别的工具
```bash
GET /api/mcp/tools?category=filesystem
```

### 获取工具服务列表
```bash
GET /api/mcp/services
```

## 支持的工具

### 文件系统工具
- `read_file` - 读取文件内容
- `write_file` - 写入文件
- `list_directory` - 列出目录内容
- `create_directory` - 创建目录
- `delete_file` - 删除文件

### 天气工具
- `get_current_weather` - 获取当前天气
- `get_weather_forecast` - 获取天气预报

### 数据处理工具
- `parse_json` - 解析JSON字符串
- `format_json` - 格式化JSON数据

### 地图工具（高德地图）
- `amap_geocode` - 地理编码
- `amap_route_planning` - 路线规划
- `amap_poi_search` - 兴趣点搜索

## 工作空间管理

每个会话都有独立的工作空间，用于存储工具产生的文件。

### 列出工作空间文件
```bash
GET /api/mcp/Codespace/{session_id}/files
```

### 下载工作空间文件
```bash
GET /api/mcp/Codespace/{session_id}/file/{filename}
```

### 上传文件到工作空间
```bash
POST /api/mcp/Codespace/{session_id}/upload
```

## 完整示例

### Python客户端示例

```python
import requests
import json

# 服务器地址
BASE_URL = "http://localhost:8000"

# 1. 自动工具检测示例
def auto_tools_example():
    response = requests.post(
        f"{BASE_URL}/api/chat/completions",
        json={
            "model": "llama3.2",
            "messages": [
                {"role": "user", "content": "创建一个hello.py文件，内容是print('Hello, World!')"}
            ],
            "auto_tools": True
        }
    )
    
    result = response.json()
    print(f"助手回复: {result['choices'][0]['message']['content']}")
    if 'tool_execution' in result:
        print(f"执行的工具: {result['tool_execution']['tools_called']}")
        print(f"工作空间: {result['tool_execution']['workspace_path']}")

# 2. 多轮对话示例
def multi_turn_example():
    session_id = None
    messages = []
    
    # 第一轮：创建文件
    messages.append({"role": "user", "content": "创建一个data.json文件，内容是{\"name\": \"Alice\", \"age\": 25}"})
    
    response = requests.post(
        f"{BASE_URL}/api/chat/completions",
        json={
            "messages": messages,
            "auto_tools": True,
            "session_id": session_id
        }
    )
    
    result = response.json()
    session_id = result.get('session_id', session_id)
    messages.append({"role": "assistant", "content": result['choices'][0]['message']['content']})
    
    # 第二轮：读取文件
    messages.append({"role": "user", "content": "读取data.json文件看看内容"})
    
    response = requests.post(
        f"{BASE_URL}/api/chat/completions",
        json={
            "messages": messages,
            "auto_tools": True,
            "session_id": session_id
        }
    )
    
    result = response.json()
    print(f"助手回复: {result['choices'][0]['message']['content']}")

# 3. 流式响应示例
def stream_example():
    response = requests.post(
        f"{BASE_URL}/api/chat/completions",
        json={
            "messages": [
                {"role": "user", "content": "列出当前目录的所有文件"}
            ],
            "auto_tools": True,
            "stream": True
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data != '[DONE]':
                    event = json.loads(data)
                    if event.get('type') == 'content':
                        print(event['delta']['content'], end='', flush=True)
                    elif event.get('type') == 'tool_call':
                        print(f"\n[调用工具: {event['tool_call']['function']['name']}]")
    print()

if __name__ == "__main__":
    # 运行示例
    print("=== 自动工具检测示例 ===")
    auto_tools_example()
    
    print("\n=== 多轮对话示例 ===")
    multi_turn_example()
    
    print("\n=== 流式响应示例 ===")
    stream_example()
```

### JavaScript/TypeScript示例

```javascript
// 使用fetch API
async function chatWithTools(message) {
  const response = await fetch('http://localhost:8000/api/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'llama3.2',
      messages: [
        { role: 'user', content: message }
      ],
      auto_tools: true
    })
  });

  const result = await response.json();
  console.log('助手回复:', result.choices[0].message.content);
  
  if (result.tool_execution) {
    console.log('执行的工具:', result.tool_execution.tools_called);
  }
}

// 流式响应
async function streamChatWithTools(message) {
  const response = await fetch('http://localhost:8000/api/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'llama3.2',
      messages: [
        { role: 'user', content: message }
      ],
      auto_tools: true,
      stream: true
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') continue;

        try {
          const event = JSON.parse(data);
          if (event.type === 'content') {
            process.stdout.write(event.delta.content);
          } else if (event.type === 'tool_call') {
            console.log(`\n[调用工具: ${event.tool_call.function.name}]`);
          }
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
  }
}
```

## 最佳实践

1. **使用session_id** - 在多轮对话中保持相同的session_id，以便在同一工作空间中操作文件。

2. **错误处理** - 始终检查响应中的错误信息，特别是工具执行可能失败的情况。

3. **工具选择** - 使用`auto_tools=true`让系统自动选择工具，或使用`tools`参数精确控制可用工具。

4. **流式响应** - 对于可能需要较长时间的操作，使用流式响应提供更好的用户体验。

5. **工作空间清理** - 定期清理不再需要的工作空间，避免占用过多磁盘空间。

## 故障排查

### 工具未执行
- 检查是否启用了`auto_tools`或提供了`tools`参数
- 确认消息内容包含工具相关的关键词
- 查看服务器日志了解详细信息

### 文件找不到
- 确认使用了正确的session_id
- 检查文件路径是否正确（相对于工作空间根目录）
- 使用工作空间API查看文件列表

### 性能问题
- 工具执行会增加响应时间，这是正常的
- 考虑使用流式响应改善用户体验
- 对于复杂操作，可以分步执行

## 更新日志

### v2.0 (2025-01-20)
- 添加`auto_tools`参数支持自动工具检测
- 改进隐式工具调用的智能判断
- 优化工具执行的错误处理
- 支持更多工具类型（高德地图等）
