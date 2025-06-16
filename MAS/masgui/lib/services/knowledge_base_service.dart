import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';
import '../models/knowledge_base.dart';
import 'device_id_service.dart';

class KnowledgeBaseService {
  final http.Client _client = http.Client();

  void dispose() {
    _client.close();
  }

  Future<List<KnowledgeBase>> listKnowledgeBases({String? deviceId, String? showMode = 'all'}) async {
    try {
      print('Fetching knowledge bases from: ${AppConfig.knowledgeEndpoint}/');
      // 构建查询参数
      final queryParams = <String, String>{};
      if (deviceId != null) {
        queryParams['device_id'] = deviceId;
      }
      if (showMode != null && showMode != 'all') {
        queryParams['show_mode'] = showMode;
      }
      
      final uri = Uri.parse('${AppConfig.knowledgeEndpoint}/')
          .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);
      
      final response = await _client.get(uri);

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

      if (response.statusCode == 200) {
        final dynamic jsonData = json.decode(response.body);
        
        // Check if the response is already a list or wrapped in an object
        List<dynamic> jsonList;
        if (jsonData is List) {
          jsonList = jsonData;
        } else if (jsonData is Map && jsonData.containsKey('data')) {
          jsonList = jsonData['data'] as List;
        } else {
          print('Unexpected response format: ${jsonData.runtimeType}');
          jsonList = [];
        }
        
        return jsonList.map((json) {
          try {
            return KnowledgeBase.fromJson(Map<String, dynamic>.from(json));
          } catch (e) {
            print('Error parsing knowledge base: $json');
            print('Error: $e');
            rethrow;
          }
        }).toList();
      } else {
        print('Failed to load knowledge bases: ${response.statusCode} - ${response.body}');
        throw Exception('Failed to load knowledge bases: ${response.statusCode}');
      }
    } catch (e) {
      print('Error in listKnowledgeBases: $e');
      rethrow;
    }
  }

  Future<KnowledgeBase> createKnowledgeBase(String name, String? description) async {
    try {
      print('Creating knowledge base: name=$name, description=$description');
      print('POST URL: ${AppConfig.knowledgeEndpoint}/');
      
      // 获取设备信息
      final deviceService = DeviceIdService();
      final deviceId = await deviceService.getDeviceId();
      final deviceName = await deviceService.getDeviceName();
      
      // 确保不发送null值
      final requestBody = {
        'name': name,
        'description': description ?? '',  // 如果是null，使用空字符串
        'is_draft': true,  // 默认创建为草稿
        'device_id': deviceId,  // 使用真实的设备ID
        'device_name': deviceName,  // 使用真实的设备名称
      };
      
      print('Request body: ${json.encode(requestBody)}');
      
      final response = await _client.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/'),  // 添加斜杠以避免重定向
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: json.encode(requestBody),
      ).timeout(const Duration(seconds: 30));

      print('Create response status: ${response.statusCode}');
      print('Create response body: ${response.body}');

      if (response.statusCode == 200 || response.statusCode == 201) {
        return KnowledgeBase.fromJson(json.decode(response.body));
      } else {
        // 尝试解析错误信息
        String errorMessage = 'Failed to create knowledge base';
        try {
          final errorData = json.decode(response.body);
          if (errorData is Map && errorData.containsKey('detail')) {
            errorMessage = errorData['detail'];
          }
        } catch (_) {
          errorMessage = '${response.statusCode} - ${response.body}';
        }
        throw Exception(errorMessage);
      }
    } catch (e) {
      print('Error creating knowledge base: $e');
      print('Stack trace: ${StackTrace.current}');
      rethrow;
    }
  }

  Future<void> deleteKnowledgeBase(String id) async {
    final response = await _client.delete(
      Uri.parse('${AppConfig.knowledgeEndpoint}/$id'),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to delete knowledge base');
    }
  }

  Future<Map<String, dynamic>> publishKnowledgeBase(String id, String deviceId) async {
    try {
      print('Publishing knowledge base: id=$id, deviceId=$deviceId');
      
      final response = await _client.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$id/publish'),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: json.encode({
          'device_id': deviceId,
        }),
      ).timeout(const Duration(seconds: 30));

      print('Publish response status: ${response.statusCode}');
      print('Publish response body: ${response.body}');

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        // 尝试解析错误信息
        String errorMessage = 'Failed to publish knowledge base';
        try {
          final errorData = json.decode(response.body);
          if (errorData is Map && errorData.containsKey('detail')) {
            errorMessage = errorData['detail'];
          }
        } catch (_) {
          errorMessage = '${response.statusCode} - ${response.body}';
        }
        throw Exception(errorMessage);
      }
    } catch (e) {
      print('Error publishing knowledge base: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> renameKnowledgeBase(String id, String newName, String deviceId) async {
    try {
      print('Renaming knowledge base: id=$id, newName=$newName, deviceId=$deviceId');
      
      final response = await _client.post(
        Uri.parse('${AppConfig.knowledgeEndpoint}/$id/rename'),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: json.encode({
          'new_name': newName,
          'device_id': deviceId,
        }),
      ).timeout(const Duration(seconds: 30));

      print('Rename response status: ${response.statusCode}');
      print('Rename response body: ${response.body}');

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        // 尝试解析错误信息
        String errorMessage = 'Failed to rename knowledge base';
        try {
          final errorData = json.decode(response.body);
          if (errorData is Map && errorData.containsKey('detail')) {
            errorMessage = errorData['detail'];
          }
        } catch (_) {
          errorMessage = '${response.statusCode} - ${response.body}';
        }
        throw Exception(errorMessage);
      }
    } catch (e) {
      print('Error renaming knowledge base: $e');
      rethrow;
    }
  }
}
