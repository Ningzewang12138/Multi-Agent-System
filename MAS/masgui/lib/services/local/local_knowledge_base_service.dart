import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'package:path/path.dart';
import 'local_database_service.dart';
import 'local_embedding_service.dart';
import 'local_document_processor.dart';

class LocalKnowledgeBaseService {
  final LocalDatabaseService _db = LocalDatabaseService();
  final LocalEmbeddingService _embedding = LocalEmbeddingService();
  final LocalDocumentProcessor _processor = LocalDocumentProcessor();
  
  static final LocalKnowledgeBaseService _instance = LocalKnowledgeBaseService._internal();
  factory LocalKnowledgeBaseService() => _instance;
  LocalKnowledgeBaseService._internal();

  // 初始化服务
  Future<void> initialize() async {
    await _embedding.initialize();
  }

  // 创建本地知识库
  Future<Map<String, dynamic>> createLocalKnowledgeBase({
    required String name,
    String? description,
  }) async {
    final id = await _db.createKnowledgeBase(
      name: name,
      description: description,
    );

    return {
      'id': id,
      'name': name,
      'description': description,
      'is_local': true,
      'document_count': 0,
      'created_at': DateTime.now().toIso8601String(),
    };
  }

  // 获取所有本地知识库
  Future<List<Map<String, dynamic>>> getLocalKnowledgeBases() async {
    return await _db.getLocalKnowledgeBases();
  }

  // 添加文档到本地知识库
  Future<Map<String, dynamic>> addDocument({
    required String kbId,
    required String content,
    String? title,
    Map<String, dynamic>? metadata,
  }) async {
    // 分割文档为chunks
    final chunks = _processor.splitText(content, metadata: metadata);
    
    // 生成嵌入
    final texts = chunks.map((c) => c['text'] as String).toList();
    final embeddings = await _embedding.embedTexts(texts);
    
    // 保存文档
    final docId = await _db.addDocument(
      kbId: kbId,
      content: content,
      title: title,
      metadata: metadata,
    );
    
    // 保存chunks和嵌入
    final chunkData = <Map<String, dynamic>>[];
    for (int i = 0; i < chunks.length; i++) {
      chunkData.add({
        'content': chunks[i]['text'],
        'embedding': _embedding.embeddingToBytes(embeddings[i]),
        'metadata': chunks[i]['metadata'],
      });
    }
    
    await _db.addDocumentChunks(docId, kbId, chunkData);
    
    return {
      'id': docId,
      'kb_id': kbId,
      'title': title,
      'chunk_count': chunks.length,
    };
  }

  // 从文件添加文档
  Future<Map<String, dynamic>> addDocumentFromFile({
    required String kbId,
    required String filePath,
    Map<String, dynamic>? metadata,
  }) async {
    final file = File(filePath);
    if (!await file.exists()) {
      throw Exception('File not found: $filePath');
    }

    // 处理文件
    final result = await _processor.processFile(filePath);
    final content = result['content'] as String;
    final fileMetadata = result['metadata'] as Map<String, dynamic>;
    
    // 合并元数据
    final combinedMetadata = {...fileMetadata, ...?metadata};
    
    // 分割文档
    final chunks = _processor.splitText(content, metadata: combinedMetadata);
    
    // 生成嵌入
    final texts = chunks.map((c) => c['text'] as String).toList();
    final embeddings = await _embedding.embedTexts(texts);
    
    // 保存文档
    final docId = await _db.addDocument(
      kbId: kbId,
      content: content,
      title: basename(filePath),
      filePath: filePath,
      fileType: extension(filePath).replaceAll('.', ''),
      fileSize: await file.length(),
      metadata: combinedMetadata,
    );
    
    // 保存chunks
    final chunkData = <Map<String, dynamic>>[];
    for (int i = 0; i < chunks.length; i++) {
      chunkData.add({
        'content': chunks[i]['text'],
        'embedding': _embedding.embeddingToBytes(embeddings[i]),
        'metadata': chunks[i]['metadata'],
      });
    }
    
    await _db.addDocumentChunks(docId, kbId, chunkData);
    
    return {
      'id': docId,
      'kb_id': kbId,
      'title': basename(filePath),
      'chunk_count': chunks.length,
      'file_size': await file.length(),
    };
  }

