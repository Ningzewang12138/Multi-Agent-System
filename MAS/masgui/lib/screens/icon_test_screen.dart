import 'package:flutter/material.dart';
import '../config/icon_sizes.dart';

/// 图标测试界面
/// 用于诊断图标是否正常显示
class IconTestScreen extends StatelessWidget {
  const IconTestScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Icon Test'),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh, size: IconSizes.appBarAction),
            onPressed: () {},
          ),
          IconButton(
            icon: Icon(Icons.sync, size: IconSizes.appBarAction),
            onPressed: () {},
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Material Icons Font Test',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            
            // 测试不同颜色的图标
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Icon Color Test:', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        Column(
                          children: [
                            Icon(Icons.folder, size: 32, color: Colors.blue),
                            const Text('Blue'),
                          ],
                        ),
                        Column(
                          children: [
                            Icon(Icons.folder, size: 32, color: Colors.red),
                            const Text('Red'),
                          ],
                        ),
                        Column(
                          children: [
                            Icon(Icons.folder, size: 32, color: Colors.green),
                            const Text('Green'),
                          ],
                        ),
                        Column(
                          children: [
                            Icon(Icons.folder, size: 32),
                            const Text('Default'),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // 知识库图标测试
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Knowledge Base Icons:', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    
                    // 列表项图标
                    ListTile(
                      leading: CircleAvatar(
                        backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                        child: Icon(
                          Icons.folder,
                          color: Theme.of(context).colorScheme.onPrimaryContainer,
                          size: IconSizes.knowledgeBaseAvatar,
                        ),
                      ),
                      title: const Text('Folder Icon in Circle'),
                      subtitle: Text('Size: ${IconSizes.knowledgeBaseAvatar}'),
                    ),
                    
                    // 小图标
                    Row(
                      children: [
                        Icon(Icons.description, size: IconSizes.knowledgeBaseSmall),
                        const SizedBox(width: 8),
                        Text('Document Icon (Size: ${IconSizes.knowledgeBaseSmall})'),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(Icons.devices, size: IconSizes.knowledgeBaseSmall),
                        const SizedBox(width: 8),
                        Text('Device Icon (Size: ${IconSizes.knowledgeBaseSmall})'),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(Icons.access_time, size: IconSizes.knowledgeBaseSmall),
                        const SizedBox(width: 8),
                        Text('Time Icon (Size: ${IconSizes.knowledgeBaseSmall})'),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // 侧边栏图标测试
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Sidebar Icons:', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    ListTile(
                      leading: Icon(Icons.add, size: IconSizes.sidebarIcon),
                      title: Text('Add Icon (Size: ${IconSizes.sidebarIcon})'),
                    ),
                    ListTile(
                      leading: Icon(Icons.chat_bubble_outline, size: IconSizes.sidebarIcon),
                      title: Text('Chat Icon (Size: ${IconSizes.sidebarIcon})'),
                    ),
                    ListTile(
                      leading: Icon(Icons.settings, size: IconSizes.sidebarIcon),
                      title: Text('Settings Icon (Size: ${IconSizes.sidebarIcon})'),
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // 主题测试
            Card(
              color: Theme.of(context).brightness == Brightness.light 
                  ? Colors.black 
                  : Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Contrast Test:',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).brightness == Brightness.light 
                            ? Colors.white 
                            : Colors.black,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(
                          Icons.folder,
                          size: 32,
                          color: Theme.of(context).brightness == Brightness.light 
                              ? Colors.white 
                              : Colors.black,
                        ),
                        const SizedBox(width: 16),
                        Text(
                          'Icon on opposite background',
                          style: TextStyle(
                            color: Theme.of(context).brightness == Brightness.light 
                                ? Colors.white 
                                : Colors.black,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 32),
            
            // 诊断信息
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Diagnostic Info:', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Text('Theme Brightness: ${Theme.of(context).brightness}'),
                    Text('Primary Color: ${Theme.of(context).colorScheme.primary}'),
                    Text('Background Color: ${Theme.of(context).colorScheme.background}'),
                    Text('Icon Theme Color: ${Theme.of(context).iconTheme.color}'),
                    const SizedBox(height: 8),
                    const Text('If you cannot see any icons above, the Material Icons font may not be loaded correctly.'),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        child: Icon(Icons.add, size: IconSizes.fab),
      ),
    );
  }
}
