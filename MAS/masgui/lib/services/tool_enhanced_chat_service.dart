import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/chat_models.dart';
import '../models/tool_models.dart';

/// MCP工具增强的聊天服务
class ToolEnhancedChatService {
  final String baseUrl;
  String? _sessionId;
  
  ToolEnhancedChatService({this.baseUrl = 'http://localhost:8000'});
  
  /// 获取当前会话ID
  String? get sessionId => _sessionId;
  
  /// 获取可用的MCP工具列表
  Future<List<Tool>> getAvailableTools() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/mcp/tools'),
      );
      
      if (response.statusCode == 200) {
        final List<dynamic> toolsJson = json.decode(response.body);
        return toolsJson.map((json) => Tool.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load tools: ${response.statusCode}');
      }
    } catch (e) {
      print('Error getting tools: $e');
      return [];
    }
  }
  
  /// 发送聊天消息（支持工具调用）
  Future<ChatResponse> sendMessage({
    required String message,
    List<ChatMessage>? history,
    bool useTools = true,
    String? model,
    String deviceId = 'flutter-client',
  }) async {
    // 构建消息列表
    final messages = <Map<String, String>>[];
    
    // 添加历史消息
    if (history != null) {
      for (final msg in history) {
        messages.add({
          'role': msg.role,
          'content': msg.content,
        });
      }
    }
    
    // 添加当前消息
    messages.add({
      'role': 'user',
      'content': message,
    });
    
    // 获取工具列表
    List<Map<String, dynamic>> tools = [];
    if (useTools) {
      final availableTools = await getAvailableTools();
      tools = availableTools.map((tool) => tool.toOpenAIFormat()).toList();
    }
    
    // 构建请求
    final requestBody = {
      'messages': messages,
      'tools': tools,
      'tool_choice': useTools ? 'auto' : 'none',
      'stream': false,
    };
    
    // 如果有会话ID，添加到请求中
    if (_sessionId != null) {
      requestBody['session_id'] = _sessionId!;
    }
    
    if (model != null) {
      requestBody['model'] = model;
    }
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/chat/completions'),
        headers: {
          'Content-Type': 'application/json',
          'X-Device-ID': deviceId,
        },
        body: json.encode(requestBody),
      );
      
      if (response.statusCode == 200) {
        final responseData = json.decode(response.body);
        
        // 更新会话ID
        if (responseData['session_id'] != null) {
          _sessionId = responseData['session_id'];
        }
        
        return ChatResponse.fromJson(responseData);
      } else {
        throw Exception('Failed to send message: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error sending message: $e');
    }
  }
  
  /// 发送聊天消息（流式响应）
  Stream<ChatStreamEvent> sendMessageStream({
    required String message,
    List<ChatMessage>? history,
    bool useTools = true,
    String? model,
    String deviceId = 'flutter-client',
  }) async* {
    // 构建消息列表
    final messages = <Map<String, String>>[];
    
    if (history != null) {
      for (final msg in history) {
        messages.add({
          'role': msg.role,
          'content': msg.content,
        });
      }
    }
    
    messages.add({
      'role': 'user',
      'content': message,
    });
    
    // 获取工具列表
    List<Map<String, dynamic>> tools = [];
    if (useTools) {
      final availableTools = await getAvailableTools();
      tools = availableTools.map((tool) => tool.toOpenAIFormat()).toList();
    }
    
    // 构建请求
    final requestBody = {
      'messages': messages,
      'tools': tools,
      'tool_choice': useTools ? 'auto' : 'none',
      'stream': true,
    };
    
    if (_sessionId != null) {
      requestBody['session_id'] = _sessionId!;
    }
    
    if (model != null) {
      requestBody['model'] = model;
    }
    
    // 创建HTTP请求
    final request = http.Request(
      'POST',
      Uri.parse('$baseUrl/api/chat/completions'),
    );
    
    request.headers['Content-Type'] = 'application/json';
    request.headers['X-Device-ID'] = deviceId;
    request.body = json.encode(requestBody);
    
    // 发送请求并处理流式响应
    final client = http.Client();
    try {
      final streamedResponse = await client.send(request);
      
      if (streamedResponse.statusCode != 200) {
        throw Exception('Failed to send message: ${streamedResponse.statusCode}');
      }
      
      // 处理流式响应
      await for (final chunk in streamedResponse.stream.transform(utf8.decoder)) {
        final lines = chunk.split('\n');
        
        for (final line in lines) {
          if (line.startsWith('data: ')) {
            final data = line.substring(6);
            if (data == '[DONE]') {
              break;
            }
            
            try {
              final event = json.decode(data);
              
              // 更新会话ID
              if (event['session_id'] != null) {
                _sessionId = event['session_id'];
              }
              
              // 生成相应的事件
              if (event['type'] == 'content') {
                yield ContentEvent(event['delta']['content']);
              } else if (event['type'] == 'tool_call') {
                yield ToolCallEvent(
                  toolName: event['tool_call']['function']['name'],
                  callId: event['tool_call']['id'],
                );
              } else if (event['type'] == 'tool_result') {
                yield ToolResultEvent(
                  callId: event['tool_call_id'],
                  success: event['result']['success'],
                  result: event['result'],
                );
              } else if (event['type'] == 'tool_execution') {
                yield ToolExecutionEvent(
                  executed: event['data']['executed'],
                  toolsCalled: List<String>.from(event['data']['tools_called']),
                  sessionId: event['data']['session_id'],
                  workspacePath: event['data']['workspace_path'],
                );
              } else if (event['type'] == 'done') {
                yield DoneEvent(event['finish_reason']);
              }
            } catch (e) {
              // 忽略解析错误，继续处理
              print('Error parsing event: $e');
            }
          }
        }
      }
    } finally {
      client.close();
    }
  }
  
  /// 获取工作空间文件列表
  Future<List<WorkspaceFile>> getWorkspaceFiles() async {
    if (_sessionId == null) {
      return [];
    }
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/mcp/workspace/$_sessionId/files'),
      );
      
      if (response.statusCode == 200) {
        final List<dynamic> filesJson = json.decode(response.body);
        return filesJson.map((json) => WorkspaceFile.fromJson(json)).toList();
      } else if (response.statusCode == 404) {
        return [];
      } else {
        throw Exception('Failed to get workspace files: ${response.statusCode}');
      }
    } catch (e) {
      print('Error getting workspace files: $e');
      return [];
    }
  }
  
  /// 下载工作空间文件
  Future<String> downloadWorkspaceFile(String filename) async {
    if (_sessionId == null) {
      throw Exception('No active session');
    }
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/mcp/workspace/$_sessionId/file/$filename'),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['content'];
      } else {
        throw Exception('Failed to download file: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error downloading file: $e');
    }
  }
  
  /// 重置会话
  void resetSession() {
    _sessionId = null;
  }
}

/// 聊天流事件基类
abstract class ChatStreamEvent {}

/// 内容事件
class ContentEvent extends ChatStreamEvent {
  final String content;
  ContentEvent(this.content);
}

/// 工具调用事件
class ToolCallEvent extends ChatStreamEvent {
  final String toolName;
  final String callId;
  ToolCallEvent({required this.toolName, required this.callId});
}

/// 工具结果事件
class ToolResultEvent extends ChatStreamEvent {
  final String callId;
  final bool success;
  final Map<String, dynamic> result;
  ToolResultEvent({
    required this.callId,
    required this.success,
    required this.result,
  });
}

/// 工具执行事件
class ToolExecutionEvent extends ChatStreamEvent {
  final bool executed;
  final List<String> toolsCalled;
  final String sessionId;
  final String workspacePath;
  
  ToolExecutionEvent({
    required this.executed,
    required this.toolsCalled,
    required this.sessionId,
    required this.workspacePath,
  });
}

/// 完成事件
class DoneEvent extends ChatStreamEvent {
  final String reason;
  DoneEvent(this.reason);
}
