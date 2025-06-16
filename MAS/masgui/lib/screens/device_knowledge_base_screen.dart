import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/multi_agent_service.dart';
import '../services/device_id_service.dart';
import 'knowledge_base_detail_screen.dart';
import '../main.dart' show reloadKnowledgeBases;
import '../config/app_config.dart';
import 'sync/knowledge_sync_screen.dart';

class DeviceKnowledgeBaseScreen extends StatefulWidget {
  const DeviceKnowledgeBaseScreen({Key? key}) : super(key: key);

  @override
  State<DeviceKnowledgeBaseScreen> createState() => _DeviceKnowledgeBaseScreenState();
}

class _DeviceKnowledgeBaseScreenState extends State<DeviceKnowledgeBaseScreen>
    with SingleTickerProviderStateMixin {
  final MultiAgentService _service = MultiAgentService();
  late TabController _tabController;
  List<Map<String, dynamic>> _myDrafts = [];
  List<Map<String, dynamic>> _publicKnowledgeBases = [];
  bool _isLoading = true;
  String? _error;
  String? _deviceId;
  String? _deviceName;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _initializeDevice();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _initializeDevice() async {
    try {
      _deviceId = await DeviceIdService().getDeviceId();
      _deviceName = await DeviceIdService().getDeviceName();
      await _loadKnowledgeBases();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _loadKnowledgeBases() async {
    if (!mounted) return;
    
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // 获取所有知识库（包括草稿和公开的）
      final knowledgeBases = await _service.getKnowledgeBases(deviceId: _deviceId);
      
      if (!mounted) return;
      
      setState(() {
        // 分离草稿和公开的知识库
        _myDrafts = knowledgeBases
            .where((kb) => 
              (kb['metadata']?['is_draft'] == true || kb['is_draft'] == true) &&
              kb['device_id'] == _deviceId
            )
            .toList();
            
        _publicKnowledgeBases = knowledgeBases
            .where((kb) => 
              kb['metadata']?['is_draft'] != true && 
              kb['is_draft'] != true
            )
            .toList();
            
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _createKnowledgeBase() async {
    final nameController = TextEditingController();
    final descriptionController = TextEditingController();

    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Create Knowledge Base'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(
                labelText: 'Name',
                hintText: 'Enter knowledge base name',
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description (optional)',
                hintText: 'Enter description',
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              if (nameController.text.trim().isNotEmpty) {
                Navigator.pop(context, {
                  'name': nameController.text.trim(),
                  'description': descriptionController.text.trim(),
                });
              }
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );

    if (result != null) {
      try {
        print('Creating knowledge base with name: ${result['name']}');
        print('Server URL: ${AppConfig.apiBaseUrl}');
        print('Knowledge endpoint: ${AppConfig.knowledgeEndpoint}');
        
        await _service.createKnowledgeBase(
          result['name']!,
          result['description'],
        );
        await _loadKnowledgeBases();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Knowledge base created')),
          );
        }
      } catch (e) {
        print('Full error details: $e');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to create: $e')),
          );
        }
      }
    }
  }

  Future<void> _publishKnowledgeBase(Map<String, dynamic> kb) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Publish Knowledge Base'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Are you sure you want to publish "${kb['name']}"?'),
            const SizedBox(height: 16),
            const Text(
              'Once published:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text('• It will be visible to all devices'),
            const Text('• All devices can edit the content'),
            const Text('• You cannot unpublish it'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Publish'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (context) => const AlertDialog(
            content: Row(
              children: [
                CircularProgressIndicator(),
                SizedBox(width: 16),
                Text('Publishing...'),
              ],
            ),
          ),
        );

        await _service.publishKnowledgeBase(kb['id']);
        
        // 关闭进度对话框
        if (mounted) Navigator.pop(context);
        
        await _loadKnowledgeBases();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Knowledge base published successfully')),
          );
        }
      } catch (e) {
        if (mounted) {
          Navigator.pop(context); // 关闭进度对话框
          
          String errorMessage = e.toString();
          if (errorMessage.contains('already exists')) {
            // 显示重命名对话框
            _showRenameDialog(kb);
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Failed to publish: $errorMessage')),
            );
          }
        }
      }
    }
  }

  Future<void> _showRenameDialog(Map<String, dynamic> kb) async {
    final controller = TextEditingController(text: kb['name']?.split(' (')[0] ?? '');
    
    final newName = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename Knowledge Base'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('A knowledge base with this name already exists. Please choose a different name:'),
            const SizedBox(height: 16),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'New Name',
                border: OutlineInputBorder(),
              ),
              autofocus: true,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Rename'),
          ),
        ],
      ),
    );

    if (newName != null && newName.isNotEmpty && mounted) {
      try {
        await _service.renameKnowledgeBase(kb['id'], newName);
        await _loadKnowledgeBases();
        
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Knowledge base renamed successfully')),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to rename: $e')),
        );
      }
    }
  }

  Future<void> _deleteKnowledgeBase(Map<String, dynamic> kb) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Knowledge Base'),
        content: Text('Are you sure you want to delete "${kb['name']}"? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _service.deleteKnowledgeBase(kb['id']);
        await _loadKnowledgeBases();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Knowledge base deleted')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to delete: $e')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Knowledge Bases'),
            if (_deviceName != null)
              Text(
                'Device: $_deviceName',
                style: Theme.of(context).textTheme.bodySmall,
              ),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(
              icon: const Icon(Icons.drafts),
              text: 'My Drafts (${_myDrafts.length})',
            ),
            Tab(
              icon: const Icon(Icons.public),
              text: 'Published (${_publicKnowledgeBases.length})',
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => const KnowledgeSyncScreen(),
                ),
              ).then((_) {
                // 返回时刷新
                _loadKnowledgeBases();
              });
            },
            tooltip: 'Publish Drafts',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadKnowledgeBases,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildErrorWidget()
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildKnowledgeBaseList(_myDrafts, isDraft: true),
                    _buildKnowledgeBaseList(_publicKnowledgeBases, isDraft: false),
                  ],
                ),
      floatingActionButton: _tabController.index == 0
          ? FloatingActionButton.extended(
              onPressed: _createKnowledgeBase,
              icon: const Icon(Icons.add),
              label: const Text('Create Draft'),
            )
          : null,
    );
  }

  Widget _buildErrorWidget() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
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

  Widget _buildKnowledgeBaseList(List<Map<String, dynamic>> knowledgeBases, {required bool isDraft}) {
    if (knowledgeBases.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isDraft ? Icons.drafts : Icons.public,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              isDraft ? 'No draft knowledge bases' : 'No published knowledge bases',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (isDraft) ...[
              const SizedBox(height: 8),
              ElevatedButton.icon(
                onPressed: _createKnowledgeBase,
                icon: const Icon(Icons.add),
                label: const Text('Create Your First Draft'),
              ),
            ],
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadKnowledgeBases,
      child: ListView.builder(
        padding: const EdgeInsets.all(8),
        itemCount: knowledgeBases.length,
        itemBuilder: (context, index) => _buildKnowledgeBaseItem(
          knowledgeBases[index],
          isDraft: isDraft,
        ),
      ),
    );
  }

  Widget _buildKnowledgeBaseItem(Map<String, dynamic> kb, {required bool isDraft}) {
    final metadata = kb['metadata'] ?? {};
    final isOwner = metadata['creator_device_id'] == _deviceId;
    
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: InkWell(
        onTap: () async {
          final result = await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => KnowledgeBaseDetailScreen(
                knowledgeBase: kb,
                onUpdate: _loadKnowledgeBases,
              ),
            ),
          );
          
          if (result == true) {
            await _loadKnowledgeBases();
            
            // 调用全局回调
            if (reloadKnowledgeBases != null) {
              reloadKnowledgeBases!();
            }
          }
        },
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    backgroundColor: isDraft
                        ? Colors.orange.shade100
                        : Colors.green.shade100,
                    child: Icon(
                      isDraft ? Icons.drafts : Icons.public,
                      color: isDraft ? Colors.orange : Colors.green,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          kb['name'] ?? 'Unnamed',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        if (kb['description'] != null && kb['description'].toString().isNotEmpty)
                          Text(
                            kb['description'],
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                      ],
                    ),
                  ),
                  if (isDraft || isOwner)
                    PopupMenuButton<String>(
                      onSelected: (value) => _handleAction(value, kb, isDraft),
                      itemBuilder: (context) => [
                        if (isDraft) ...[
                          const PopupMenuItem(
                            value: 'publish',
                            child: Row(
                              children: [
                                Icon(Icons.publish),
                                SizedBox(width: 8),
                                Text('Publish'),
                              ],
                            ),
                          ),
                          const PopupMenuItem(
                            value: 'rename',
                            child: Row(
                              children: [
                                Icon(Icons.edit),
                                SizedBox(width: 8),
                                Text('Rename'),
                              ],
                            ),
                          ),
                        ],
                        if (isOwner || isDraft)
                          const PopupMenuItem(
                            value: 'delete',
                            child: Row(
                              children: [
                                Icon(Icons.delete),
                                SizedBox(width: 8),
                                Text('Delete'),
                              ],
                            ),
                          ),
                      ],
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(
                    Icons.description,
                    size: 16,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${kb['document_count'] ?? 0} documents',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(width: 16),
                  Icon(
                    Icons.access_time,
                    size: 16,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    _formatDate(kb['created_at'] ?? kb['updated_at']),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (!isDraft && metadata['device_name'] != null) ...[
                    const SizedBox(width: 16),
                    Icon(
                      Icons.devices,
                      size: 16,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      metadata['device_name'],
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _handleAction(String action, Map<String, dynamic> kb, bool isDraft) async {
    switch (action) {
      case 'publish':
        await _publishKnowledgeBase(kb);
        break;
      case 'rename':
        await _showRenameDialog(kb);
        break;
      case 'delete':
        await _deleteKnowledgeBase(kb);
        break;
    }
  }

  String _formatDate(String? dateStr) {
    if (dateStr == null) return 'Unknown';
    try {
      final date = DateTime.parse(dateStr);
      return DateFormat.yMMMd().format(date);
    } catch (_) {
      return dateStr;
    }
  }
}
