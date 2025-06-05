import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';

class MultiAgentService {
  // 单例模式
  static final MultiAgentService _instance = MultiAgentService._internal();
  factory MultiAgentService() => _instance;
  MultiAgentService._internal();

  // 获取可用模型列表
  Future<List<Map<String, dynamic>>> getModels() async {
    try {
      final response = await http.get(
        Uri.parse(AppConfig.modelsEndpoint),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return List<Map<String, dynamic>>.from(data['data'] ?? []);
      }
      throw Exception('Failed to load models');
    } catch (e) {
      print('Error getting models: $e');
      return [];
    }
  }

  // 普通聊天
  Future<Map<String, dynamic>> sendMessage(
    List<Map<String, String>> messages, {
    String? model,
    bool stream = false,
  }) async {
    try {
      final response = await http.post(
        Uri.parse(AppConfig.chatEndpoint),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'messages': messages,
          'stream': stream,
          if (model != null) 'model': model,
        }),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      throw Exception('Failed to send message');
    } catch (e) {
      print('Error sending message: $e');
      rethrow;
    }
  }

  // RAG 聊天（新增功能）
  Future<Map<String, dynamic>> sendRAGMessage(
    List<Map<String, String>> messages,
    String knowledgeBaseId, {
    String? model,
    int searchLimit = 5,
  }) async {
    try {
      final response = await http.post(
        Uri.parse(AppConfig.ragEndpoint),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'knowledge_base_id': knowledgeBaseId,
          'messages': messages,
          'stream': false,
          'search_limit': searchLimit,
          if (model != null) 'model': model,
        }),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      throw Exception('Failed to send RAG message');
    } catch (e) {
      print('Error sending RAG message: $e');
      rethrow;
    }
  }

  // 获取知识库列表（新增功能）
  Future<List<Map<String, dynamic>>> getKnowledgeBases() async {
    try {
      final response = await http.get(
        Uri.parse(AppConfig.knowledgeEndpoint),
      );

      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(json.decode(response.body));
      }
      throw Exception('Failed to load knowledge bases');
    } catch (e) {
      print('Error getting knowledge bases: $e');
      return [];
    }
  }

  // 创建知识库（新增功能）
  Future<Map<String, dynamic>> createKnowledgeBase(
    String name,
    String description,
  ) async {
    try {
      final response = await http.post(
        Uri.parse(AppConfig.knowledgeEndpoint),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'name': name,
          'description': description,
        }),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      throw Exception('Failed to create knowledge base');
    } catch (e) {
      print('Error creating knowledge base: $e');
      rethrow;
    }
  }

  // 添加文档到知识库（新增功能）
  Future<void> addDocument(
    String knowledgeBaseId,
    String content, {
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'content': content,
          'metadata': metadata ?? {},
        }),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to add document');
      }
    } catch (e) {
      print('Error adding document: $e');
      rethrow;
    }
  }

  // 测试连接
  Future<bool> testConnection() async {
    try {
      final response = await http.get(
        Uri.parse(AppConfig.baseUrl),
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      print('Connection test failed: $e');
      return false;
    }
  }
}
