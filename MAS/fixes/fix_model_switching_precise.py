"""
修复Flutter客户端模型切换问题（更精确版本）

问题：
1. Local模式下切换模型后出现"request failed, server issue"
2. Internet模式下点击model selector后退出会黑屏

根本原因：
1. setter.dart中的setModalState可能在加载时为null
2. 对话框关闭后仍然尝试调用setState
3. Internet模式下的特殊处理导致流程提前返回
"""

import os
import re
import shutil
from datetime import datetime

PROJECT_ROOT = r"D:\Workspace\Python_Workspace\AIagent-dev\MAS"
MASGUI_DIR = os.path.join(PROJECT_ROOT, "masgui", "lib")

def fix_setter_dart_null_check():
    """修复setter.dart中的null检查问题"""
    file_path = os.path.join(MASGUI_DIR, "worker", "setter.dart")
    
    # 备份
    backup_path = file_path + ".bak"
    if not os.path.exists(backup_path):
        shutil.copy2(file_path, backup_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找并修复Internet模式的处理
    # 1. 修复setModalState可能为null的问题
    content = re.sub(
        r'setModalState!\(\(\) \{\}\);',
        'if (setModalState != null) setModalState!(() {});',
        content
    )
    
    # 2. 确保在dialog关闭后不再调用setState
    content = re.sub(
        r'(void load\(\) async \{)',
        r'\1\n    if (!isMounted) return;',
        content
    )
    
    # 3. 修复Internet模式下的返回逻辑
    # 找到Internet模式的代码块
    pattern = r'(if \(AppModeManager\.isInternetMode\) \{[^}]+loaded = true;\s*)(setModalState!\(\(\) \{\}\);)(.*?return; // 重要：Internet模式不执行后续代码\s*\})'
    replacement = r'\1if (setModalState != null) {\n          setModalState!(() {});\n        }\3'
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 修复 setter.dart null检查完成")

def fix_main_dart_model_selector():
    """修复main.dart中的模型选择器问题"""
    file_path = os.path.join(MASGUI_DIR, "main.dart")
    
    # 备份
    backup_path = file_path + ".bak"
    if not os.path.exists(backup_path):
        shutil.copy2(file_path, backup_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复模型选择器的安全检查
    # 查找Widget selector的定义
    pattern = r'(Widget selector = InkWell\(\s*onTap: !useModel\s*\? \(\) \{)'
    replacement = r'''\1
                // 添加更严格的安全检查
                if (!mounted) {
                  print('[Model Selector] Widget not mounted, skipping');
                  return;
                }'''
    
    content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 修复 main.dart 模型选择器完成")

def add_debug_logs():
    """添加调试日志以追踪问题"""
    setter_path = os.path.join(MASGUI_DIR, "worker", "setter.dart")
    
    with open(setter_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在关键位置添加调试日志
    # 1. load函数开始
    content = re.sub(
        r'(void load\(\) async \{)',
        r'''\1
    print('[setModel] Starting load, mode: ${AppModeManager.getModeName()}');''',
        content
    )
    
    # 2. Internet模式处理前
    content = re.sub(
        r'(if \(AppModeManager\.isInternetMode\) \{)',
        r'''print('[setModel] Handling Internet mode');
      \1''',
        content
    )
    
    # 3. 对话框关闭时
    content = re.sub(
        r'(}\)\.then\(\(_\) \{)',
        r'''\1
      print('[setModel] Dialog closed');''',
        content
    )
    
    with open(setter_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 添加调试日志完成")

def create_safe_wrapper():
    """创建一个安全的setState包装器"""
    wrapper_file = os.path.join(MASGUI_DIR, "utils", "safe_state.dart")
    
    content = '''/// 安全的setState包装器，防止在widget销毁后调用setState
mixin SafeStateMixin<T extends StatefulWidget> on State<T> {
  bool _mounted = true;
  
  @override
  void dispose() {
    _mounted = false;
    super.dispose();
  }
  
  /// 安全的setState，只有在widget仍然挂载时才执行
  void safeSetState(VoidCallback fn) {
    if (_mounted && mounted) {
      setState(fn);
    }
  }
  
  /// 检查widget是否仍然挂载
  bool get isSafeMounted => _mounted && mounted;
}

/// 对话框专用的安全setState
class DialogStateSetter {
  bool _isActive = true;
  final void Function(VoidCallback fn) _setState;
  
  DialogStateSetter(this._setState);
  
  void call(VoidCallback fn) {
    if (_isActive) {
      _setState(fn);
    }
  }
  
  void dispose() {
    _isActive = false;
  }
}
'''
    
    os.makedirs(os.path.dirname(wrapper_file), exist_ok=True)
    with open(wrapper_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 创建安全setState包装器完成")

def fix_critical_issue():
    """修复最关键的问题 - setModalState可能为null"""
    setter_path = os.path.join(MASGUI_DIR, "worker", "setter.dart")
    
    with open(setter_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 确保在所有使用setModalState的地方都进行null检查
    # 1. 替换所有的 setModalState!(() {}); 为安全版本
    content = re.sub(
        r'setModalState!\(\(\) \{([^}]*)\}\);',
        r'if (setModalState != null) setModalState!(() {\1});',
        content
    )
    
    # 2. 在load函数中早期初始化setModalState的检查
    content = re.sub(
        r'(loaded = true;\s*)(setModalState)',
        r'''\1if (setModalState == null) {
          print('[setModel] Warning: setModalState is null, waiting...');
          await Future.delayed(Duration(milliseconds: 100));
        }
        \2''',
        content
    )
    
    with open(setter_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 修复关键null检查问题完成")

def main():
    print("开始修复Flutter客户端模型切换问题（精确版）...")
    print("-" * 50)
    
    try:
        # 1. 修复null检查
        fix_setter_dart_null_check()
        
        # 2. 修复模型选择器
        fix_main_dart_model_selector()
        
        # 3. 添加调试日志
        add_debug_logs()
        
        # 4. 创建安全包装器
        create_safe_wrapper()
        
        # 5. 修复关键问题
        fix_critical_issue()
        
        print("-" * 50)
        print("✅ 所有修复完成！")
        print("\n修复的关键问题：")
        print("1. setModalState可能为null导致的崩溃")
        print("2. Internet模式下的特殊处理流程")
        print("3. Widget销毁后仍然调用setState的问题")
        print("4. 添加了详细的调试日志")
        print("\n请重新编译并测试！")
        
    except Exception as e:
        print(f"❌ 修复过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
