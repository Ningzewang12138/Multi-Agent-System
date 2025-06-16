# Flutter客户端图标大小调整指南

## 概述

本项目的Flutter客户端使用了统一的图标大小配置系统，所有图标大小都集中在 `lib/config/icon_sizes.dart` 文件中管理。

## 图标大小配置文件

配置文件位置：`lib/config/icon_sizes.dart`

### 当前配置的图标类型和默认大小：

1. **侧边栏图标** (`sidebarIcon`): 24px
   - 用于侧边栏的菜单项图标

2. **聊天界面图标**
   - 附件按钮 (`chatAttachment`): 24px
   - 发送按钮 (`chatSend`): 18px

3. **知识库界面图标**
   - 列表头像 (`knowledgeBaseAvatar`): 24px
   - 小图标 (`knowledgeBaseSmall`): 16px（文档数量、设备、时间等）
   - 大图标 (`knowledgeBaseLarge`): 64px（空状态显示）

4. **AppBar操作图标** (`appBarAction`): 24px
   - 用于顶部导航栏的操作按钮

5. **弹出菜单图标** (`popupMenuItem`): 20px
   - 用于弹出菜单项

6. **其他图标**
   - 对话框 (`dialogIcon`): 24px
   - 浮动操作按钮 (`fab`): 24px
   - 空状态 (`emptyState`): 64px
   - 错误状态 (`errorState`): 64px
   - 设置界面 (`settings`): 24px

## 如何调整图标大小

### 方法1：修改配置文件（推荐）

直接编辑 `lib/config/icon_sizes.dart` 文件中的常量值：

```dart
class IconSizes {
  // 将侧边栏图标从24px改为28px
  static const double sidebarIcon = 28.0;
  
  // 将知识库小图标从16px改为18px
  static const double knowledgeBaseSmall = 18.0;
}
```

### 方法2：使用自适应大小

对于需要根据屏幕大小动态调整的图标，可以使用 `adaptive` 方法：

```dart
Icon(
  Icons.folder,
  size: IconSizes.adaptive(
    IconSizes.knowledgeBaseAvatar, 
    MediaQuery.of(context).size.width
  ),
)
```

自适应规则：
- 屏幕宽度 < 360px：缩小15%
- 屏幕宽度 > 600px：放大10%
- 其他情况：使用原始大小

### 方法3：创建自定义大小

如果需要为特定场景创建新的图标大小，可以在 `IconSizes` 类中添加新的常量：

```dart
class IconSizes {
  // ... 现有常量 ...
  
  // 添加新的图标大小
  static const double customIcon = 32.0;
}
```

## 已应用图标大小配置的文件

以下文件已经使用了统一的图标大小配置：

1. **main.dart**
   - 侧边栏所有图标
   - AppBar操作图标
   - 知识库选择器图标

2. **knowledge_base_screen.dart**
   - 知识库列表项图标
   - 空状态和错误状态图标
   - 弹出菜单图标
   - AppBar操作图标

## 使用示例

### 基本使用

```dart
import '../config/icon_sizes.dart';

// 使用预定义的图标大小
Icon(Icons.settings, size: IconSizes.sidebarIcon)

// 使用自适应大小
Icon(
  Icons.folder,
  size: IconSizes.adaptive(
    IconSizes.knowledgeBaseAvatar,
    MediaQuery.of(context).size.width
  ),
)
```

### 在ListTile中使用

```dart
ListTile(
  leading: Icon(Icons.add, size: IconSizes.sidebarIcon),
  title: const Text('New Chat'),
)
```

### 在IconButton中使用

```dart
IconButton(
  icon: Icon(Icons.refresh, size: IconSizes.appBarAction),
  onPressed: () {},
)
```

## 测试图标大小

项目中包含了一个演示界面 `icon_sizes_demo_screen.dart`，可以用来：

1. 查看所有预定义的图标大小
2. 动态调整图标大小并实时预览
3. 测试自适应图标大小功能

要使用演示界面，可以在设置页面添加入口或临时替换某个页面进行测试。

## 最佳实践

1. **保持一致性**：相同类型的图标应该使用相同的大小
2. **考虑可访问性**：确保图标不要太小，建议最小16px
3. **响应式设计**：对于跨平台应用，考虑使用自适应大小
4. **测试多种设备**：在不同屏幕尺寸的设备上测试图标显示效果

## 注意事项

1. 修改图标大小后需要重新编译应用
2. 某些Material Design组件对图标大小有默认要求，过大或过小可能影响布局
3. 在调整图标大小时，也要考虑周围元素的间距和对齐
