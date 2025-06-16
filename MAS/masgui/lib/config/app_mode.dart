// lib/config/app_mode.dart

/// 应用模式枚举
enum AppMode {
  /// 本地模式 - 包含 Direct Ollama 和 Multi-Agent Server
  local,
  
  /// 互联网模式 - 连接外部API (DeepSeek, Claude, ChatGPT等)
  internet,
}

/// 本地模式的子模式
enum LocalSubMode {
  /// 直接连接Ollama
  ollama,
  
  /// 连接Multi-Agent Server
  multiAgent,
}

/// 应用模式管理器
class AppModeManager {
  static AppMode currentMode = AppMode.local;
  static LocalSubMode localSubMode = LocalSubMode.multiAgent;
  
  /// 获取当前模式的显示名称
  static String getModeName() {
    switch (currentMode) {
      case AppMode.local:
        return localSubMode == LocalSubMode.ollama ? 'Local (Ollama)' : 'Local (Multi-Agent)';
      case AppMode.internet:
        return 'Internet';
    }
  }
  
  /// 是否为本地模式
  static bool get isLocalMode => currentMode == AppMode.local;
  
  /// 是否为互联网模式
  static bool get isInternetMode => currentMode == AppMode.internet;
  
  /// 是否为Ollama子模式
  static bool get isOllamaMode => 
    currentMode == AppMode.local && localSubMode == LocalSubMode.ollama;
  
  /// 是否为Multi-Agent子模式
  static bool get isMultiAgentMode => 
    currentMode == AppMode.local && localSubMode == LocalSubMode.multiAgent;
}
