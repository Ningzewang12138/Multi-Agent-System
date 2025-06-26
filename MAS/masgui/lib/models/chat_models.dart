/// 聊天相关的数据模型

/// 聊天消息
class ChatMessage {
  final String role;
  final String content;
  final DateTime? timestamp;
  final List<ToolCall>? toolCalls;
  
  ChatMessage({
    required this.role,
    required this.content,
    this.timestamp,
    this.toolCalls,
  });
  
  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      role: json['role'],
      content: json['content'],
      timestamp: json['timestamp'] != null 
          ? DateTime.parse(json['timestamp'])
          : null,
      toolCalls: json['tool_calls'] != null
          ? (json['tool_calls'] as List)
              .map((tc) => ToolCall.fromJson(tc))
              .toList()
          : null,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'role': role,
      'content': content,
      if (timestamp != null) 'timestamp': timestamp!.toIso8601String(),
      if (toolCalls != null) 'tool_calls': toolCalls!.map((tc) => tc.toJson()).toList(),
    };
  }
}

/// 工具调用
class ToolCall {
  final String id;
  final String type;
  final ToolFunction function;
  
  ToolCall({
    required this.id,
    required this.type,
    required this.function,
  });
  
  factory ToolCall.fromJson(Map<String, dynamic> json) {
    return ToolCall(
      id: json['id'],
      type: json['type'],
      function: ToolFunction.fromJson(json['function']),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'function': function.toJson(),
    };
  }
}

/// 工具函数
class ToolFunction {
  final String name;
  final String arguments;
  
  ToolFunction({
    required this.name,
    required this.arguments,
  });
  
  factory ToolFunction.fromJson(Map<String, dynamic> json) {
    return ToolFunction(
      name: json['name'],
      arguments: json['arguments'],
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'arguments': arguments,
    };
  }
}

/// 聊天响应
class ChatResponse {
  final String id;
  final String object;
  final int created;
  final String model;
  final List<Choice> choices;
  final Usage usage;
  final ToolExecution? toolExecution;
  final String? sessionId;
  
  ChatResponse({
    required this.id,
    required this.object,
    required this.created,
    required this.model,
    required this.choices,
    required this.usage,
    this.toolExecution,
    this.sessionId,
  });
  
  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    return ChatResponse(
      id: json['id'],
      object: json['object'],
      created: json['created'],
      model: json['model'],
      choices: (json['choices'] as List)
          .map((c) => Choice.fromJson(c))
          .toList(),
      usage: Usage.fromJson(json['usage']),
      toolExecution: json['tool_execution'] != null
          ? ToolExecution.fromJson(json['tool_execution'])
          : null,
      sessionId: json['session_id'],
    );
  }
}

/// 选择项
class Choice {
  final int index;
  final ChatMessage message;
  final String finishReason;
  
  Choice({
    required this.index,
    required this.message,
    required this.finishReason,
  });
  
  factory Choice.fromJson(Map<String, dynamic> json) {
    return Choice(
      index: json['index'],
      message: ChatMessage.fromJson(json['message']),
      finishReason: json['finish_reason'],
    );
  }
}

/// 使用统计
class Usage {
  final int promptTokens;
  final int completionTokens;
  final int totalTokens;
  
  Usage({
    required this.promptTokens,
    required this.completionTokens,
    required this.totalTokens,
  });
  
  factory Usage.fromJson(Map<String, dynamic> json) {
    return Usage(
      promptTokens: json['prompt_tokens'],
      completionTokens: json['completion_tokens'],
      totalTokens: json['total_tokens'],
    );
  }
}

/// 工具执行信息
class ToolExecution {
  final bool executed;
  final List<String> toolsCalled;
  final String sessionId;
  final String CodespacePath;
  
  ToolExecution({
    required this.executed,
    required this.toolsCalled,
    required this.sessionId,
    required this.CodespacePath,
  });
  
  factory ToolExecution.fromJson(Map<String, dynamic> json) {
    return ToolExecution(
      executed: json['executed'],
      toolsCalled: List<String>.from(json['tools_called']),
      sessionId: json['session_id'],
      CodespacePath: json['Codespace_path'],
    );
  }
}

/// 工作空间文件
class CodespaceFile {
  final String name;
  final int size;
  final String modified;
  final bool isDirectory;
  
  CodespaceFile({
    required this.name,
    required this.size,
    required this.modified,
    required this.isDirectory,
  });
  
  factory CodespaceFile.fromJson(Map<String, dynamic> json) {
    return CodespaceFile(
      name: json['name'],
      size: json['size'],
      modified: json['modified'],
      isDirectory: json['is_directory'],
    );
  }
}
