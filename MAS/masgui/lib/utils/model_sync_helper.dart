import '../main.dart';
import '../config/app_mode.dart';

/// 模型同步帮助类，确保模型选择在不同模式间正确同步
class ModelSyncHelper {
  /// 同步模型选择到全局变量
  static void syncModelSelection() {
    if (prefs == null) return;
    
    if (AppModeManager.isInternetMode) {
      // Internet模式：从selected_internet_model加载
      final internetModel = prefs!.getString('selected_internet_model');
      model = internetModel;
      chatAllowed = internetModel != null;
      multimodal = false; // Internet模式不支持多模态
    } else {
      // Local模式：从model键加载
      final localModel = prefs!.getString('model');
      model = localModel;
      chatAllowed = localModel != null;
      multimodal = prefs!.getBool('multimodal') ?? false;
    }
  }
  
  /// 保存当前模型选择
  static void saveModelSelection(String? selectedModel) {
    if (prefs == null || selectedModel == null) return;
    
    if (AppModeManager.isInternetMode) {
      prefs!.setString('selected_internet_model', selectedModel);
    } else {
      prefs!.setString('model', selectedModel);
    }
    
    // 更新全局变量
    model = selectedModel;
    chatAllowed = true;
  }
  
  /// 清除模型选择
  static void clearModelSelection() {
    if (prefs == null) return;
    
    if (AppModeManager.isInternetMode) {
      prefs!.remove('selected_internet_model');
    } else {
      prefs!.remove('model');
    }
    
    model = null;
    chatAllowed = false;
  }
}
