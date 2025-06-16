import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/knowledge_base.dart';
import '../services/knowledge_base_service.dart';
import '../services/device_id_service.dart';
import 'knowledge_base_detail_screen.dart';
import 'create_knowledge_base_dialog.dart';
import '../main.dart';  // 导入全局回调
import '../utils/responsive_helper.dart';
import '../config/icon_sizes.dart';
import 'sync/knowledge_sync_screen.dart';

class KnowledgeBaseScreen extends StatefulWidget {
  const KnowledgeBaseScreen({Key? key}) : super(key: key);

  @override
  State<KnowledgeBaseScreen> createState() => _KnowledgeBaseScreenState();
}

class _KnowledgeBaseScreenState extends State<KnowledgeBaseScreen> 
    with SingleTickerProviderStateMixin {
  final KnowledgeBaseService _service = KnowledgeBaseService();
  final DeviceIdService _deviceIdService = DeviceIdService();
  
  late TabController _tabController;
  List<KnowledgeBase> _allKnowledgeBases = [];
  List<KnowledgeBase> _myDrafts = [];
  List<KnowledgeBase> _publishedKnowledgeBases = [];
  bool _isLoading = true;
  String? _error;
  String? _deviceId;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _initializeDevice();
  }

  Future<void> _initializeDevice() async {
    _deviceId = await _deviceIdService.getDeviceId();
    _loadKnowledgeBases();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _service.dispose();
    super.dispose();
  }

  Future<void> _loadKnowledgeBases() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      print('Loading knowledge bases with device ID: $_deviceId');
      
      // 获取所有知识库（包括当前设备的草稿）
      final knowledgeBases = await _service.listKnowledgeBases(
        deviceId: _deviceId,
        showMode: 'all',
      );
      
      print('Loaded ${knowledgeBases.length} knowledge bases');
      
      if (mounted) {
        setState(() {
          _allKnowledgeBases = knowledgeBases;
          
          // 分类知识库
          _myDrafts = knowledgeBases
              .where((kb) => kb.isDraft && kb.deviceId == _deviceId)
              .toList();
          
          _publishedKnowledgeBases = knowledgeBases
              .where((kb) => !kb.isDraft)
              .toList();
          
          // 调试输出
          print('Total KBs: ${_allKnowledgeBases.length}');
          print('My Drafts: ${_myDrafts.length}');
          print('Published: ${_publishedKnowledgeBases.length}');
          for (var kb in knowledgeBases) {
            print('KB: ${kb.name}, isDraft: ${kb.isDraft}, deviceId: ${kb.deviceId}');
          }
          
          _isLoading = false;
        });
      }
    } catch (e) {
      print('Error loading knowledge bases: $e');
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _createKnowledgeBase() async {
    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (context) => const CreateKnowledgeBaseDialog(),
    );

    if (result != null && mounted) {
      try {
        final name = result['name'];
        final description = result['description'];
        
        if (name == null || name.isEmpty) {
          throw Exception('Name is required');
        }
        
        await _service.createKnowledgeBase(
          name,
          description,
        );
        
        await Future.delayed(const Duration(milliseconds: 100));
        
        if (mounted) {
          await _loadKnowledgeBases();
          
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Knowledge base created successfully')),
            );
          }
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to create knowledge base: $e')),
          );
        }
      }
    }
  }

  Future<void> _deleteKnowledgeBase(KnowledgeBase kb) async {
    // 权限检查：只有草稿可以删除
    if (!kb.isDraft || kb.deviceId != _deviceId) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Published knowledge bases can only be deleted through the server admin interface')),
        );
      }
      return;
    }
    
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Knowledge Base'),
        content: Text('Are you sure you want to delete "${kb.name}"? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Theme.of(context).colorScheme.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _service.deleteKnowledgeBase(kb.id);
        _loadKnowledgeBases();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Knowledge base "${kb.name}" deleted')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to delete knowledge base: $e')),
          );
        }
      }
    }
  }

  Future<void> _publishKnowledgeBase(KnowledgeBase kb) async {
    if (_deviceId == null) return;
    
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Publish Knowledge Base'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Do you want to publish "${kb.name}"?'),
            const SizedBox(height: 8),
            const Text(
              'Once published, this knowledge base will be visible to all devices and cannot be reverted to draft status.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Publish'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _service.publishKnowledgeBase(kb.id, _deviceId!);
        await _loadKnowledgeBases();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Knowledge base published successfully')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to publish: $e')),
          );
        }
      }
    }
  }

  Future<void> _renameKnowledgeBase(KnowledgeBase kb) async {
    if (_deviceId == null) return;
    
    final controller = TextEditingController(text: kb.name);
    final newName = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename Knowledge Base'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'New Name',
            hintText: 'Enter new name',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Rename'),
          ),
        ],
      ),
    );

    if (newName != null && newName.isNotEmpty && newName != kb.name) {
      try {
        await _service.renameKnowledgeBase(kb.id, newName, _deviceId!);
        await _loadKnowledgeBases();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Knowledge base renamed successfully')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to rename: $e')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Knowledge Bases'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'All'),
            Tab(text: 'My Drafts'),
            Tab(text: 'Published'),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.sync, size: IconSizes.appBarAction),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const KnowledgeSyncScreen(),
                ),
              ).then((_) {
                _loadKnowledgeBases();
                if (reloadKnowledgeBases != null) {
                  reloadKnowledgeBases!();
                }
              });
            },
            tooltip: 'Sync Knowledge Bases',
          ),
          IconButton(
            icon: Icon(Icons.refresh, size: IconSizes.appBarAction),
            onPressed: _loadKnowledgeBases,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildKnowledgeBaseList(_allKnowledgeBases),
          _buildKnowledgeBaseList(_myDrafts),
          _buildKnowledgeBaseList(_publishedKnowledgeBases),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _createKnowledgeBase,
        tooltip: 'Create Knowledge Base',
        child: Icon(Icons.add, size: IconSizes.fab),
      ),
    );
  }

  Widget _buildKnowledgeBaseList(List<KnowledgeBase> knowledgeBases) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: IconSizes.errorState,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Error loading knowledge bases',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                _error!,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _loadKnowledgeBases,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (knowledgeBases.isEmpty) {
      String message;
      if (_tabController.index == 1) {
        message = 'No draft knowledge bases yet';
      } else if (_tabController.index == 2) {
        message = 'No published knowledge bases yet';
      } else {
        message = 'No knowledge bases yet';
      }
      
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.folder_open,
              size: IconSizes.emptyState,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Create your first knowledge base to get started',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
      );
    }

    final isMobile = ResponsiveHelper.isMobile(context);
    final padding = ResponsiveHelper.getScreenPadding(context);
    
    return RefreshIndicator(
      onRefresh: _loadKnowledgeBases,
      child: isMobile
          ? ListView.builder(
              padding: padding,
              itemCount: knowledgeBases.length,
              itemBuilder: (context, index) => _buildKnowledgeBaseItem(context, knowledgeBases[index]),
            )
          : ResponsiveContainer(
              child: GridView.builder(
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: ResponsiveHelper.getGridColumns(context),
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  childAspectRatio: 3,
                ),
                itemCount: knowledgeBases.length,
                itemBuilder: (context, index) => _buildKnowledgeBaseItem(context, knowledgeBases[index]),
              ),
            ),
    );
  }

  Widget _buildKnowledgeBaseItem(BuildContext context, KnowledgeBase kb) {
    final isMobile = ResponsiveHelper.isMobile(context);
    // 更严格的判断：只有是自己的草稿才显示删除选项
    final isMyDraft = kb.isDraft && kb.deviceId == _deviceId;
    // 是否显示删除选项：只有草稿可以删除
    final canDelete = kb.isDraft && kb.deviceId == _deviceId;
    
    return Card(
      margin: EdgeInsets.symmetric(
        vertical: isMobile ? 4 : 0,
        horizontal: isMobile ? 8 : 0,
      ),
      child: InkWell(
        onTap: () async {
          final result = await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => KnowledgeBaseDetailScreen(
                knowledgeBase: kb.toJson(),
                onUpdate: () {
                  if (mounted) {
                    _loadKnowledgeBases();
                  }
                  
                  if (reloadKnowledgeBases != null) {
                    reloadKnowledgeBases!();
                  }
                },
              ),
            ),
          );
          
          if (result == true && mounted) {
            await _loadKnowledgeBases();
            
            if (reloadKnowledgeBases != null) {
              reloadKnowledgeBases!();
            }
          }
        },
        child: Padding(
          padding: ResponsiveHelper.getCardPadding(context),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: kb.isDraft 
                    ? Theme.of(context).colorScheme.secondaryContainer
                    : Theme.of(context).colorScheme.primaryContainer,
                child: Icon(
                  kb.isDraft ? Icons.edit_document : Icons.folder,
                  color: kb.isDraft 
                      ? Theme.of(context).colorScheme.onSecondaryContainer
                      : Theme.of(context).colorScheme.onPrimaryContainer,
                  size: IconSizes.knowledgeBaseAvatar,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            kb.name,
                            style: Theme.of(context).textTheme.titleMedium,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (kb.isDraft) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Theme.of(context).colorScheme.secondaryContainer,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              'DRAFT',
                              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                color: Theme.of(context).colorScheme.onSecondaryContainer,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    if (kb.description != null && kb.description!.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        kb.description!,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 16,
                      children: [
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.description,
                              size: IconSizes.knowledgeBaseSmall,
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              '${kb.documentCount} docs',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                        if (kb.deviceName != null) ...[
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                Icons.devices,
                                size: IconSizes.knowledgeBaseSmall,
                                color: Theme.of(context).colorScheme.onSurfaceVariant,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                kb.deviceName!,
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                          ),
                        ],
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.access_time,
                              size: IconSizes.knowledgeBaseSmall,
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              DateFormat.yMMMd().format(kb.createdAt),
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              PopupMenuButton<String>(
                onSelected: (value) {
                  switch (value) {
                    case 'publish':
                      _publishKnowledgeBase(kb);
                      break;
                    case 'rename':
                      _renameKnowledgeBase(kb);
                      break;
                    case 'delete':
                      _deleteKnowledgeBase(kb);
                      break;
                  }
                },
                itemBuilder: (context) {
                  // 动态构建菜单项，确保只显示合适的选项
                  final items = <PopupMenuItem<String>>[];
                  
                  if (isMyDraft) {
                    items.add(
                      const PopupMenuItem(
                        value: 'publish',
                        child: Row(
                          children: [
                            Icon(Icons.publish, size: IconSizes.popupMenuItem),
                            SizedBox(width: 8),
                            Text('Publish'),
                          ],
                        ),
                      ),
                    );
                    items.add(
                      const PopupMenuItem(
                        value: 'rename',
                        child: Row(
                          children: [
                            Icon(Icons.edit, size: IconSizes.popupMenuItem),
                            SizedBox(width: 8),
                            Text('Rename'),
                          ],
                        ),
                      ),
                    );
                    items.add(
                      const PopupMenuItem(
                        value: 'delete',
                        child: Row(
                          children: [
                            Icon(Icons.delete, size: IconSizes.popupMenuItem),
                            SizedBox(width: 8),
                            Text('Delete'),
                          ],
                        ),
                      ),
                    );
                  }
                  
                  return items;
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
