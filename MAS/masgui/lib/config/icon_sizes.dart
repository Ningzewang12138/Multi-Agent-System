/// 图标大小配置
///
/// 这个文件集中管理应用中所有图标的大小
/// 可以根据需要调整这些值来改变图标大小
class IconSizes {
  // 侧边栏图标
  static const double sidebarIcon = 28.0; // 默认24，可调整为20-28

  // 聊天界面图标
  static const double chatAttachment = 24.0; // 附件按钮图标
  static const double chatSend = 18.0; // 发送按钮图标

  // 知识库界面图标
  static const double knowledgeBaseAvatar = 32.0; // 列表中的头像图标（增大到32）
  static const double knowledgeBaseSmall = 20.0; // 小图标（文档数量等，增大到20）
  static const double knowledgeBaseLarge = 72.0; // 空状态大图标（增大到72）

  // AppBar操作图标
  static const double appBarAction = 24.0; // AppBar中的动作图标（增大到28）

  // 弹出菜单图标
  static const double popupMenuItem = 24.0; // 弹出菜单项图标（增大到24）

  // 对话框图标
  static const double dialogIcon = 24.0; // 对话框中的图标

  // 浮动操作按钮图标
  static const double fab = 28.0; // FloatingActionButton图标（增大到28）

  // 底部导航栏图标
  static const double bottomNav = 24.0; // 底部导航栏图标

  // 错误/空状态图标
  static const double emptyState = 64.0; // 空状态显示的大图标
  static const double errorState = 64.0; // 错误状态显示的大图标

  // 设置界面图标
  static const double settings = 40.0; // 设置项图标

  // 聊天界面中间的logo图标
  static const double chatLogo = 60.0; // 聊天界面空状态时的logo图标（默认44，可调整为30-60）

  // 根据屏幕大小动态调整图标大小的方法
  static double adaptive(double baseSize, double screenWidth) {
    if (screenWidth < 360) {
      return baseSize * 0.85; // 小屏幕缩小15%
    } else if (screenWidth > 600) {
      return baseSize * 1.1; // 大屏幕放大10%
    }
    return baseSize;
  }
}
