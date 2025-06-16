import 'package:flutter/material.dart';
import '../config/icon_sizes.dart';

/// 图标大小调整演示界面
/// 
/// 这个界面展示了如何使用IconSizes配置类来统一管理图标大小
class IconSizesDemoScreen extends StatefulWidget {
  const IconSizesDemoScreen({Key? key}) : super(key: key);

  @override
  State<IconSizesDemoScreen> createState() => _IconSizesDemoScreenState();
}

class _IconSizesDemoScreenState extends State<IconSizesDemoScreen> {
  // 可以在这里添加滑块来动态调整图标大小
  double _sidebarIconSize = IconSizes.sidebarIcon;
  double _appBarIconSize = IconSizes.appBarAction;
  double _knowledgeBaseIconSize = IconSizes.knowledgeBaseAvatar;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Icon Sizes Demo'),
        actions: [
          IconButton(
            icon: Icon(Icons.settings, size: _appBarIconSize),
            onPressed: () {},
          ),
          IconButton(
            icon: Icon(Icons.refresh, size: _appBarIconSize),
            onPressed: () {},
          ),
        ],
      ),
      drawer: Drawer(
        child: ListView(
          children: [
            const DrawerHeader(
              child: Text('图标大小演示'),
            ),
            ListTile(
              leading: Icon(Icons.add, size: _sidebarIconSize),
              title: const Text('新建'),
            ),
            ListTile(
              leading: Icon(Icons.folder, size: _sidebarIconSize),
              title: const Text('文件夹'),
            ),
            ListTile(
              leading: Icon(Icons.settings, size: _sidebarIconSize),
              title: const Text('设置'),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '图标大小配置',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            
            // 侧边栏图标大小调整
            _buildSizeAdjuster(
              '侧边栏图标',
              _sidebarIconSize,
              (value) => setState(() => _sidebarIconSize = value),
              Icon(Icons.menu, size: _sidebarIconSize),
            ),
            
            // AppBar图标大小调整
            _buildSizeAdjuster(
              'AppBar图标',
              _appBarIconSize,
              (value) => setState(() => _appBarIconSize = value),
              Icon(Icons.more_vert, size: _appBarIconSize),
            ),
            
            // 知识库图标大小调整
            _buildSizeAdjuster(
              '知识库头像图标',
              _knowledgeBaseIconSize,
              (value) => setState(() => _knowledgeBaseIconSize = value),
              Icon(Icons.folder, size: _knowledgeBaseIconSize),
            ),
            
            const Divider(height: 32),
            
            // 所有图标尺寸展示
            Text(
              '所有图标尺寸',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            
            _buildIconShowcase('侧边栏图标', Icons.menu, IconSizes.sidebarIcon),
            _buildIconShowcase('聊天附件', Icons.attachment, IconSizes.chatAttachment),
            _buildIconShowcase('聊天发送', Icons.send, IconSizes.chatSend),
            _buildIconShowcase('知识库头像', Icons.folder, IconSizes.knowledgeBaseAvatar),
            _buildIconShowcase('知识库小图标', Icons.description, IconSizes.knowledgeBaseSmall),
            _buildIconShowcase('知识库大图标', Icons.folder_open, IconSizes.knowledgeBaseLarge),
            _buildIconShowcase('AppBar操作', Icons.settings, IconSizes.appBarAction),
            _buildIconShowcase('弹出菜单', Icons.more_vert, IconSizes.popupMenuItem),
            _buildIconShowcase('对话框', Icons.info, IconSizes.dialogIcon),
            _buildIconShowcase('浮动按钮', Icons.add, IconSizes.fab),
            _buildIconShowcase('空状态', Icons.inbox, IconSizes.emptyState),
            _buildIconShowcase('错误状态', Icons.error_outline, IconSizes.errorState),
            
            const SizedBox(height: 32),
            
            // 自适应图标大小演示
            Text(
              '自适应图标大小',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text('屏幕宽度: ${MediaQuery.of(context).size.width.toStringAsFixed(0)}'),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        Column(
                          children: [
                            Icon(
                              Icons.phone_android,
                              size: IconSizes.adaptive(24, MediaQuery.of(context).size.width),
                            ),
                            const Text('自适应大小'),
                          ],
                        ),
                        Column(
                          children: [
                            const Icon(Icons.phone_android, size: 24),
                            const Text('固定大小'),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // 重置所有图标大小
          setState(() {
            _sidebarIconSize = IconSizes.sidebarIcon;
            _appBarIconSize = IconSizes.appBarAction;
            _knowledgeBaseIconSize = IconSizes.knowledgeBaseAvatar;
          });
        },
        child: Icon(Icons.refresh, size: IconSizes.fab),
      ),
    );
  }

  Widget _buildSizeAdjuster(
    String label,
    double currentValue,
    ValueChanged<double> onChanged,
    Widget icon,
  ) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                icon,
                const SizedBox(width: 16),
                Text(label),
                const Spacer(),
                Text('${currentValue.toStringAsFixed(0)}px'),
              ],
            ),
            Slider(
              value: currentValue,
              min: 16,
              max: 48,
              divisions: 32,
              onChanged: onChanged,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildIconShowcase(String label, IconData icon, double size) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          SizedBox(
            width: 48,
            child: Icon(icon, size: size),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Text(label),
          ),
          Text('${size.toStringAsFixed(0)}px',
              style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}