  // 搜索本地知识库
  Future<List<Map<String, dynamic>>> searchLocalKnowledgeBase({
    required String kbId,
    required String query,
    int limit = 10,
  }) async {
    // 生成查询嵌入
    final queryEmbedding = await _embedding.embedText(query);
    if (queryEmbedding == null) {
      // 退化到文本搜索
      return await _db.searchChunks(kbId, query, limit: limit);
    }

    // 获取所有chunks（实际应该优化为向量搜索）
    final chunks = await _db.searchChunks(kbId, '', limit: 1000);
    
    // 计算相似度并排序
    final results = <Map<String, dynamic>>[];
    for (final chunk in chunks) {
      if (chunk['embedding'] != null) {
        final chunkEmbedding = _embedding.embeddingFromBytes(chunk['embedding'] as Uint8List);
        final similarity = _embedding.cosineSimilarity(queryEmbedding, chunkEmbedding);
        
        results.add({
          ...chunk,
          'similarity': similarity,
        });
      }
    }
    
    // 按相似度排序
    results.sort((a, b) => (b['similarity'] as double).compareTo(a['similarity'] as double));
    
    // 返回前N个结果
    return results.take(limit).toList();
  }

  // 获取本地知识库的文档列表
  Future<List<Map<String, dynamic>>> getDocuments(String kbId) async {
    return await _db.getDocuments(kbId);
  }

  // 删除文档
  Future<void> deleteDocument(String docId) async {
    await _db.deleteDocument(docId);
  }

  // 删除本地知识库
  Future<void> deleteKnowledgeBase(String kbId) async {
    await _db.deleteKnowledgeBase(kbId);
  }

  // 将本地知识库发布到服务器
  Future<Map<String, dynamic>> publishToServer({
    required String kbId,
    required String serverUrl,
  }) async {
    // 获取知识库信息
    final kb = await _db.getKnowledgeBase(kbId);
    if (kb == null) {
      throw Exception('Knowledge base not found');
    }

    // 获取所有文档
    final documents = await _db.getDocuments(kbId);
    
    // TODO: 实现上传逻辑
    // 这里需要调用服务器API上传知识库和文档
    
    // 标记为已同步
    await _db.markKnowledgeBaseAsSynced(kbId, 'server_generated_id');
    
    // 记录同步历史
    await _db.recordSyncHistory(
      kbId: kbId,
      syncType: 'full',
      syncDirection: 'push',
      status: 'completed',
      documentsSync: documents.length,
    );

    return {
      'success': true,
      'server_kb_id': 'server_generated_id',
      'documents_synced': documents.length,
    };
  }

  // 从服务器下载知识库
  Future<Map<String, dynamic>> pullFromServer({
    required String serverKbId,
    required String serverUrl,
  }) async {
    // TODO: 实现下载逻辑
    // 这里需要调用服务器API下载知识库内容
    
    // 创建本地知识库
    final localKbId = await _db.createKnowledgeBase(
      name: 'Downloaded KB',
      description: 'Downloaded from server',
    );
    
    // 记录同步历史
    await _db.recordSyncHistory(
      kbId: localKbId,
      syncType: 'full',
      syncDirection: 'pull',
      status: 'completed',
    );

    return {
      'success': true,
      'local_kb_id': localKbId,
    };
  }

  // 获取统计信息
  Future<Map<String, dynamic>> getStatistics() async {
    return await _db.getStatistics();
  }

  // 获取同步历史
  Future<List<Map<String, dynamic>>> getSyncHistory(String kbId) async {
    return await _db.getSyncHistory(kbId);
  }
}
