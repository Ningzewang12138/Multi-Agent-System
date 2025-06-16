# Android APK 构建和测试指南

## 准备工作

### 1. 获取电脑的局域网 IP 地址
```cmd
ipconfig
```
找到您的 IPv4 地址（通常是 192.168.x.x 格式）

### 2. 修改配置文件
编辑 `lib/config/app_config_android.dart`，将 SERVER_IP 改为您的实际 IP 地址：
```dart
static const String SERVER_IP = "192.168.1.100"; // 改为您的 IP
```

### 3. 配置 Windows 防火墙
确保 Windows 防火墙允许端口 8000：
- 打开 Windows 防火墙设置
- 添加入站规则
- 允许端口 8000 的 TCP 连接

### 4. 启动服务器
在服务器目录运行：
```cmd
python -m server.main
```
注意：服务器需要监听 0.0.0.0 而不是 localhost

## 构建 APK

### 方式一：构建调试版 APK（推荐用于测试）
```bash
cd D:\Workspace\Python_Workspace\AIagent-dev\MAS\masgui
flutter build apk --debug
```

APK 文件位置：`build\app\outputs\flutter-apk\app-debug.apk`

### 方式二：构建发布版 APK（需要签名）
```bash
flutter build apk --release
```

## 安装到手机

### 方式一：USB 连接安装
1. 在手机上启用开发者选项和 USB 调试
2. 用 USB 连接手机到电脑
3. 运行：
```bash
flutter install
```

### 方式二：手动安装
1. 将 APK 文件复制到手机
2. 在手机上打开文件管理器
3. 找到 APK 文件并点击安装
4. 可能需要允许"安装未知来源应用"

## 测试多设备场景

1. **Windows 端**：正常运行 Flutter 应用
2. **Android 端**：运行安装的 APK
3. 两个设备会有不同的设备 ID，可以测试：
   - 各自创建草稿知识库
   - 查看对方的草稿是否可见
   - 发布功能是否正常

## 常见问题

### 1. 连接失败
- 确保手机和电脑在同一 WiFi 网络
- 检查 IP 地址是否正确
- 检查防火墙设置
- 确保服务器正在运行

### 2. 网络权限错误
- 确保 AndroidManifest.xml 包含 INTERNET 权限
- 清理并重新构建项目

### 3. 构建失败
- 运行 `flutter doctor` 检查环境
- 确保 Android SDK 已安装
- 尝试 `flutter clean` 后重新构建

## 快速测试命令

使用提供的批处理文件：
```cmd
build_android.bat
```

这将自动执行清理、获取依赖和构建 APK 的步骤。
