import 'dart:io';
import '../config/app_config.dart';
import '../models/knowledge_base.dart';
import 'multi_agent_service.dart';
import 'local/local_knowledge_base_service.dart';

enum KnowledgeBaseLocation {
  local,
  server,
  synced,
}

class UnifiedKnowledgeBaseService {
  final MultiAgentService _remoteService = MultiAgentService();
  final LocalKnowledgeBaseService _localService = LocalKnowledgeBaseService();
  
  static final UnifiedKnowledgeBaseService _instance = UnifiedKnowledgeBaseService._internal();
  factory UnifiedKnowledgeBaseService() => _instance;
  UnifiedKnowledgeBaseService._internal();

  // 初始化
  Future<void> initialize() async {
    await _localService.initialize();
  }

  // 获取所有知识库（本地+服务器）
  Future<List<Map<String, dynamic>>> getAllKnowledgeBases({
    bool includeLocal = true,
    bool includeServer = true,
    bool includeSynced = true,
  }) async {
    final allKbs = <Map<String, dynamic>>[];
    
    // 获取本地知识库
    if (includeLocal) {
      try {
        final localKbs = await _localService.getLocalKnowledgeBases();
        for (final kb in localKbs) {
          allKbs.add({
            ...kb,
            'location': 'local',
            'can_sync': !kb['is_synced'],
          });
        }
      } catch (e) {
        print('Error loading local knowledge bases: $e');
      }
    }
    
    // 获取服务器知识库
    if (includeServer && AppConfig.serverMode == 'multiagent') {
      try {
        final serverKbs = await _remoteService.getKnowledgeBases();
        for (final kb in serverKbs) {
          // 检查是否是当前设备创建的
          final isOwn = kb['device_id'] == await _getDeviceId();
          
          allKbs.add({
            ...kb,
            'location': 'server',
            'is_own': isOwn,
            'can_download': !isOwn,
          });
        }
      } catch (e) {
        print('Error loading server knowledge bases: $e');
      }
    }
    
    // 获取已同步的知识库
    if (includeSynced && AppConfig.serverMode == 'multiagent') {
      try {
        final syncedKbs = await _remoteService.getSyncedKnowledgeBases();
        for (final kb in syncedKbs) {
          allKbs.add({
            ...kb,
            'location': 'synced',
            'is_synced': true,
          });
        }
      } catch (e) {
        print('Error loading synced knowledge bases: $e');
      }
    }
    
    return allKbs;
  }

  // 创建知识库（本地或服务器）
  Future<Map<String, dynamic>> createKnowledgeBase({
    required String name,
    String? description,
    required bool isLocal,
  }) async {
    if (isLocal) {
      return await _localService.createLocalKnowledgeBase(
        name: name,
        description: description,
      );
    } else {
      return await _remoteService.createKnowledgeBase(name, description);
    }
  }

  // 添加文档
  Future<void> addDocument({
    required String kbId,
    required String content,
    String? title,
    Map<String, dynamic>? metadata,
    required bool isLocal,
  }) async {
    if (isLocal) {
      await _localService.addDocument(
        kbId: kbId,
        content: content,
        title: title,
        metadata: metadata,
      );
    } else {
      await _remoteService.addDocument(
        kbId,
        content,
        metadata: metadata,
      );
    }
  }

  // 上传文档文件
  Future<void> uploadDocument({
    required String kbId,
    required String filePath,
    required bool isLocal,
  }) async {
    if (isLocal) {
      await _localService.addDocumentFromFile(
        kbId: kbId,
        filePath: filePath,
      );
    } else {
      await _remoteService.uploadDocument(kbId, filePath);
    }
  }

  // 搜索知识库
  Future<List<Map<String, dynamic>>> searchKnowledgeBase({
    required String kbId,
    required String query,
    required bool isLocal,
    int limit = 10,
  }) async {
    if (isLocal) {
      return await _localService.searchLocalKnowledgeBase(
        kbId: kbId,
        query: query,
        limit: limit,
      );
    } else {
      return await _remoteService.searchDocuments(
        kbId,
        query,
        limit: limit,
      );
    }
  }

