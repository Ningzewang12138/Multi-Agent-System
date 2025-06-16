# Flutter客户端管理说明

## 概述

Flutter客户端管理工具整合了所有Flutter相关的构建、测试和部署功能，替代了之前分散的批处理文件。

## 使用方法

### 1. 通过快速启动菜单（推荐）

```bash
python quickstart.py
# 选择 9 - Flutter客户端管理
```

### 2. 直接运行Flutter管理器

```bash
# 交互式菜单
python flutter_manager.py

# 或使用Windows批处理
flutter_manager.bat
```

### 3. 命令行模式

```bash
# 构建Debug APK
python flutter_manager.py build

# 构建Release APK
python flutter_manager.py release

# USB调试运行
python flutter_manager.py run

# 清理项目
python flutter_manager.py clean

# 清理旧的批处理文件
python flutter_manager.py cleanup
```

## 功能说明

### 主要功能

1. **环境检查**
   - 检查Flutter SDK安装
   - 检查连接的设备
   - 验证Java环境

2. **构建功能**
   - Debug APK构建（用于测试）
   - Release APK构建（用于发布）
   - 支持Windows、iOS、Web等平台构建

3. **开发调试**
   - USB调试运行
   - 实时热重载
   - 设备连接指导

4. **项目维护**
   - 清理构建缓存
   - 更新服务器配置
   - 项目信息查看

### 文件位置

- 构建的APK文件：
  - Debug: `masgui/build/app/outputs/flutter-apk/app-debug.apk`
  - Release: `masgui/build/app/outputs/flutter-apk/app-release.apk`
  - 复制到根目录: `masgui-debug.apk` 或 `masgui-release.apk`

- 旧的批处理文件：
  - 已移动到: `masgui/old_bat_files/`
  - 确认不需要后可以删除

## 常见问题

### Q: 构建失败怎么办？

1. 运行环境检查：选择 "1. 检查Flutter环境"
2. 清理项目：选择 "5. 清理项目"
3. 重新获取依赖并构建

### Q: 手机无法连接？

1. 确保手机已启用开发者选项
2. 启用USB调试
3. 连接USB线时选择"允许调试"
4. 运行设备检查：选择 "1. 检查Flutter环境"

### Q: 如何更改服务器地址？

1. 选择 "6. 更新服务器配置"
2. 或手动编辑: `masgui/lib/config/app_config.dart`

### Q: 需要安装什么软件？

- Flutter SDK (必需)
- Android Studio (推荐，用于Android开发)
- Java JDK (Android Studio自带)
- Git (用于Flutter包管理)

## 迁移说明

### 从旧批处理文件迁移

| 旧文件 | 新功能 |
|--------|--------|
| build_android.bat | 选择 "2. 构建Android APK (Debug)" |
| build_apk_now.bat | 选择 "2. 构建Android APK (Debug)" |
| run_on_phone.bat | 选择 "4. USB调试运行" |
| install_to_phone.bat | 选择 "4. USB调试运行" |
| build_debug_apk.bat | 选择 "2. 构建Android APK (Debug)" |
| quick_fix_build.bat | 选择 "5. 清理项目" 后重新构建 |

### 清理旧文件

所有旧的批处理文件已移动到 `masgui/old_bat_files/` 目录。确认新工具正常工作后，可以：

```bash
# Windows
rmdir /s masgui\old_bat_files

# 或通过管理工具
python flutter_manager.py
# 选择 "9. 清理旧的批处理文件"
```

## 进阶使用

### 自定义构建参数

编辑 `flutter_manager.py` 中的构建命令，添加自定义参数：

```python
# 例如，添加混淆
cmd = ["flutter", "build", "apk", "--release", "--obfuscate", "--split-debug-info=./debug_info"]
```

### 批量操作

创建批处理脚本进行批量操作：

```batch
@echo off
rem 批量构建所有平台
python flutter_manager.py clean
python flutter_manager.py build
python flutter_manager.py release
```

## 支持

如遇到问题：
1. 查看Flutter日志：`flutter doctor -v`
2. 检查项目状态：`python quickstart.py` 选择 "10"
3. 提交Issue到项目仓库
