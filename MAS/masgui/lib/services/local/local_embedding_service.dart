import 'dart:typed_data';
import 'dart:convert';
import 'package:http/http.dart' as http;

class LocalEmbeddingService {
  static final LocalEmbeddingService _instance = LocalEmbeddingService._internal();
  factory LocalEmbeddingService() => _instance;
  LocalEmbeddingService._internal();

  // 使用本地的Ollama嵌入模型
  String? _localOllamaUrl;
  String _embeddingModel = 'nomic-embed-text:latest';

  Future<void> initialize({String? ollamaUrl, String? model}) async {
    _localOllamaUrl = ollamaUrl ?? 'http://localhost:11434';
    if (model != null) {
      _embeddingModel = model;
    }
    
    // 检查本地Ollama是否可用
    await checkLocalOllama();
  }

  Future<bool> checkLocalOllama() async {
    try {
      final response = await http.get(
        Uri.parse('$_localOllamaUrl/api/tags'),
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final models = data['models'] as List;
        
        // 检查是否有嵌入模型
        final hasEmbeddingModel = models.any((model) => 
          model['name'].toString().contains('embed') ||
          model['name'].toString().contains('bge')
        );
        
        print('Local Ollama available. Has embedding model: $hasEmbeddingModel');
        return hasEmbeddingModel;
      }
    } catch (e) {
      print('Local Ollama not available: $e');
    }
    return false;
  }

  // 生成文本嵌入
  Future<List<double>?> embedText(String text) async {
    if (_localOllamaUrl == null) {
      print('Local Ollama URL not set');
      return null;
    }

    try {
      final response = await http.post(
        Uri.parse('$_localOllamaUrl/api/embeddings'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'model': _embeddingModel,
          'prompt': text,
        }),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final embedding = data['embedding'] as List;
        return embedding.map((e) => (e as num).toDouble()).toList();
      }
    } catch (e) {
      print('Error generating embedding: $e');
    }
    
    // 如果失败，返回一个简单的哈希嵌入作为备选
    return _generateSimpleEmbedding(text);
  }

  // 批量生成嵌入
  Future<List<List<double>>> embedTexts(List<String> texts) async {
    final embeddings = <List<double>>[];
    
    for (final text in texts) {
      final embedding = await embedText(text);
      embeddings.add(embedding ?? _generateSimpleEmbedding(text));
    }
    
    return embeddings;
  }

  // 简单的文本嵌入生成（作为备选方案）
  List<double> _generateSimpleEmbedding(String text, {int dimension = 384}) {
    // 使用简单的哈希方法生成固定维度的向量
    final bytes = utf8.encode(text);
    final embedding = List<double>.filled(dimension, 0.0);
    
    for (int i = 0; i < bytes.length; i++) {
      final index = i % dimension;
      embedding[index] += bytes[i] / 255.0;
    }
    
    // 归一化
    double sum = 0;
    for (final val in embedding) {
      sum += val * val;
    }
    final norm = 1.0 / (sum > 0 ? sum : 1.0);
    
    for (int i = 0; i < embedding.length; i++) {
      embedding[i] *= norm;
    }
    
    return embedding;
  }

  // 计算余弦相似度
  double cosineSimilarity(List<double> a, List<double> b) {
    if (a.length != b.length) {
      throw ArgumentError('Vectors must have the same dimension');
    }

    double dotProduct = 0;
    double normA = 0;
    double normB = 0;

    for (int i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    if (normA == 0 || normB == 0) {
      return 0;
    }

    return dotProduct / (normA * normB);
  }

  // 将嵌入转换为Uint8List用于存储
  Uint8List embeddingToBytes(List<double> embedding) {
    final buffer = ByteData(embedding.length * 8);
    for (int i = 0; i < embedding.length; i++) {
      buffer.setFloat64(i * 8, embedding[i], Endian.little);
    }
    return buffer.buffer.asUint8List();
  }

  // 从Uint8List恢复嵌入
  List<double> embeddingFromBytes(Uint8List bytes) {
    final buffer = ByteData.sublistView(bytes);
    final embedding = <double>[];
    
    for (int i = 0; i < bytes.length ~/ 8; i++) {
      embedding.add(buffer.getFloat64(i * 8, Endian.little));
    }
    
    return embedding;
  }
}
