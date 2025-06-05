class AppConfig {
  // 服务器模式：'ollama' 直连 或 'multiagent' 连接你的服务器
  static String serverMode = 'multiagent';

  // 多Agent服务器地址（修改为你的PC IP）
  static String multiAgentServer = 'http://192.168.1.3:8000';

  // 原始Ollama服务器地址
  static String ollamaServer = 'http://localhost:11434';

  // 获取当前使用的服务器地址
  static String get baseUrl =>
      serverMode == 'multiagent' ? multiAgentServer : ollamaServer;

  // API端点
  static String get chatEndpoint => '$baseUrl/api/chat/completions';
  static String get ragEndpoint => '$baseUrl/api/chat/rag/completions';
  static String get knowledgeEndpoint => '$baseUrl/api/knowledge';
  static String get modelsEndpoint => '$baseUrl/api/chat/models';
}
