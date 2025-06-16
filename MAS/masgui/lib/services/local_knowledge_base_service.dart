import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as path;
import 'package:uuid/uuid.dart';
import 'local_storage_config.dart';

class LocalKnowledgeBase {
  final String id;
  final String name;
  final String? description;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int documentCount;
  final Map<String, dynamic> metadata;

  LocalKnowledgeBase({
    required this.id,
    required this.name,
    this.description,
    required this.createdAt,
    required this.updatedAt,
    required this.documentCount,
    required this.metadata,
  });

  factory LocalKnowledgeBase.fromJson(Map<String, dynamic> json) {
    return LocalKnowledgeBase(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      documentCount: json['document_count'] ?? 0,
      metadata: json['metadata'] ?? {},
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'document_count': documentCount,
      'metadata': metadata,
    };
  }
}

class LocalKnowledgeBaseService {
  static final LocalKnowledgeBaseService _instance = LocalKnowledgeBaseService._internal();
  factory LocalKnowledgeBaseService() => _instance;
  LocalKnowledgeBaseService._internal();

  final _uuid = const Uuid();

  // 获取知识库配置文件路径
  String get _configFilePath => path.join(LocalStorageConfig.configPath, 'knowledge_bases.json');

  // 加载所有本地知识库
  Future<List<LocalKnowledgeBase>> getLocalKnowledgeBases() async {
    try {
      final configFile = File(_configFilePath);
      if (!await configFile.exists()) {
        return [];
      }

      final content = await configFile.readAsString();
      final List<dynamic> jsonList = json.decode(content);
      
      return jsonList.map((json) => LocalKnowledgeBase.fromJson(json)).toList();
    } catch (e) {
      print('Error loading local knowledge bases: $e');
      return [];
    }
  }

  // 创建本地知识库
  Future<LocalKnowledgeBase> createLocalKnowledgeBase(String name, String? description) async {
    final id = _uuid.v4();
    final now = DateTime.now();
    
    final kb = LocalKnowledgeBase(
      id: id,
      name: name,
      description: description,
      createdAt: now,
      updatedAt: now,
      documentCount: 0,
      metadata: {
        'is_local': true,
        'synced': false,
        'device_id': await _getDeviceId(),
      },
    );

    // 创建知识库目录
    final kbDir = Directory(path.join(LocalStorageConfig.knowledgeBasePath, id));
    await kbDir.create(recursive: true);
    
    // 创建文档目录
    final docsDir = Directory(path.join(kbDir.path, 'documents'));
    await docsDir.create();
    
    // 创建索引目录（用于存储向量等）
    final indexDir = Directory(path.join(kbDir.path, 'index'));
    await indexDir.create();
    
    // 保存配置
    await _saveKnowledgeBases();
    
    return kb;
  }

  // 删除本地知识库
  Future<void> deleteLocalKnowledgeBase(String id) async {
    // 删除知识库目录
    final kbDir = Directory(path.join(LocalStorageConfig.knowledgeBasePath, id));
    if (await kbDir.exists()) {
      await kbDir.delete(recursive: true);
    }
    
    // 更新配置
    await _saveKnowledgeBases();
  }

  // 添加文档到本地知识库
  Future<void> addDocument(String kbId, String documentId, String content, Map<String, dynamic> metadata) async {
    final docPath = path.join(LocalStorageConfig.knowledgeBasePath, kbId, 'documents', '$documentId.json');
    final docFile = File(docPath);
    
    await docFile.writeAsString(json.encode({
      'id': documentId,
      'content': content,
      'metadata': metadata,
      'created_at': DateTime.now().toIso8601String(),
    }));
    
    // 更新文档计数
    await _updateDocumentCount(kbId);
  }

  // 获取知识库的所有文档
  Future<List<Map<String, dynamic>>> getDocuments(String kbId) async {
    final docsDir = Directory(path.join(LocalStorageConfig.knowledgeBasePath, kbId, 'documents'));
    if (!await docsDir.exists()) {
      return [];
    }

    final documents = <Map<String, dynamic>>[];
    await for (final file in docsDir.list()) {
      if (file is File && file.path.endsWith('.json')) {
        final content = await file.readAsString();
        documents.add(json.decode(content));
      }
    }
    
    return documents;
  }

  // 标记知识库已同步
  Future<void> markAsSynced(String kbId, String serverKbId) async {
    final kbs = await getLocalKnowledgeBases();
    final kb = kbs.firstWhere((kb) => kb.id == kbId);
    
    kb.metadata['synced'] = true;
    kb.metadata['server_kb_id'] = serverKbId;
    kb.metadata['synced_at'] = DateTime.now().toIso8601String();
    
    await _saveKnowledgeBases();
  }

  // 保存知识库配置
  Future<void> _saveKnowledgeBases() async {
    final kbs = <LocalKnowledgeBase>[];
    
    // 扫描知识库目录
    final kbRootDir = Directory(LocalStorageConfig.knowledgeBasePath);
    if (await kbRootDir.exists()) {
      await for (final dir in kbRootDir.list()) {
        if (dir is Directory) {
          final configFile = File(path.join(dir.path, 'config.json'));
          if (await configFile.exists()) {
            final content = await configFile.readAsString();
            kbs.add(LocalKnowledgeBase.fromJson(json.decode(content)));
          }
        }
      }
    }
    
    // 保存到主配置文件
    final configFile = File(_configFilePath);
    await configFile.parent.create(recursive: true);
    await configFile.writeAsString(
      json.encode(kbs.map((kb) => kb.toJson()).toList()),
    );
  }

  // 更新文档计数
  Future<void> _updateDocumentCount(String kbId) async {
    final docs = await getDocuments(kbId);
    final kbs = await getLocalKnowledgeBases();
    final kb = kbs.firstWhere((kb) => kb.id == kbId);
    
    kb.metadata['document_count'] = docs.length;
    await _saveKnowledgeBases();
  }

  // 获取设备ID
  Future<String> _getDeviceId() async {
    // TODO: 实现持久化的设备ID
    return 'local_device_${DateTime.now().millisecondsSinceEpoch}';
  }
}
