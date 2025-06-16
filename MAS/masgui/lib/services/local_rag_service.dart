import 'dart:convert';
import 'package:http/http.dart' as http;
import 'local/local_knowledge_base_service.dart';
import '../config/app_config.dart';

class LocalRAGService {
  final LocalKnowledgeBaseService _localKbService = LocalKnowledgeBaseService();
  
  static final LocalRAGService _instance = LocalRAGService._internal();
  factory LocalRAGService() => _instance;
  LocalRAGService._internal();

  // 使用本地知识库进行RAG对话
  Future<String> chatWithLocalRAG({
    required String query,
    required String knowledgeBaseId,
    String? model,
    int searchLimit = 5,
  }) async {
    try {
      // 1. 搜索相关文档
      final searchResults = await _localKbService.searchLocalKnowledgeBase(
        kbId: knowledgeBaseId,
        query: query,
        limit: searchLimit,
      );
      
      if (searchResults.isEmpty) {
        return await _directChat(query, model: model);
      }
      
      // 2. 构建上下文
      final context = _buildContext(searchResults);
      
      // 3. 构建增强的提示词
      final enhancedPrompt = _buildEnhancedPrompt(query, context);
      
      // 4. 调用本地Ollama进行对话
      return await _chatWithOllama(enhancedPrompt, model: model);
      
    } catch (e) {
      print('Error in local RAG: $e');
      // 降级到直接对话
      return await _directChat(query, model: model);
    }
  }

  // 构建上下文
  String _buildContext(List<Map<String, dynamic>> searchResults) {
    final buffer = StringBuffer();
    buffer.writeln('Based on the following relevant information:');
    buffer.writeln('---');
    
    for (int i = 0; i < searchResults.length; i++) {
      final result = searchResults[i];
      final content = result['content'] ?? '';
      final similarity = result['similarity'] ?? 0.0;
      
      buffer.writeln('Document ${i + 1} (Relevance: ${(similarity * 100).toStringAsFixed(1)}%):');
      buffer.writeln(content);
      buffer.writeln('---');
    }
    
    return buffer.toString();
  }

  // 构建增强的提示词
  String _buildEnhancedPrompt(String query, String context) {
    return '''$context

Based on the above context, please answer the following question. If the context doesn't contain relevant information, please indicate that and provide a general answer if possible.

Question: $query

Answer:''';
  }

  // 直接对话（不使用RAG）
  Future<String> _directChat(String query, {String? model}) async {
    return await _chatWithOllama(query, model: model);
  }

  // 调用本地Ollama
  Future<String> _chatWithOllama(String prompt, {String? model}) async {
    try {
      final ollamaUrl = 'http://localhost:11434/api/generate';
      final selectedModel = model ?? 'llama3:latest';
      
      final response = await http.post(
        Uri.parse(ollamaUrl),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'model': selectedModel,
          'prompt': prompt,
          'stream': false,
        }),
      ).timeout(const Duration(seconds: 60));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['response'] ?? 'No response generated';
      } else {
        throw Exception('Failed to generate response: ${response.statusCode}');
      }
    } catch (e) {
      print('Error calling Ollama: $e');
      return 'Error: Unable to generate response. Please check if Ollama is running locally.';
    }
  }

  // 检查本地Ollama是否可用
  Future<bool> isOllamaAvailable() async {
    try {
      final response = await http.get(
        Uri.parse('http://localhost:11434/api/tags'),
      ).timeout(const Duration(seconds: 5));
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  // 获取本地可用的模型
  Future<List<String>> getLocalModels() async {
    try {
      final response = await http.get(
        Uri.parse('http://localhost:11434/api/tags'),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final models = data['models'] as List;
        return models.map((m) => m['name'].toString()).toList();
      }
    } catch (e) {
      print('Error getting local models: $e');
    }
    return [];
  }
}
