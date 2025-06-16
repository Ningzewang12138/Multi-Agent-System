import 'dart:convert';
import 'package:http/http.dart' as http;

/// Internet模式聊天服务，支持多个外部API
class InternetChatService {
  // 硬编码的API密钥 - 请在这里填入您的API密钥
  static const Map<String, String> _hardcodedApiKeys = {
    'deepseek-v3':
        'sk-0f32ae7e4ace4f97b44af431c4437019', // 在这里填入您的DeepSeek API密钥
    'deepseek-r1':
        'sk-0f32ae7e4ace4f97b44af431c4437019', // 在这里填入您的DeepSeek API密钥（通常与v3相同）
    'claude-4-sonnet':
        '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', // 在这里填入您的Claude API密钥
    'chatgpt-4o':
        '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', // 在这里填入您的ChatGPT API密钥
  };
  // API配置
  static const Map<String, Map<String, dynamic>> _apiConfigs = {
    'deepseek-v3': {
      'name': 'DeepSeek V3',
      'baseUrl': 'https://api.deepseek.com/v1',
      'model': 'deepseek-chat',
      'requiresApiKey': true,
    },
    'deepseek-r1': {
      'name': 'DeepSeek R1',
      'baseUrl': 'https://api.deepseek.com/v1',
      'model': 'deepseek-reasoner',
      'requiresApiKey': true,
    },
    'claude-4-sonnet': {
      'name': 'Claude 4 Sonnet',
      'baseUrl': 'https://api.anthropic.com/v1',
      'model': 'claude-3-5-sonnet-20241022',
      'requiresApiKey': true,
      'headerStyle': 'anthropic', // 特殊的请求头格式
    },
    'chatgpt-4o': {
      'name': 'ChatGPT 4o',
      'baseUrl': 'https://api.openai.com/v1',
      'model': 'gpt-4o',
      'requiresApiKey': true,
    },
  };

  /// 获取可用的模型列表
  static List<Map<String, String>> getAvailableModels() {
    return _apiConfigs.entries.map((entry) {
      return {
        'id': entry.key,
        'name': entry.value['name'] as String,
        'requiresApiKey': entry.value['requiresApiKey'].toString(),
      };
    }).toList();
  }

  /// 获取API密钥（优先使用硬编码，否则从存储获取）
  static String getApiKey(String modelId, String? storedKey) {
    // 如果有硬编码的密钥，优先使用
    final hardcodedKey = _hardcodedApiKeys[modelId];
    if (hardcodedKey != null && hardcodedKey.isNotEmpty) {
      return hardcodedKey;
    }
    // 否则使用存储的密钥
    return storedKey ?? '';
  }

  /// 发送聊天消息
  Future<Map<String, dynamic>> sendMessage({
    required String modelId,
    required List<Map<String, String>> messages,
    required String apiKey,
    bool stream = false,
  }) async {
    final config = _apiConfigs[modelId];
    if (config == null) {
      throw Exception('Unknown model: $modelId');
    }

    // 获取实际使用的API密钥
    final actualApiKey = getApiKey(modelId, apiKey);

    if (config['requiresApiKey'] == true && actualApiKey.isEmpty) {
      throw Exception('API key is required for $modelId');
    }

    final url = '${config['baseUrl']}/chat/completions';
    final model = config['model'] as String;

    try {
      // 构建请求体
      final requestBody = {
        'model': model,
        'messages': messages,
        'stream': stream,
      };

      // 构建请求头
      final headers = <String, String>{
        'Content-Type': 'application/json',
      };

      // 根据不同的API设置不同的认证头
      if (config['headerStyle'] == 'anthropic') {
        // Anthropic使用特殊的请求头
        headers['x-api-key'] = actualApiKey;
        headers['anthropic-version'] = '2023-06-01';

        // Anthropic的请求格式略有不同
        requestBody.remove('model');
        requestBody['model'] = model;
        requestBody['max_tokens'] = 4096;
      } else {
        // OpenAI和DeepSeek使用标准的Bearer认证
        headers['Authorization'] = 'Bearer $actualApiKey';
      }

      print('Sending request to $url');
      print('Model: $model');
      print('Messages count: ${messages.length}');

      final response = await http
          .post(
            Uri.parse(url),
            headers: headers,
            body: jsonEncode(requestBody),
          )
          .timeout(const Duration(seconds: 60));

      print('Response status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data;
      } else {
        print('Error response: ${response.body}');
        final error = jsonDecode(response.body);
        throw Exception(
            'API Error (${response.statusCode}): ${error['error']?['message'] ?? error['message'] ?? response.body}');
      }
    } catch (e) {
      print('Error in sendMessage: $e');
      rethrow;
    }
  }

  /// 测试API连接
  Future<bool> testConnection({
    required String modelId,
    required String apiKey,
  }) async {
    try {
      final response = await sendMessage(
        modelId: modelId,
        apiKey: apiKey,
        messages: [
          {'role': 'user', 'content': 'Hi'},
        ],
      );
      return response['choices'] != null;
    } catch (e) {
      print('Connection test failed: $e');
      return false;
    }
  }

  /// 获取模型的API密钥存储键
  static String getApiKeyStorageKey(String modelId) {
    return 'internet_api_key_$modelId';
  }
}
