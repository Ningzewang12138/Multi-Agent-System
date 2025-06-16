import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import '../config/app_config.dart';
import 'device_id_service.dart';

class MultiAgentService {
  // 单例模式
  static final MultiAgentService _instance = MultiAgentService._internal();
  factory MultiAgentService() => _instance;
  MultiAgentService._internal();

  // 获取可用模型列表
  Future<List<String>> getModels() async {
    try {
      final response = await http.get(
        Uri.parse(AppConfig.modelsEndpoint),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final modelData = List<Map<String, dynamic>>.from(data['data'] ?? []);
        // 提取模型名称列表
        return modelData.map((model) => model['id'] as String).toList();
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
      print('Sending message to: ${AppConfig.chatEndpoint}');
      print('Request body: ${json.encode({
        'messages': messages,
        'stream': stream,
        'model': model,
      })}');

      final response = await http.post(
        Uri.parse(AppConfig.chatEndpoint),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'messages': messages,
          'stream': stream,
          if (model != null) 'model': model,
        }),
      ).timeout(const Duration(seconds: 30));

      print('Chat response status: ${response.statusCode}');
      print('Chat response body: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        throw Exception('Invalid response format');
      }
      throw Exception('Failed to send message: ${response.statusCode} - ${response.body}');
    } catch (e) {
      print('Error sending message: $e');
      print('Stack trace: ${StackTrace.current}');
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
        final data = json.decode(response.body);
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        return <String, dynamic>{};
      }
      throw Exception('Failed to send RAG message');
    } catch (e) {
      print('Error sending RAG message: $e');
      rethrow;
    }
  }

  // 获取知识库列表（新增功能）
  Future<List<Map<String, dynamic>>> getKnowledgeBases({String? deviceId}) async {
    try {
      final queryParams = <String, String>{};
      if (deviceId != null) {
        queryParams['device_id'] = deviceId;
      }
      
      final uri = Uri.parse(AppConfig.knowledgeEndpoint)
          .replace(queryParameters: queryParams);
      
      final response = await http.get(uri);

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
    String? description,  // 改为可选参数
  ) async {
    try {
      // 获取设备ID和名称
      final deviceId = await _getDeviceId();
      final deviceName = await _getDeviceName();
      
      final requestBody = {
        'name': name,
        'description': description ?? '',  // 确保不发送null
        'is_draft': true,  // 默认创建为草稿
        'device_id': deviceId,
        'device_name': deviceName,
      };
      
      print('Creating KB with: ${json.encode(requestBody)}');
      print('Sending to: ${AppConfig.knowledgeEndpoint}');
      
      // 确保 URL 正确，添加尾部斜杠以避免 307 重定向
      final url = '${AppConfig.knowledgeEndpoint}/';
      print('POST URL: $url');
      
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: json.encode(requestBody),
      ).timeout(const Duration(seconds: 30));

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        return <String, dynamic>{};
      } else {
        // 打印详细错误信息
        print('Error response: ${response.body}');
        throw Exception('Failed to create knowledge base: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('Error creating knowledge base: $e');
      print('Stack trace: ${StackTrace.current}');
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

  // 获取知识库中的文档列表
  Future<List<Map<String, dynamic>>> getDocuments(String knowledgeBaseId) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // 处理不同的响应格式
        if (data is Map && data.containsKey('documents')) {
          return List<Map<String, dynamic>>.from(data['documents']);
        } else if (data is List) {
          return List<Map<String, dynamic>>.from(data);
        }
        return [];
      }
      throw Exception('Failed to load documents');
    } catch (e) {
      print('Error getting documents: $e');
      return [];
    }
  }

  // 删除知识库
  Future<void> deleteKnowledgeBase(String knowledgeBaseId) async {
    try {
      final response = await http.delete(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId'),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to delete knowledge base');
      }
    } catch (e) {
      print('Error deleting knowledge base: $e');
      rethrow;
    }
  }

  // 删除文档
  Future<void> deleteDocument(String knowledgeBaseId, String documentId) async {
    try {
      final response = await http.delete(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents/$documentId'),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to delete document');
      }
    } catch (e) {
      print('Error deleting document: $e');
      rethrow;
    }
  }

  // 上传文档文件
  Future<void> uploadDocument(String knowledgeBaseId, String filePath) async {
    try {
      final file = File(filePath);
      final fileName = filePath.split('/').last.split('\\').last;
      final fileExtension = fileName.split('.').last.toLowerCase();
      
      // 确定MIME类型
      String mimeType;
      switch (fileExtension) {
        case 'pdf':
          mimeType = 'application/pdf';
          break;
        case 'doc':
          mimeType = 'application/msword';
          break;
        case 'docx':
          mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
          break;
        case 'txt':
          mimeType = 'text/plain';
          break;
        case 'md':
          mimeType = 'text/markdown';
          break;
        default:
          mimeType = 'application/octet-stream';
      }

      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents/upload'),
      );
      
      request.files.add(
        await http.MultipartFile.fromPath(
          'file',
          filePath,
          contentType: MediaType.parse(mimeType),
          filename: fileName,
        ),
      );
      
      final response = await request.send();
      final responseBody = await response.stream.bytesToString();
      
      if (response.statusCode != 200) {
        throw Exception('Failed to upload document: $responseBody');
      }
    } catch (e) {
      print('Error uploading document: $e');
      rethrow;
    }
  }

  // 测试连接
  Future<bool> testConnection() async {
    try {
      print('Testing connection to: ${AppConfig.baseUrl}');
      final response = await http.get(
        Uri.parse(AppConfig.baseUrl),
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 5));

      print('Connection test response: ${response.statusCode}');
      print('Response body: ${response.body}');
      return response.statusCode == 200;
    } catch (e) {
      print('Connection test failed: $e');
      return false;
    }
  }

  // 获取文档列表（分页）
  Future<Map<String, dynamic>> getDocumentsPaginated(
    String knowledgeBaseId, {
    int page = 1,
    int pageSize = 20,
    String? searchQuery,
    String? fileType,
    String? sortBy,
    bool? ascending,
  }) async {
    try {
      final queryParams = <String, String>{
        'limit': pageSize.toString(),
        'offset': ((page - 1) * pageSize).toString(),
      };
      
      if (searchQuery != null && searchQuery.isNotEmpty) {
        queryParams['search'] = searchQuery;
      }
      if (fileType != null && fileType != 'all') {
        queryParams['file_type'] = fileType;
      }
      if (sortBy != null) {
        queryParams['sort_by'] = sortBy;
      }
      if (ascending != null) {
        queryParams['ascending'] = ascending.toString();
      }
      
      final uri = Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents')
          .replace(queryParameters: queryParams);
      
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // 如果后端返回的是数组，包装成对象
        if (data is List) {
          return {
            'documents': data.map((doc) => Map<String, dynamic>.from(doc as Map)).toList(),
            'total': data.length,
            'page': page,
            'page_size': pageSize,
          };
        } else if (data is Map && data.containsKey('documents')) {
          // 确保 documents 是正确的类型
          final documents = data['documents'];
          if (documents is List) {
            return {
              'documents': documents.map((doc) => Map<String, dynamic>.from(doc as Map)).toList(),
              'total': data['total'] ?? documents.length,
              'page': page,
              'page_size': pageSize,
            };
          }
        }
        return {
          'documents': <Map<String, dynamic>>[],
          'total': 0,
          'page': page,
          'page_size': pageSize,
        };
      }
      throw Exception('Failed to load documents');
    } catch (e) {
      print('Error getting documents: $e');
      return {
        'documents': <Map<String, dynamic>>[],
        'total': 0,
        'page': page,
        'page_size': pageSize,
      };
    }
  }

  // 批量删除文档
  Future<void> deleteDocuments(
    String knowledgeBaseId,
    List<String> documentIds,
  ) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents/delete'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'document_ids': documentIds,
        }),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to delete documents');
      }
    } catch (e) {
      print('Error deleting documents: $e');
      rethrow;
    }
  }

  // 搜索文档
  Future<List<Map<String, dynamic>>> searchDocuments(
    String knowledgeBaseId,
    String query, {
    int limit = 10,
    Map<String, dynamic>? filter,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/search'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'query': query,
          'limit': limit,
          if (filter != null) 'filter': filter,
        }),
      );

      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(json.decode(response.body));
      }
      throw Exception('Failed to search documents');
    } catch (e) {
      print('Error searching documents: $e');
      return [];
    }
  }

  // 获取知识库统计信息
  Future<Map<String, dynamic>> getKnowledgeBaseStats(String knowledgeBaseId) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/stats'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        return <String, dynamic>{};
      }
      throw Exception('Failed to get stats');
    } catch (e) {
      print('Error getting stats: $e');
      return <String, dynamic>{};
    }
  }

  // 获取文档统计信息
  Future<Map<String, dynamic>> getDocumentsStats(String knowledgeBaseId) async {
    try {
      final url = '${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents/stats';
      print('Getting document stats from: $url');
      
      final response = await http.get(
        Uri.parse(url),
      ).timeout(const Duration(seconds: 10));

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // 确保返回的是 Map<String, dynamic>
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        return <String, dynamic>{};
      } else if (response.statusCode == 404) {
        print('Knowledge base not found: $knowledgeBaseId');
        return <String, dynamic>{};
      } else {
        print('Server returned error: ${response.statusCode} - ${response.body}');
        return <String, dynamic>{};
      }
    } catch (e) {
      print('Error getting document stats: $e');
      return <String, dynamic>{};
    }
  }

  // 清理知识库
  Future<Map<String, dynamic>> cleanupKnowledgeBase(
    String knowledgeBaseId,
    bool deleteAll,
  ) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/cleanup'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'delete_all': deleteAll,
          'confirm': 'CONFIRM',
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // 确保返回的是 Map<String, dynamic>
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        return <String, dynamic>{'success': true};
      }
      throw Exception('Failed to cleanup knowledge base');
    } catch (e) {
      print('Error cleaning up: $e');
      rethrow;
    }
  }



  // 获取已同步的知识库列表
  Future<List<Map<String, dynamic>>> getSyncedKnowledgeBases() async {
    try {
      final url = '${AppConfig.baseUrl}/api/sync/knowledge/synced';
      print('Getting synced KBs from: $url');
      
      final response = await http.get(
        Uri.parse(url),
      );

      print('Synced KBs response status: ${response.statusCode}');
      print('Synced KBs response body: ${response.body}');

      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(json.decode(response.body));
      }
      throw Exception('Failed to load synced knowledge bases: ${response.statusCode}');
    } catch (e) {
      print('Error getting synced knowledge bases: $e');
      return [];
    }
  }

  // 获取文档详情
  Future<Map<String, dynamic>> getDocumentDetail(
    String knowledgeBaseId,
    String documentId,
  ) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents/$documentId'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        return <String, dynamic>{};
      }
      throw Exception('Failed to get document detail');
    } catch (e) {
      print('Error getting document detail: $e');
      rethrow;
    }
  }

  // 获取文档评论
  Future<List<Map<String, dynamic>>> getDocumentComments(
    String knowledgeBaseId,
    String documentId,
  ) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents/$documentId/comments'),
      );

      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(json.decode(response.body));
      }
      return [];
    } catch (e) {
      print('Error getting comments: $e');
      return [];
    }
  }

  // 添加文档评论
  Future<Map<String, dynamic>> addDocumentComment(
    String knowledgeBaseId,
    String documentId,
    String content, {
    String? parentId,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents/$documentId/comments'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'content': content,
          'parent_id': parentId,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        return <String, dynamic>{};
      }
      throw Exception('Failed to add comment');
    } catch (e) {
      print('Error adding comment: $e');
      rethrow;
    }
  }

  // 更新文档标签
  Future<void> updateDocumentTags(
    String knowledgeBaseId,
    String documentId,
    List<String> tags,
  ) async {
    try {
      final response = await http.put(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/documents/$documentId/tags'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'tags': tags,
        }),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to update tags');
      }
    } catch (e) {
      print('Error updating tags: $e');
      rethrow;
    }
  }

  // 获取热门标签
  Future<List<Map<String, dynamic>>> getPopularTags(String knowledgeBaseId) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$knowledgeBaseId/tags/popular'),
      );

      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(json.decode(response.body));
      }
      return [];
    } catch (e) {
      print('Error getting popular tags: $e');
      return [];
    }
  }
  
  // 发布知识库
  Future<Map<String, dynamic>> publishKnowledgeBase(String kbId) async {
    try {
      final deviceId = await _getDeviceId();
      
      final response = await http.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$kbId/publish?device_id=$deviceId'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        return <String, dynamic>{};
      }
      throw Exception('Failed to publish knowledge base: ${response.body}');
    } catch (e) {
      print('Error publishing knowledge base: $e');
      rethrow;
    }
  }
  
  // 重命名知识库
  Future<Map<String, dynamic>> renameKnowledgeBase(String kbId, String newName) async {
    try {
      final deviceId = await _getDeviceId();
      
      final response = await http.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$kbId/rename?device_id=$deviceId&new_name=${Uri.encodeComponent(newName)}'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map) {
          return Map<String, dynamic>.from(data);
        }
        return <String, dynamic>{};
      }
      throw Exception('Failed to rename knowledge base: ${response.body}');
    } catch (e) {
      print('Error renaming knowledge base: $e');
      rethrow;
    }
  }
  
  // 获取设备ID
  Future<String> _getDeviceId() async {
    return await DeviceIdService().getDeviceId();
  }
  
  // 获取设备名称
  Future<String> _getDeviceName() async {
    return await DeviceIdService().getDeviceName();
  }
}
