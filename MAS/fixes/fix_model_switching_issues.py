"""
修复Flutter客户端模型切换问题
1. Local模式下换模型后出现"request failed, server issue"
2. Internet模式下点击model selector后退出会黑屏
"""

import os
import re
import shutil
from datetime import datetime

# 项目根目录
PROJECT_ROOT = r"D:\Workspace\Python_Workspace\AIagent-dev\MAS"
MASGUI_DIR = os.path.join(PROJECT_ROOT, "masgui", "lib")

# 备份目录
BACKUP_DIR = os.path.join(PROJECT_ROOT, "fixes", f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

def backup_file(file_path):
    """备份文件"""
    if not os.path.exists(file_path):
        return
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    relative_path = os.path.relpath(file_path, PROJECT_ROOT)
    backup_path = os.path.join(BACKUP_DIR, relative_path)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(file_path, backup_path)
    print(f"备份文件: {relative_path}")

def fix_setter_dart():
    """修复setter.dart中的模型选择逻辑"""
    file_path = os.path.join(MASGUI_DIR, "worker", "setter.dart")
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复1: 在setModel函数中添加安全检查
    # 找到setModel函数的开始
    pattern = r'(void setModel\(BuildContext context, Function setState\) \{)'
    replacement = r'''\1
  List<String> models = [];
  List<String> modelsReal = [];
  List<bool> modal = [];
  int usedIndex = -1;
  int oldIndex = -1;
  int addIndex = -1;
  bool loaded = false;
  Function? setModalState;
  bool isMounted = true;  // 添加mounted标志
  
  // 安全的setState包装
  void safeSetState(Function fn) {
    if (isMounted && context.mounted) {
      try {
        setState(fn);
      } catch (e) {
        print('Error in setState: $e');
      }
    }
  }
  
  desktopTitleVisible = false;
  safeSetState(() {});'''
    
    # 替换第一部分
    content = re.sub(pattern, replacement, content, count=1)
    
    # 修复2: 在Internet模式下正确处理模型选择
    # 查找Internet模式的处理部分
    pattern2 = r'if \(AppModeManager\.isInternetMode\) \{[^}]+// Internet模式不执行后续代码\s*\}'
    replacement2 = '''if (AppModeManager.isInternetMode) {
        // Internet模式 - 显示固定的模型列表
        final internetModels = InternetChatService.getAvailableModels();
        for (var m in internetModels) {
          models.add(m['name'] as String);
          modelsReal.add(m['id'] as String);
          modal.add(false); // Internet模型不支持多模态
        }
        // Internet模式不支持添加模型
        addIndex = -1;
        
        // 加载已选择的Internet模型
        final savedModel = prefs?.getString('selected_internet_model');
        if (savedModel != null) {
          for (var i = 0; i < modelsReal.length; i++) {
            if (modelsReal[i] == savedModel) {
              usedIndex = i;
              oldIndex = i;
              break;
            }
          }
        }
        
        // Internet模式直接设置loaded为true，不需要网络请求
        loaded = true;
        if (setModalState != null) {
          setModalState!(() {});
        }
        return; // 重要：Internet模式不执行后续代码
      }'''
    
    content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
    
    # 修复3: 在PopScope的onPopInvokedWithResult中添加安全检查
    pattern3 = r'(onPopInvokedWithResult: \(didPop, result\) async \{)'
    replacement3 = r'''\1
          if (!loaded || !context.mounted) return;
          loaded = false;
          isMounted = false;  // 标记为未挂载'''
    
    content = re.sub(pattern3, replacement3, content)
    
    # 修复4: 替换所有的setState为safeSetState
    content = re.sub(r'(?<!safe)setState\(', 'safeSetState(', content)
    
    # 修复5: 在对话框关闭时设置isMounted为false
    pattern5 = r'(}\)\.then\(\(_\) \{)'
    replacement5 = r'''\1
      // 对话框关闭时设置为未挂载
      isMounted = false;'''
    
    content = re.sub(pattern5, replacement5, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 修复 setter.dart 完成")

def fix_sender_dart():
    """修复sender.dart中的发送逻辑"""
    file_path = os.path.join(MASGUI_DIR, "worker", "sender.dart")
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复Multi-Agent模式下的模型检查
    pattern = r'// 修改检查逻辑\s*if \(AppModeManager\.isMultiAgentMode\)[^}]+\}'
    replacement = '''// 修改检查逻辑
  if (AppModeManager.isMultiAgentMode) {
    // 多Agent模式不需要检查host
    print('Using Multi-Agent mode with model: $model');
  } else if (AppModeManager.isInternetMode) {
    // Internet模式不需要检查host
    print('Using Internet mode with model: $model');
  } else if (host == null) {
    // 只有Ollama模式才需要检查host
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(AppLocalizations.of(context)!.noHostSelected),
        showCloseIcon: true));
    if (onStream != null) {
      onStream("", true);
    }
    return "";
  }'''
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 修复 sender.dart 完成")

def fix_main_dart():
    """修复main.dart中的模型选择器显示逻辑"""
    file_path = os.path.join(MASGUI_DIR, "main.dart")
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复模型选择器的点击逻辑
    pattern = r'(Widget selector = InkWell\(\s*onTap: !useModel\s*\? \(\) \{[^}]+\}\s*: null,)'
    replacement = '''Widget selector = InkWell(
        onTap: !useModel
            ? () {
                // 添加安全检查
                if (!mounted) return;
                
                // Internet模式下也可以选择模型
                if (host == null && AppModeManager.isOllamaMode) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                      content:
                          Text(AppLocalizations.of(context)!.noHostSelected),
                      showCloseIcon: true));
                  return;
                }
                
                // 调用setModel前确保context有效
                if (context.mounted) {
                  setModel(context, setState);
                }
              }
            : null,'''
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 修复 main.dart 完成")

def fix_model_sync_helper():
    """修复ModelSyncHelper的同步逻辑"""
    file_path = os.path.join(MASGUI_DIR, "utils", "model_sync_helper.dart")
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加更好的错误处理
    new_content = '''import '../main.dart';
import '../config/app_mode.dart';

/// 模型同步帮助类，确保模型选择在不同模式间正确同步
class ModelSyncHelper {
  /// 同步模型选择到全局变量
  static void syncModelSelection() {
    if (prefs == null) return;
    
    try {
      if (AppModeManager.isInternetMode) {
        // Internet模式：从selected_internet_model加载
        final internetModel = prefs!.getString('selected_internet_model');
        model = internetModel;
        chatAllowed = internetModel != null;
        multimodal = false; // Internet模式不支持多模态
        print('Loaded Internet model: $model');
      } else if (AppModeManager.isMultiAgentMode) {
        // Multi-Agent模式：从model键加载
        final localModel = prefs!.getString('model');
        model = localModel;
        chatAllowed = localModel != null;
        multimodal = false; // Multi-Agent模式暂不支持多模态检测
        print('Loaded Multi-Agent model: $model');
      } else {
        // Ollama模式：从model键加载
        final localModel = prefs!.getString('model');
        model = localModel;
        chatAllowed = localModel != null;
        multimodal = prefs!.getBool('multimodal') ?? false;
        print('Loaded Ollama model: $model');
      }
    } catch (e) {
      print('Error syncing model selection: $e');
      model = null;
      chatAllowed = false;
      multimodal = false;
    }
  }
  
  /// 保存当前模型选择
  static void saveModelSelection(String? selectedModel) {
    if (prefs == null) return;
    
    try {
      if (selectedModel == null) {
        clearModelSelection();
        return;
      }
      
      if (AppModeManager.isInternetMode) {
        prefs!.setString('selected_internet_model', selectedModel);
        print('Saved Internet model: $selectedModel');
      } else {
        prefs!.setString('model', selectedModel);
        print('Saved Local model: $selectedModel');
      }
      
      // 更新全局变量
      model = selectedModel;
      chatAllowed = true;
    } catch (e) {
      print('Error saving model selection: $e');
    }
  }
  
  /// 清除模型选择
  static void clearModelSelection() {
    if (prefs == null) return;
    
    try {
      if (AppModeManager.isInternetMode) {
        prefs!.remove('selected_internet_model');
      } else {
        prefs!.remove('model');
      }
      
      model = null;
      chatAllowed = false;
      multimodal = false;
      print('Cleared model selection');
    } catch (e) {
      print('Error clearing model selection: $e');
    }
  }
}
'''
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 修复 model_sync_helper.dart 完成")

def main():
    print("开始修复Flutter客户端模型切换问题...")
    print(f"项目目录: {PROJECT_ROOT}")
    print(f"备份目录: {BACKUP_DIR}")
    print("-" * 50)
    
    try:
        # 修复各个文件
        fix_setter_dart()
        fix_sender_dart()
        fix_main_dart()
        fix_model_sync_helper()
        
        print("-" * 50)
        print("✅ 所有修复完成！")
        print("\n请执行以下步骤：")
        print("1. 在Flutter项目目录运行: flutter clean")
        print("2. 运行: flutter pub get")
        print("3. 重新编译并测试应用")
        print("\n修复内容：")
        print("- 添加了mounted状态检查，防止在widget销毁后调用setState")
        print("- 修复了Internet模式下的模型选择逻辑")
        print("- 改进了Multi-Agent模式下的错误处理")
        print("- 增强了模型同步的健壮性")
        
    except Exception as e:
        print(f"❌ 修复过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
