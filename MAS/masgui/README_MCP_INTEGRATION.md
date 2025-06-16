# Flutter MCP工具调用集成指南

## 概述

本指南展示了如何在Flutter应用中集成MCP（Model Context Protocol）工具调用功能，使用户能够通过自然语言与AI助手交互，执行文件操作等任务。

## 文件结构

```
masgui/lib/
├── services/
│   └── tool_enhanced_chat_service.dart    # 工具增强的聊天服务
├── models/
│   ├── chat_models.dart                   # 聊天相关数据模型
│   └── tool_models.dart                   # MCP工具相关数据模型
├── screens/
│   └── tool_enhanced_chat_screen.dart     # 聊天界面
└── mcp_demo_app.dart                      # 演示应用入口
```

## 快速开始

### 1. 添加依赖

在 `pubspec.yaml` 中添加必要的依赖：

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
```

### 2. 运行演示应用

```bash
cd masgui
flutter run lib/mcp_demo_app.dart
```

### 3. 集成到现有应用

#### 基础用法

```dart
import 'package:your_app/services/tool_enhanced_chat_service.dart';
import 'package:your_app/models/chat_models.dart';

// 创建服务实例
final chatService = ToolEnhancedChatService(
  baseUrl: 'http://localhost:8000',
);

// 发送消息（非流式）
final response = await chatService.sendMessage(
  message: 'Create a file named notes.txt with content "Hello World"',
  useTools: true,
);

// 检查工具执行
if (response.toolExecution != null) {
  print('Tools executed: ${response.toolExecution!.toolsCalled}');
}

// 获取响应内容
final content = response.choices.first.message.content;
print('Response: $content');
```

#### 流式响应

```dart
// 发送消息（流式）
await for (final event in chatService.sendMessageStream(
  message: 'List all files in the current directory',
  useTools: true,
)) {
  if (event is ContentEvent) {
    // 处理内容片段
    print(event.content);
  } else if (event is ToolExecutionEvent) {
    // 处理工具执行
    print('Tools: ${event.toolsCalled}');
  }
}
```

## 主要功能

### 1. ToolEnhancedChatService

核心服务类，提供以下功能：

- **getAvailableTools()**: 获取可用的MCP工具列表
- **sendMessage()**: 发送聊天消息（支持工具调用）
- **sendMessageStream()**: 流式发送消息
- **getWorkspaceFiles()**: 获取工作空间文件列表
- **downloadWorkspaceFile()**: 下载工作空间文件
- **resetSession()**: 重置会话

### 2. 支持的自然语言命令

- 创建文件：`"Create a file named X with content Y"`
- 列出文件：`"List all files"`, `"Show files in directory"`
- 读取文件：`"Read file X"`, `"Show me the content of X"`
- 删除文件：`"Delete file X"`, `"Remove X"`

### 3. 会话管理

- 每个会话有独立的工作空间
- 会话ID自动管理
- 支持会话重置

## 界面组件

### ToolEnhancedChatScreen

完整的聊天界面组件，包含：

- 消息列表显示
- 工具执行状态提示
- 工作空间文件列表
- 示例命令帮助
- 工具开关控制

使用示例：

```dart
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (context) => ToolEnhancedChatScreen(
      serverUrl: 'http://localhost:8000',
    ),
  ),
);
```

## 自定义集成

### 1. 自定义工具处理

```dart
class CustomChatService extends ToolEnhancedChatService {
  @override
  Future<List<Tool>> getAvailableTools() async {
    final tools = await super.getAvailableTools();
    // 过滤或添加自定义工具
    return tools.where((tool) => 
      ['write_file', 'read_file'].contains(tool.name)
    ).toList();
  }
}
```

### 2. 自定义UI

```dart
// 监听工具执行事件
chatService.sendMessageStream(...).listen((event) {
  if (event is ToolExecutionEvent) {
    // 显示自定义UI
    showCustomToolNotification(event.toolsCalled);
  }
});
```

### 3. 错误处理

```dart
try {
  final response = await chatService.sendMessage(...);
} catch (e) {
  if (e.toString().contains('No active session')) {
    // 处理会话错误
    chatService.resetSession();
  }
}
```

## 最佳实践

1. **会话管理**
   - 在应用启动时创建服务实例
   - 合理使用resetSession()清理会话

2. **性能优化**
   - 对长对话使用流式响应
   - 缓存工具列表，避免频繁请求

3. **用户体验**
   - 提供命令示例和帮助
   - 显示工具执行状态
   - 展示工作空间文件列表

4. **错误处理**
   - 捕获网络错误
   - 提供友好的错误提示
   - 支持重试机制

## 调试技巧

1. **查看服务器日志**
   ```bash
   # 服务器端会输出详细的工具调用日志
   grep -i "tool\|intent" server.log
   ```

2. **测试工具调用**
   ```dart
   // 强制使用工具
   final response = await chatService.sendMessage(
     message: 'Create test.txt with content "test"',
     useTools: true,  // 确保启用工具
   );
   ```

3. **检查会话状态**
   ```dart
   print('Current session: ${chatService.sessionId}');
   ```

## 故障排除

### 工具未执行
- 确保服务器正在运行
- 检查 `useTools` 参数是否为 `true`
- 验证消息格式是否符合自然语言模式

### 会话丢失
- 调用 `resetSession()` 重新开始
- 检查服务器是否重启

### 网络错误
- 验证服务器URL是否正确
- 检查防火墙设置
- 确保设备可以访问服务器

## 示例项目

运行完整的演示应用：

```bash
cd masgui
flutter pub get
flutter run lib/mcp_demo_app.dart
```

这将启动一个包含所有功能的演示应用，展示如何使用MCP工具调用功能。
