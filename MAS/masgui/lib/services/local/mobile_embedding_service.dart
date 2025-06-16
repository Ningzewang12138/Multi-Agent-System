import 'dart:typed_data';
import 'dart:convert';
import 'dart:math';
import 'package:crypto/crypto.dart';

class MobileEmbeddingService {
  static final MobileEmbeddingService _instance = MobileEmbeddingService._internal();
  factory MobileEmbeddingService() => _instance;
  MobileEmbeddingService._internal();

  // 使用不同的嵌入策略
  EmbeddingStrategy _strategy = EmbeddingStrategy.simpleHash;
  
  // TF-IDF词汇表（可以预先加载常用词汇）
  Map<String, double> _idfScores = {};
  Set<String> _vocabulary = {};

  Future<void> initialize() async {
    // 加载预计算的IDF分数或词汇表
    await _loadVocabulary();
  }

  // 根据设备能力选择嵌入策略
  Future<List<double>> embedText(String text) async {
    switch (_strategy) {
      case EmbeddingStrategy.simpleHash:
        return _simpleHashEmbedding(text);
      
      case EmbeddingStrategy.tfidf:
        return _tfidfEmbedding(text);
      
      case EmbeddingStrategy.sentencepiece:
        return _sentencePieceEmbedding(text);
      
      case EmbeddingStrategy.remoteApi:
        return await _remoteApiEmbedding(text);
    }
  }

  // 1. 简单哈希嵌入（最轻量，适合低端设备）
  List<double> _simpleHashEmbedding(String text, {int dimension = 128}) {
    // 预处理文本
    text = text.toLowerCase().trim();
    final words = text.split(RegExp(r'\s+'));
    
    // 初始化嵌入向量
    final embedding = List<double>.filled(dimension, 0.0);
    
    // 使用多个哈希函数生成特征
    for (final word in words) {
      // 使用不同的哈希函数
      final hash1 = md5.convert(utf8.encode(word)).hashCode;
      final hash2 = sha1.convert(utf8.encode(word)).hashCode;
      final hash3 = sha256.convert(utf8.encode(word)).hashCode;
      
      // 映射到向量维度
      embedding[hash1.abs() % dimension] += 1.0;
      embedding[hash2.abs() % dimension] += 0.5;
      embedding[hash3.abs() % dimension] += 0.3;
    }
    
    // 归一化
    return _normalize(embedding);
  }

  // 2. TF-IDF嵌入（中等复杂度）
  List<double> _tfidfEmbedding(String text, {int dimension = 256}) {
    text = text.toLowerCase().trim();
    final words = text.split(RegExp(r'\s+'));
    
    // 计算词频
    final tf = <String, double>{};
    for (final word in words) {
      tf[word] = (tf[word] ?? 0) + 1;
    }
    
    // 归一化词频
    final maxFreq = tf.values.reduce(max);
    tf.updateAll((key, value) => value / maxFreq);
    
    // 创建嵌入向量
    final embedding = List<double>.filled(dimension, 0.0);
    
    // 将TF-IDF分数映射到向量
    tf.forEach((word, tfScore) {
      final idfScore = _idfScores[word] ?? log(10000); // 默认IDF
      final tfidfScore = tfScore * idfScore;
      
      // 使用哈希将词映射到向量位置
      final position = word.hashCode.abs() % dimension;
      embedding[position] += tfidfScore;
    });
    
    return _normalize(embedding);
  }

  // 3. SentencePiece嵌入（使用预训练的小型分词器）
  List<double> _sentencePieceEmbedding(String text) {
    // 这里可以集成一个轻量级的分词器
    // 例如：使用Flutter的sentencepiece插件
    // 暂时返回简单实现
    return _simpleHashEmbedding(text, dimension: 384);
  }

  // 4. 远程API嵌入（需要网络，但最准确）
  Future<List<double>> _remoteApiEmbedding(String text) async {
    try {
      // 可以调用免费的嵌入API，如：
      // - Hugging Face API
      // - OpenAI API (如果有key)
      // - 自建的轻量级嵌入服务
      
      // 示例：调用本地服务器的嵌入API
      final response = await http.post(
        Uri.parse('http://localhost:8000/api/embeddings'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'text': text}),
      ).timeout(const Duration(seconds: 10));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return List<double>.from(data['embedding']);
      }
    } catch (e) {
      print('Remote embedding failed, falling back to local: $e');
    }
    
    // 降级到本地嵌入
    return _simpleHashEmbedding(text);
  }

  // 加载词汇表
  Future<void> _loadVocabulary() async {
    // 可以从assets加载预计算的词汇表
    // 或者使用最常见的1000-5000个词
    _vocabulary = {
      'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
      'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
      // ... 更多常用词
    };
    
    // 简单的IDF计算
    int totalDocs = 10000; // 假设的文档总数
    _vocabulary.forEach((word) {
      // 简化的IDF计算
      _idfScores[word] = log(totalDocs / 100); // 假设每个词出现在100个文档中
    });
  }

  // 向量归一化
  List<double> _normalize(List<double> vector) {
    double sum = 0;
    for (final val in vector) {
      sum += val * val;
    }
    
    if (sum == 0) return vector;
    
    final norm = 1.0 / sqrt(sum);
    return vector.map((val) => val * norm).toList();
  }

  // 余弦相似度计算（保持不变）
  double cosineSimilarity(List<double> a, List<double> b) {
    if (a.length != b.length) return 0;
    
    double dotProduct = 0;
    double normA = 0;
    double normB = 0;
    
    for (int i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
    
    if (normA == 0 || normB == 0) return 0;
    
    return dotProduct / (sqrt(normA) * sqrt(normB));
  }

  // 批量嵌入优化
  Future<List<List<double>>> embedTexts(List<String> texts) async {
    final embeddings = <List<double>>[];
    
    // 如果是远程API，可以批量发送
    if (_strategy == EmbeddingStrategy.remoteApi) {
      // 批量处理逻辑
      for (final text in texts) {
        embeddings.add(await embedText(text));
      }
    } else {
      // 本地处理
      for (final text in texts) {
        embeddings.add(await embedText(text));
      }
    }
    
    return embeddings;
  }

  // 根据设备能力自动选择策略
  void autoSelectStrategy() {
    // 检查设备内存
    final totalMemory = MemoryInfo.getTotalMemory(); // 需要实现
    
    if (totalMemory < 2 * 1024 * 1024 * 1024) { // < 2GB
      _strategy = EmbeddingStrategy.simpleHash;
    } else if (totalMemory < 4 * 1024 * 1024 * 1024) { // < 4GB
      _strategy = EmbeddingStrategy.tfidf;
    } else {
      _strategy = EmbeddingStrategy.sentencepiece;
    }
  }
}

enum EmbeddingStrategy {
  simpleHash,    // 最轻量
  tfidf,         // 中等
  sentencepiece, // 较重
  remoteApi,     // 需要网络
}

// 内存信息辅助类（需要根据平台实现）
class MemoryInfo {
  static int getTotalMemory() {
    // 根据平台获取内存信息
    // iOS: 使用 ProcessInfo
    // Android: 使用 ActivityManager
    return 4 * 1024 * 1024 * 1024; // 默认4GB
  }
}
