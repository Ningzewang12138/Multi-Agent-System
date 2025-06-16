import 'dart:convert';
import 'package:http/http.dart' as http;
import 'mobile_embedding_service.dart';
import 'local_knowledge_base_service.dart';

class MobileRAGService {
  final MobileEmbeddingService _embeddingService = MobileEmbeddingService();
  final LocalKnowledgeBaseService _kbService = LocalKnowledgeBaseService();
  
  static final MobileRAGService _instance = MobileRAGService._internal();
  factory MobileRAGService() => _instance;
  MobileRAGService._internal();

  // RAG策略
  RAGStrategy _strategy = RAGStrategy.hybrid;

  Future<void> initialize() async {
    await _embeddingService.initialize();
    _autoSelectStrategy();
  }

  // 移动端RAG对话
  Future<String> mobileRAGChat({
    required String query,
    required String knowledgeBaseId,
    String? model,
  }) async {
    switch (_strategy) {
      case RAGStrategy.localOnly:
        return await _localOnlyRAG(query, knowledgeBaseId);
      
      case RAGStrategy.remoteModel:
        return await _remoteModelRAG(query, knowledgeBaseId, model);
      
      case RAGStrategy.hybrid:
        return await _hybridRAG(query, knowledgeBaseId, model);
      
      case RAGStrategy.templateBased:
        return await _templateBasedRAG(query, knowledgeBaseId);
    }
  }

  // 1. 纯本地RAG（使用模板和规则）
  Future<String> _localOnlyRAG(String query, String kbId) async {
    // 搜索相关文档
    final results = await _kbService.searchLocalKnowledgeBase(
      kbId: kbId,
      query: query,
      limit: 3,
    );
    
    if (results.isEmpty) {
      return "I couldn't find any relevant information in the knowledge base for your query.";
    }
    
    // 构建基于模板的响应
    final buffer = StringBuffer();
    buffer.writeln("Based on the knowledge base, here's what I found:");
    buffer.writeln();
    
    for (int i = 0; i < results.length; i++) {
      final content = results[i]['content'] ?? '';
      final similarity = results[i]['similarity'] ?? 0.0;
      
      if (similarity > 0.7) {
        buffer.writeln("• ${_extractKeyPoints(content, query)}");
      }
    }
    
    return buffer.toString();
  }

  // 2. 远程模型RAG（连接到服务器或云API）
  Future<String> _remoteModelRAG(String query, String kbId, String? model) async {
    // 搜索相关文档
    final results = await _kbService.searchLocalKnowledgeBase(
      kbId: kbId,
      query: query,
      limit: 5,
    );
    
    // 构建上下文
    final context = _buildContext(results);
    
    // 尝试不同的远程服务
    // A. 本地网络中的Ollama服务器
    String? response = await _tryLocalNetworkOllama(query, context, model);
    if (response != null) return response;
    
    // B. 云端API（如果有配置）
    response = await _tryCloudAPI(query, context);
    if (response != null) return response;
    
    // C. 降级到模板响应
    return _localOnlyRAG(query, kbId);
  }

  // 3. 混合RAG（优先远程，降级到本地）
  Future<String> _hybridRAG(String query, String kbId, String? model) async {
    try {
      // 首先尝试远程模型
      return await _remoteModelRAG(query, kbId, model);
    } catch (e) {
      print('Remote RAG failed, falling back to local: $e');
      // 降级到本地处理
      return await _localOnlyRAG(query, kbId);
    }
  }

  // 4. 基于模板的智能RAG（不需要LLM）
  Future<String> _templateBasedRAG(String query, String kbId) async {
    // 分析查询类型
    final queryType = _analyzeQueryType(query);
    
    // 搜索相关文档
    final results = await _kbService.searchLocalKnowledgeBase(
      kbId: kbId,
      query: query,
      limit: 5,
    );
    
    if (results.isEmpty) {
      return _getNoResultTemplate(queryType);
    }
    
    // 根据查询类型选择模板
    switch (queryType) {
      case QueryType.definition:
        return _buildDefinitionResponse(query, results);
      
      case QueryType.howTo:
        return _buildHowToResponse(query, results);
      
      case QueryType.comparison:
        return _buildComparisonResponse(query, results);
      
      case QueryType.listing:
        return _buildListingResponse(query, results);
      
      default:
        return _buildGeneralResponse(query, results);
    }
  }

