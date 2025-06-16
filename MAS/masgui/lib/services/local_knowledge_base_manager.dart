import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as path;
import 'package:uuid/uuid.dart';
import 'local_storage_config.dart';
import '../config/app_config.dart';
import 'package:http/http.dart' as http;

class LocalKnowledgeBaseManager {
  static final LocalKnowledgeBaseManager _instance = LocalKnowledgeBaseManager._internal();
  factory LocalKnowledgeBaseManager() => _instance;
  LocalKnowledgeBaseManager._internal();

  final _uuid = const Uuid();
  
  // 本地ChromaDB服务端口
  static const int localChromaPort = 8100;
  
  // 本地API端点
  String get _localApiBase => 'http://localhost:$localChromaPort';
  
  // 启动本地ChromaDB服务
  Future<bool> startLocalChromaDB() async {
    try {
      // 检查是否已经运行
      final isRunning = await _isChromaDBRunning();
      if (isRunning) {
        print('Local ChromaDB already running');
        return true;
      }
      
      // 创建本地数据目录
      final chromaDir = path.join(LocalStorageConfig.knowledgeBasePath, 'chromadb');
      await Directory(chromaDir).create(recursive: true);
      
      // 启动ChromaDB服务（需要Python环境）
      final process = await Process.start(
        'python',
        [
          '-m',
          'chromadb',
          'run',
          '--path', chromaDir,
          '--port', localChromaPort.toString(),
          '--host', '127.0.0.1',
        ],
        workingDirectory: chromaDir,
      );
      
      // 等待服务启动
      await Future.delayed(const Duration(seconds: 3));
      
      // 验证服务是否启动
      return await _isChromaDBRunning();
    } catch (e) {
      print('Failed to start local ChromaDB: $e');
      return false;
    }
  }
  
  // 检查ChromaDB是否运行
  Future<bool> _isChromaDBRunning() async {
    try {
      final response = await http.get(
        Uri.parse('$_localApiBase/api/v1/heartbeat'),
      ).timeout(const Duration(seconds: 2));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  // 创建本地知识库
  Future<Map<String, dynamic>> createLocalKnowledgeBase(
    String name,
    String? description,
  ) async {
    try {
      // 确保本地ChromaDB运行
      final isRunning = await startLocalChromaDB();
      if (!isRunning) {
        throw Exception('Failed to start local ChromaDB');
      }
      
      final id = _uuid.v4();
      final metadata = {
        'name': name,
        'description': description ?? '',
        'created_at': DateTime.now().toIso8601String(),
        'is_local': true,
        'synced': false,
        'device_id': await _getDeviceId(),
      };
      
      // 创建集合
      final response = await http.post(
        Uri.parse('$_localApiBase/api/v1/collections'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'name': id,
          'metadata': metadata,
        }),
      );
      
      if (response.statusCode == 200 || response.statusCode == 201) {
        // 保存到本地配置
        await _saveLocalKnowledgeBase(id, name, description);
        
        return {
          'id': id,
          'name': name,
          'description': description ?? '',
          'created_at': metadata['created_at'],
          'document_count': 0,
          'is_local': true,
          'synced': false,
        };
      } else {
        throw Exception('Failed to create local collection: ${response.body}');
      }
    } catch (e) {
      print('Error creating local knowledge base: $e');
      rethrow;
    }
  }
  
  // 获取本地知识库列表
  Future<List<Map<String, dynamic>>> getLocalKnowledgeBases() async {
    try {
      final configFile = File(path.join(LocalStorageConfig.configPath, 'local_knowledge_bases.json'));
      if (!await configFile.exists()) {
        return [];
      }
      
      final content = await configFile.readAsString();
      final List<dynamic> kbs = json.decode(content);
      
      return kbs.map((kb) => Map<String, dynamic>.from(kb)).toList();
    } catch (e) {
      print('Error loading local knowledge bases: $e');
      return [];
    }
  }
  
  // 发布本地知识库到服务器
  Future<Map<String, dynamic>> publishToServer(String localKbId) async {
    try {
      // 1. 获取本地知识库信息
      final localKbs = await getLocalKnowledgeBases();
      final localKb = localKbs.firstWhere((kb) => kb['id'] == localKbId);
      
      // 2. 获取本地知识库的所有文档
      final documents = await _getLocalDocuments(localKbId);
      
      // 3. 在服务器创建知识库
      final serverResponse = await http.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'name': localKb['name'],
          'description': localKb['description'] ?? '',
          'device_id': localKb['device_id'],
          'device_name': Platform.localHostname,
        }),
      );
      
      if (serverResponse.statusCode != 200) {
        throw Exception('Failed to create server knowledge base');
      }
      
      final serverKb = json.decode(serverResponse.body);
      
      // 4. 上传文档到服务器
      for (final doc in documents) {
        await _uploadDocumentToServer(serverKb['id'], doc);
      }
      
      // 5. 标记本地知识库为已同步
      await _markAsSynced(localKbId, serverKb['id']);
      
      return {
        'success': true,
        'server_kb_id': serverKb['id'],
        'document_count': documents.length,
      };
    } catch (e) {
      print('Error publishing to server: $e');
      rethrow;
    }
  }
  
  // 保存本地知识库配置
  Future<void> _saveLocalKnowledgeBase(String id, String name, String? description) async {
    final configFile = File(path.join(LocalStorageConfig.configPath, 'local_knowledge_bases.json'));
    
    List<dynamic> kbs = [];
    if (await configFile.exists()) {
      final content = await configFile.readAsString();
      kbs = json.decode(content);
    }
    
    kbs.add({
      'id': id,
      'name': name,
      'description': description ?? '',
      'created_at': DateTime.now().toIso8601String(),
      'document_count': 0,
      'is_local': true,
      'synced': false,
      'device_id': await _getDeviceId(),
    });
    
    await configFile.parent.create(recursive: true);
    await configFile.writeAsString(json.encode(kbs));
  }
  
  // 获取本地文档
  Future<List<Map<String, dynamic>>> _getLocalDocuments(String kbId) async {
    // TODO: 从本地ChromaDB获取文档
    return [];
  }
  
  // 上传文档到服务器
  Future<void> _uploadDocumentToServer(String serverKbId, Map<String, dynamic> doc) async {
    // TODO: 实现文档上传
  }
  
  // 标记为已同步
  Future<void> _markAsSynced(String localKbId, String serverKbId) async {
    final configFile = File(path.join(LocalStorageConfig.configPath, 'local_knowledge_bases.json'));
    
    if (await configFile.exists()) {
      final content = await configFile.readAsString();
      final List<dynamic> kbs = json.decode(content);
      
      for (var kb in kbs) {
        if (kb['id'] == localKbId) {
          kb['synced'] = true;
          kb['server_kb_id'] = serverKbId;
          kb['synced_at'] = DateTime.now().toIso8601String();
          break;
        }
      }
      
      await configFile.writeAsString(json.encode(kbs));
    }
  }
  
  // 获取设备ID
  Future<String> _getDeviceId() async {
    // TODO: 实现持久化的设备ID
    return Platform.localHostname;
  }
}
