class DefaultConfig {
  // 默认服务器配置
  static const String defaultServerMode = 'multiagent';
  static const String defaultMultiAgentServer = 'http://192.168.1.100:8000';

  // 默认Ollama配置
  static const String defaultOllamaHost = 'http://localhost:11434';

  // 推荐的模型列表
  static const List<String> recommendedModels = [
    'qwen2.5:latest',
    'llama3.2:latest',
    'gemma2:latest',
    'mistral:latest'
  ];

  // 应用信息
  static const String appVersion = '1.0.0';
  static const String appName = 'Baymin';
  static const String appDescription =
      'Multi-Agent Chat Client with RAG Support';

  // 功能开关
  static const bool enableMultipleChats = true;
  static const bool enableSettings = true;
  static const bool enableVoiceMode = true;
  static const bool enableRAG = true;

  // UI配置
  static const bool useDeviceTheme = true;
  static const bool showTips = true;
  static const bool preloadModels = true;
  static const bool generateTitles = true;
}