  // 尝试本地网络中的Ollama
  Future<String?> _tryLocalNetworkOllama(
    String query,
    String context,
    String? model,
  ) async {
    // 尝试常见的本地网络地址
    final addresses = [
      'http://localhost:11434',
      'http://127.0.0.1:11434',
      'http://192.168.1.100:11434', // 常见的局域网地址
      // 可以添加更多地址或使用网络发现
    ];
    
    for (final address in addresses) {
      try {
        final response = await http.post(
          Uri.parse('$address/api/generate'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'model': model ?? 'llama3:latest',
            'prompt': _buildPrompt(query, context),
            'stream': false,
          }),
        ).timeout(const Duration(seconds: 10));
        
        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          return data['response'];
        }
      } catch (e) {
        continue; // 尝试下一个地址
      }
    }
    
    return null;
  }

  // 尝试云端API
  Future<String?> _tryCloudAPI(String query, String context) async {
    // 检查是否配置了API密钥
    final apiKey = await _getCloudAPIKey();
    if (apiKey == null) return null;
    
    try {
      // 示例：使用免费的API服务
      // 可以是Hugging Face、Cohere、或其他提供免费额度的服务
      final response = await http.post(
        Uri.parse('https://api.example.com/v1/completions'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $apiKey',
        },
        body: json.encode({
          'prompt': _buildPrompt(query, context),
          'max_tokens': 500,
        }),
      ).timeout(const Duration(seconds: 20));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['choices'][0]['text'];
      }
    } catch (e) {
      print('Cloud API failed: $e');
    }
    
    return null;
  }

  // 构建提示词
  String _buildPrompt(String query, String context) {
    return '''Context information:
$context

Based on the above context, please answer the following question:
$query

Answer:''';
  }

  // 构建上下文
  String _buildContext(List<Map<String, dynamic>> results) {
    final buffer = StringBuffer();
    for (final result in results) {
      buffer.writeln(result['content'] ?? '');
      buffer.writeln('---');
    }
    return buffer.toString();
  }

  // 分析查询类型
  QueryType _analyzeQueryType(String query) {
    query = query.toLowerCase();
    
    if (query.startsWith('what is') || query.startsWith('define')) {
      return QueryType.definition;
    } else if (query.startsWith('how to') || query.startsWith('how do')) {
      return QueryType.howTo;
    } else if (query.contains('vs') || query.contains('compare')) {
      return QueryType.comparison;
    } else if (query.startsWith('list') || query.contains('what are')) {
      return QueryType.listing;
    } else {
      return QueryType.general;
    }
  }

  // 提取关键点
  String _extractKeyPoints(String content, String query) {
    // 简单的关键句提取
    final sentences = content.split(RegExp(r'[.!?]'));
    final queryWords = query.toLowerCase().split(' ');
    
    // 找出包含查询词最多的句子
    String bestSentence = '';
    int maxMatches = 0;
    
    for (final sentence in sentences) {
      final lowerSentence = sentence.toLowerCase();
      int matches = 0;
      
      for (final word in queryWords) {
        if (lowerSentence.contains(word)) matches++;
      }
      
      if (matches > maxMatches) {
        maxMatches = matches;
        bestSentence = sentence.trim();
      }
    }
    
    return bestSentence.isNotEmpty ? bestSentence : sentences.first.trim();
  }

  // 构建定义类响应
  String _buildDefinitionResponse(String query, List<Map<String, dynamic>> results) {
    final term = query.replaceAll(RegExp(r'^what is |^define '), '').trim();
    final buffer = StringBuffer();
    
    buffer.writeln('Based on the knowledge base:');
    buffer.writeln();
    buffer.writeln('$term is ${_extractKeyPoints(results.first['content'], query)}');
    
    if (results.length > 1) {
      buffer.writeln();
      buffer.writeln('Additional information:');
      buffer.writeln('• ${_extractKeyPoints(results[1]['content'], query)}');
    }
    
    return buffer.toString();
  }

  // 其他响应构建方法...
  String _buildHowToResponse(String query, List<Map<String, dynamic>> results) {
    // 实现how-to类响应
    return 'How-to response based on: ${results.first['content']}';
  }

  String _buildComparisonResponse(String query, List<Map<String, dynamic>> results) {
    // 实现比较类响应
    return 'Comparison based on available information...';
  }

  String _buildListingResponse(String query, List<Map<String, dynamic>> results) {
    // 实现列表类响应
    return 'List of items found in knowledge base...';
  }

  String _buildGeneralResponse(String query, List<Map<String, dynamic>> results) {
    // 实现通用响应
    return 'Based on the knowledge base: ${_extractKeyPoints(results.first['content'], query)}';
  }

  String _getNoResultTemplate(QueryType type) {
    switch (type) {
      case QueryType.definition:
        return "I couldn't find a definition for that term in the knowledge base.";
      case QueryType.howTo:
        return "I don't have instructions for that in the knowledge base.";
      default:
        return "I couldn't find relevant information for your query in the knowledge base.";
    }
  }

  // 自动选择策略
  void _autoSelectStrategy() {
    // 根据设备能力和网络状态选择策略
    // 这里需要实际的设备检测逻辑
    _strategy = RAGStrategy.hybrid;
  }

  // 获取云API密钥
  Future<String?> _getCloudAPIKey() async {
    // 从安全存储获取API密钥
    return null; // 需要实现
  }
}

enum RAGStrategy {
  localOnly,     // 纯本地处理
  remoteModel,   // 使用远程模型
  hybrid,        // 混合模式
  templateBased, // 基于模板
}

enum QueryType {
  definition,
  howTo,
  comparison,
  listing,
  general,
}