  // 同步本地知识库到服务器
  Future<Map<String, dynamic>> syncToServer(String localKbId) async {
    if (AppConfig.serverMode != 'multiagent') {
      throw Exception('Server mode must be multiagent for sync');
    }
    
    // 获取本地知识库
    final localKbs = await _localService.getLocalKnowledgeBases();
    final localKb = localKbs.firstWhere(
      (kb) => kb['id'] == localKbId,
      orElse: () => throw Exception('Local knowledge base not found'),
    );
    
    // 创建服务器知识库
    final serverKb = await _remoteService.createKnowledgeBase(
      localKb['name'],
      localKb['description'],
    );
    
    // 获取本地文档
    final documents = await _localService.getDocuments(localKbId);
    
    // 上传每个文档
    int uploaded = 0;
    for (final doc in documents) {
      try {
        await _remoteService.addDocument(
          serverKb['id'],
          doc['content'],
          metadata: doc['metadata'] != null 
              ? Map<String, dynamic>.from(doc['metadata']) 
              : null,
        );
        uploaded++;
      } catch (e) {
        print('Error uploading document: $e');
      }
    }
    
    // 标记为已同步
    if (uploaded > 0) {
      await _localService.publishToServer(
        kbId: localKbId,
        serverUrl: AppConfig.multiAgentServer,
      );
    }
    
    return {
      'success': true,
      'server_kb_id': serverKb['id'],
      'documents_uploaded': uploaded,
      'total_documents': documents.length,
    };
  }

  // 从服务器下载知识库
  Future<Map<String, dynamic>> downloadFromServer(String serverKbId) async {
    if (AppConfig.serverMode != 'multiagent') {
      throw Exception('Server mode must be multiagent for sync');
    }
    
    // 获取服务器知识库信息
    final serverKbs = await _remoteService.getKnowledgeBases();
    final serverKb = serverKbs.firstWhere(
      (kb) => kb['id'] == serverKbId,
      orElse: () => throw Exception('Server knowledge base not found'),
    );
    
    // 创建本地知识库
    final localKb = await _localService.createLocalKnowledgeBase(
      name: '${serverKb['name']} (Downloaded)',
      description: serverKb['description'] ?? 'Downloaded from server',
    );
    
    // 获取服务器文档
    final documents = await _remoteService.getDocuments(serverKbId);
    
    // 下载每个文档
    int downloaded = 0;
    for (final doc in documents) {
      try {
        await _localService.addDocument(
          kbId: localKb['id'],
          content: doc['content'] ?? doc['content_preview'] ?? '',
          title: doc['title'],
          metadata: doc['metadata'],
        );
        downloaded++;
      } catch (e) {
        print('Error downloading document: $e');
      }
    }
    
    return {
      'success': true,
      'local_kb_id': localKb['id'],
      'documents_downloaded': downloaded,
      'total_documents': documents.length,
    };
  }

  // 删除知识库
  Future<void> deleteKnowledgeBase({
    required String kbId,
    required bool isLocal,
  }) async {
    if (isLocal) {
      await _localService.deleteKnowledgeBase(kbId);
    } else {
      await _remoteService.deleteKnowledgeBase(kbId);
    }
  }

  // 获取设备ID
  Future<String> _getDeviceId() async {
    // 生成或获取设备唯一ID
    // 这里需要实现持久化存储
    return Platform.operatingSystem + '_' + Platform.localHostname;
  }

  // 获取统计信息
  Future<Map<String, dynamic>> getStatistics() async {
    final localStats = await _localService.getStatistics();
    
    Map<String, dynamic> serverStats = {};
    if (AppConfig.serverMode == 'multiagent') {
      try {
        final serverKbs = await _remoteService.getKnowledgeBases();
        serverStats = {
          'server_kb_count': serverKbs.length,
        };
      } catch (e) {
        serverStats = {'server_kb_count': 0};
      }
    }
    
    return {
      ...localStats,
      ...serverStats,
      'total_kb_count': (localStats['local_kb_count'] ?? 0) + 
                        (serverStats['server_kb_count'] ?? 0),
    };
  }
}
