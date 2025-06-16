# Flutter客户端图标大小调整指南

## 概述

本项目的Flutter客户端使用了统一的图标大小配置系统，所有图标大小都集中在 `lib/config/icon_sizes.dart` 文件中管理。

## 快速调整方法

编辑 `lib/config/icon_sizes.dart` 文件，修改对应的数值即可：

```dart
class IconSizes {
  static const double sidebarIcon = 24.0;      // 侧边栏图标
  static const double chatAttachment = 24.0;   // 聊天附件按钮
  static const double chatSend = 18.0;         // 发送按钮
  static const double knowledgeBaseAvatar = 24.0;  // 知识库头像
  static const double knowledgeBaseSmall = 16.0;   // 知识库小图标
  static const double knowledgeBaseLarge = 64.0;   // 知识库大图标
  static const double appBarAction = 24.0;     // AppBar操作图标
  static const double popupMenuItem = 20.0;    // 弹出菜单图标
  static const double dialogIcon = 24.0;       // 对话框图标
  static const double fab = 24.0;              // 浮动操作按钮
  static const double emptyState = 64.0;       // 空状态图标
  static const double errorState = 64.0;       // 错误状态图标
  static const double settings = 24.0;         // 设置图标
}
```

修改后重新运行应用即可看到效果。
