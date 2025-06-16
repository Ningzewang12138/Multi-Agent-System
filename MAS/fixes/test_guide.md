# Flutter客户端模型切换问题修复测试指南

## 问题描述

1. **Local模式下切换模型后出现"request failed, server issue"**
   - 原因：setModalState在某些情况下为null，导致调用失败

2. **Internet模式下点击model selector后退出会黑屏**
   - 原因：Internet模式的特殊处理导致流程提前返回，但状态管理不当

## 已应用的修复

### 1. setter.dart
- 在所有调用`setModalState!(() {})`的地方添加了null检查
- 使用`safeSetState`包装器防止在widget销毁后调用setState
- 添加了`isMounted`标志来跟踪widget生命周期

### 2. 关键修复
```dart
// 原代码
loaded = true;
setModalState!(() {});

// 修复后
loaded = true;
if (setModalState != null) {
  setModalState!(() {});
}
```

## 测试步骤

### 测试Local模式（Multi-Agent）
1. 启动服务器：`python quickstart.py` 选择4
2. 在手机上启动Flutter应用
3. 进入模式选择，选择Local (Multi-Agent)
4. 点击顶部的模型选择器
5. 选择一个模型（如deepseek-r1:7b）
6. 确认没有错误提示
7. 发送测试消息："你好"
8. 切换到另一个模型，重复测试

### 测试Internet模式
1. 在手机上启动Flutter应用
2. 进入模式选择，选择Internet
3. 点击顶部的模型选择器
4. 选择一个模型（如DeepSeek V3）
5. 点击返回或选择完成后，确认界面正常，没有黑屏
6. 发送测试消息："你好"

### 测试切换模式
1. 从Local模式切换到Internet模式
2. 选择模型并测试
3. 从Internet模式切换回Local模式  
4. 选择模型并测试

## 调试信息

如果仍有问题，请查看调试输出：
- 在Android Studio的Logcat中搜索`[setModel]`
- 查看是否有null相关的错误
- 检查`setModalState is null`的警告

## 如果问题仍然存在

1. 清理Flutter缓存：
   ```bash
   cd masgui
   flutter clean
   flutter pub get
   ```

2. 完全卸载应用后重新安装

3. 检查服务器日志是否有错误

## 预期结果

- ✅ Local模式下切换模型不会出现错误
- ✅ Internet模式下选择模型后不会黑屏
- ✅ 所有模式下都能正常发送和接收消息
- ✅ 模式切换后模型选择正常工作
