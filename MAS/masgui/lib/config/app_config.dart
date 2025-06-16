// lib/config/app_config.dart

import 'dart:io' show Platform;
import 'app_config_android.dart';

class AppConfig {
  // 服务器模式：'ollama' 或 'multiagent'
  static String serverMode = 'multiagent';
  
  // 多Agent服务器地址 - 改回静态变量
  static String _multiAgentServer = 'http://localhost:8000';
  
  // Getter 和 Setter
  static String get multiAgentServer {
    // 优先使用动态设置的地址
    if (_multiAgentServer != 'http://localhost:8000') {
      return _multiAgentServer;
    }
    
    // 如果是 Android 平台且没有设置，使用 Android 配置
    try {
      if (Platform.isAndroid) {
        return AppConfigAndroid.multiAgentServer;
      }
    } catch (e) {
      // 在某些情况下 Platform 可能不可用
    }
    return _multiAgentServer;
  }
  
  static set multiAgentServer(String value) {
    _multiAgentServer = value;
  }
  
  // API基础URL（用于兼容旧代码）
  static String get apiBaseUrl {
    if (serverMode == 'multiagent') {
      return multiAgentServer;
    }
    // 返回Ollama服务器地址或其他
    return 'http://localhost:11434';
  }
  
  // API端点
  static String get baseUrl => apiBaseUrl;
  static String get modelsEndpoint => '$apiBaseUrl/api/chat/models';
  static String get chatEndpoint => '$apiBaseUrl/api/chat/completions';
  static String get ragEndpoint => '$apiBaseUrl/api/chat/rag/completions';
  static String get knowledgeEndpoint => '$apiBaseUrl/api/knowledge';  // 知识库端点
  
  // 文件上传大小限制（MB）
  static const int maxFileSize = 50;
  
  // 支持的文件类型
  static const List<String> supportedFileTypes = [
    'pdf', 'txt', 'docx', 'doc', 'md', 
    'json', 'csv', 'html', 'xml'
  ];
  
  // 同步相关配置
  static const int syncPort = 8001;  // 设备发现端口
  static const int syncTimeout = 30; // 设备超时时间（秒）
  static const int syncBroadcastInterval = 5; // 广播间隔（秒）
}
