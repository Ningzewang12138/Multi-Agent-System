# MCP工具调用集成API设计文档

## 概述

本文档定义了将MCP工具调用功能集成到聊天API中的详细设计，包括请求/响应格式、工作流程和示例。

## API端点

### 主端点
- **URL**: `/api/chat/completions`
- **Method**: `POST`
- **描述**: 支持工具调用的聊天完成端点（兼容OpenAI格式）

## 请求格式

### 基础请求结构

```json
{
  "model": "string",                    // 模型名称，可选，默认自动选择
  "messages": [                         // 消息历史
    {
      "role": "user|assistant|system|tool",
      "content": "string",
      "tool_call_id": "string"          // 仅tool角色使用
    }
  ],
  "tools": [                            // 可用工具列表（可选）
    {
      "type": "function",
      "function": {
        "name": "string",
        "description": "string",
        "parameters": {
          "type": "object",
          "properties": {},
          "required": []
        }
      }
    }
  ],
  "tool_choice": "auto|none|required|{specific_tool}",  // 工具选择策略
  "stream": false,                      // 是否流式响应
  "temperature": 0.7,                   // 温度参数
  "max_tokens": null,                   // 最大令牌数
  "session_id": "string"                // 会话ID（可选，用于工作空间管理）
}
```

### 工具定义格式

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "读取文件内容",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "文件路径"
        },
        "encoding": {
          "type": "string",
          "description": "文件编码",
          "enum": ["utf-8", "gbk", "ascii"],
          "default": "utf-8"
        }
      },
      "required": ["path"]
    }
  }
}
```

## 响应格式

### 标准响应（无工具调用）

```json
{
  "id": "chatcmpl-123456",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "llama3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "这是助手的回复内容"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

### 包含工具调用的响应

```json
{
  "id": "chatcmpl-123456",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "llama3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "read_file",
              "arguments": "{\"path\": \"/tmp/data.txt\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 30,
    "total_tokens": 150
  }
}
```

### 工具执行后的最终响应

```json
{
  "id": "chatcmpl-123457",
  "object": "chat.completion",
  "created": 1234567891,
  "model": "llama3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "我已经读取了文件内容。文件包含了用户数据..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 200,
    "completion_tokens": 80,
    "total_tokens": 280
  },
  "tool_execution": {
    "executed": true,
    "tools_called": ["read_file"],
    "session_id": "sess_abc123",
    "workspace_path": "/mcp_workspaces/sess_abc123"
  }
}
```

## 流式响应格式

### 流式响应事件类型

```typescript
// 1. 内容流
data: {"type": "content", "delta": {"content": "这是"}}
data: {"type": "content", "delta": {"content": "流式"}}
data: {"type": "content", "delta": {"content": "响应"}}

// 2. 工具调用流
data: {"type": "tool_call", "delta": {"tool_calls": [{"index": 0, "id": "call_123", "type": "function", "function": {"name": "read_file", "arguments": ""}}]}}
data: {"type": "tool_call", "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\"path\":"}}]}}
data: {"type": "tool_call", "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "\"/tmp/data.txt\"}"}}]}}

// 3. 工具执行结果
data: {"type": "tool_result", "tool_call_id": "call_123", "result": {"success": true, "content": "文件内容..."}}

// 4. 最终完成
data: {"type": "done", "finish_reason": "stop"}
data: [DONE]
```

## 完整的对话流程示例

### 示例1：简单工具调用

**请求**：
```json
{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "请读取/tmp/config.json文件并告诉我其中的版本号"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "读取文件内容",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {"type": "string", "description": "文件路径"}
          },
          "required": ["path"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

**响应1**（工具调用）：
```json
{
  "id": "chatcmpl-001",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "llama3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_001",
            "type": "function",
            "function": {
              "name": "read_file",
              "arguments": "{\"path\": \"/tmp/config.json\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

**客户端处理**：
客户端需要执行工具调用，并将结果作为新消息发送：

```json
{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "请读取/tmp/config.json文件并告诉我其中的版本号"
    },
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_001",
          "type": "function",
          "function": {
            "name": "read_file",
            "arguments": "{\"path\": \"/tmp/config.json\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_001",
      "content": "{\"version\": \"2.3.1\", \"name\": \"MyApp\", \"author\": \"DevTeam\"}"
    }
  ]
}
```

**响应2**（最终回答）：
```json
{
  "id": "chatcmpl-002",
  "object": "chat.completion",
  "created": 1234567891,
  "model": "llama3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "根据读取的config.json文件，版本号是2.3.1。"
      },
      "finish_reason": "stop"
    }
  ]
}
```

### 示例2：多工具调用

**请求**：
```json
{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "获取北京的天气，并保存到weather.txt文件中"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "fetch",
        "description": "获取URL内容",
        "parameters": {
          "type": "object",
          "properties": {
            "url": {"type": "string"}
          },
          "required": ["url"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "write_file",
        "description": "写入文件",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"}
          },
          "required": ["path", "content"]
        }
      }
    }
  ]
}
```

**响应**（多个工具调用）：
```json
{
  "id": "chatcmpl-003",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "llama3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_002",
            "type": "function",
            "function": {
              "name": "fetch",
              "arguments": "{\"url\": \"https://api.weather.com/v1/beijing\"}"
            }
          },
          {
            "id": "call_003",
            "type": "function",
            "function": {
              "name": "write_file",
              "arguments": "{\"path\": \"weather.txt\", \"content\": \"北京天气：晴，温度25°C\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

## 错误处理

### 工具不存在
```json
{
  "error": {
    "message": "Tool 'unknown_tool' not found",
    "type": "invalid_request_error",
    "code": "tool_not_found"
  }
}
```

### 工具执行失败
```json
{
  "error": {
    "message": "Tool execution failed: Permission denied",
    "type": "tool_execution_error",
    "code": "tool_failed",
    "tool_name": "read_file"
  }
}
```

## 服务端实现要点

### 1. 自动工具调用模式

当`tool_choice="auto"`时，服务端应该：
1. 自动检测是否需要调用工具
2. 执行工具调用
3. 将结果注入对话
4. 生成最终响应

### 2. 手动工具调用模式

当客户端需要控制工具执行时：
1. 服务端返回工具调用请求
2. 客户端执行工具（或调用服务端的工具执行API）
3. 客户端将结果作为tool消息发送
4. 服务端基于工具结果生成最终响应

### 3. 工作空间管理

- 每个session_id对应一个独立的工作空间
- 工具执行在对应的工作空间中进行
- 自动清理过期的工作空间

## 客户端集成指南

### JavaScript/TypeScript示例

```typescript
async function chatWithTools(message: string) {
  const response = await fetch('/api/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: 'llama3.2',
      messages: [{ role: 'user', content: message }],
      tools: availableTools,
      tool_choice: 'auto',
      session_id: sessionId
    })
  });

  if (response.headers.get('content-type')?.includes('text/event-stream')) {
    // 处理流式响应
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          handleStreamEvent(data);
        }
      }
    }
  } else {
    // 处理标准响应
    const data = await response.json();
    return data;
  }
}
```

### Python示例

```python
import requests
import json

def chat_with_tools(message, tools=None, session_id=None):
    url = "http://localhost:8000/api/chat/completions"
    
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "user", "content": message}],
        "tools": tools or [],
        "tool_choice": "auto",
        "session_id": session_id
    }
    
    response = requests.post(url, json=payload)
    
    if response.headers.get('content-type') == 'text/event-stream':
        # 处理流式响应
        for line in response.iter_lines():
            if line.startswith(b'data: '):
                data = json.loads(line[6:])
                handle_stream_event(data)
    else:
        # 处理标准响应
        return response.json()
```

## 安全考虑

1. **工具权限控制**
   - 根据用户权限限制可用工具
   - 敏感操作需要额外确认

2. **输入验证**
   - 严格验证工具参数
   - 防止路径遍历等攻击

3. **资源限制**
   - 限制工具执行时间
   - 限制工作空间大小
   - 限制并发工具调用数

4. **审计日志**
   - 记录所有工具调用
   - 包括调用者、时间、参数和结果

## 性能优化

1. **工具缓存**
   - 缓存只读操作的结果
   - 使用ETag验证缓存有效性

2. **并行执行**
   - 独立的工具调用可以并行执行
   - 使用asyncio提高并发性能

3. **流式处理**
   - 大文件操作使用流式处理
   - 避免内存溢出

## 版本兼容性

- API版本：v1
- 向后兼容：支持不带tools的传统请求
- 未来扩展：预留字段用于新功能

## 测试用例

### 基础功能测试
```bash
# 1. 无工具调用
curl -X POST http://localhost:8000/api/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2", "messages": [{"role": "user", "content": "你好"}]}'

# 2. 简单工具调用
curl -X POST http://localhost:8000/api/chat/completions \
  -H "Content-Type: application/json" \
  -d @- << EOF
{
  "model": "llama3.2",
  "messages": [{"role": "user", "content": "读取test.txt文件"}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "read_file",
      "description": "读取文件",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {"type": "string"}
        },
        "required": ["path"]
      }
    }
  }]
}
EOF
```

## 监控指标

1. **请求指标**
   - 总请求数
   - 包含工具调用的请求比例
   - 平均响应时间

2. **工具指标**
   - 各工具调用频率
   - 工具执行成功率
   - 平均执行时间

3. **错误指标**
   - 工具调用失败率
   - 错误类型分布

## 部署清单

- [ ] 更新API文档
- [ ] 添加监控告警
- [ ] 配置日志收集
- [ ] 性能测试
- [ ] 安全审查
- [ ] 客户端SDK更新
