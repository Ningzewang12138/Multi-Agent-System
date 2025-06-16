import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/unified_knowledge_base_service.dart';
import '../services/multi_agent_service.dart';
import '../config/app_config.dart';
import '../utils/responsive_helper.dart';
import 'knowledge_base_detail_screen.dart';
import '../main.dart' show reloadKnowledgeBases;

class UnifiedKnowledgeBaseScreen extends StatefulWidget {
  const UnifiedKnowledgeBaseScreen({Key? key}) : super(key: key);

  @override
  State<UnifiedKnowledgeBaseScreen> createState() => _UnifiedKnowledgeBaseScreenState();
}

class _UnifiedKnowledgeBaseScreenState extends State<UnifiedKnowledgeBaseScreen>
    with SingleTickerProviderStateMixin {
  final UnifiedKnowledgeBaseService _service = UnifiedKnowledgeBaseService();
  late TabController _tabController;
  
  List<Map<String, dynamic>> _allKnowledgeBases = [];
  List<Map<String, dynamic>> _localKnowledgeBases = [];
  List<Map<String, dynamic>> _serverKnowledgeBases = [];
  List<Map<String, dynamic>> _syncedKnowledgeBases = [];
  
  bool _isLoading = true;
  String? _error;
  
  // 排序和筛选
  String _sortBy = 'name';
  bool _ascending = true;
  String _filterType = 'all';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadKnowledgeBases();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadKnowledgeBases() async {
    if (!mounted) return;
    
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final allKbs = await _service.getAllKnowledgeBases();
      
      if (!mounted) return;
      
      setState(() {
        _allKnowledgeBases = allKbs;
        
        // 分类知识库
        _localKnowledgeBases = allKbs
            .where((kb) => kb['location'] == 'local')
            .toList();
            
        _serverKnowledgeBases = allKbs
            .where((kb) => kb['location'] == 'server')
            .toList();
            
        _syncedKnowledgeBases = allKbs
            .where((kb) => kb['is_synced'] == true)
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

  Future<void> _createKnowledgeBase(bool isLocal) async {
    final nameController = TextEditingController();
    final descriptionController = TextEditingController();

    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Create ${isLocal ? "Local" : "Server"} Knowledge Base'),
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
        await _service.createKnowledgeBase(
          name: result['name']!,
          description: result['description'],
          isLocal: isLocal,
        );
        
        await _loadKnowledgeBases();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Knowledge base created')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to create: $e')),
          );
        }
      }
    }
  }

  Future<void> _syncToServer(Map<String, dynamic> kb) async {
    try {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => const AlertDialog(
          content: Row(
            children: [
              CircularProgressIndicator(),
              SizedBox(width: 16),
              Text('Syncing to server...'),
            ],
          ),
        ),
      );

      await _service.syncToServer(kb['id']);
      
      if (mounted) Navigator.pop(context);
      
      await _loadKnowledgeBases();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Successfully synced to server')),
        );
      }
    } catch (e) {
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to sync: $e')),
        );
      }
    }
  }

  Future<void> _downloadFromServer(Map<String, dynamic> kb) async {
    try {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => const AlertDialog(
          content: Row(
            children: [
              CircularProgressIndicator(),
              SizedBox(width: 16),
              Text('Downloading from server...'),
            ],
          ),
        ),
      );

      await _service.downloadFromServer(kb['id']);
      
      if (mounted) Navigator.pop(context);
      
      await _loadKnowledgeBases();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Successfully downloaded')),
        );
      }
    } catch (e) {
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to download: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('All Knowledge Bases'),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(
              icon: const Icon(Icons.phone_android),
              text: 'Local (${_localKnowledgeBases.length})',
            ),
            Tab(
              icon: const Icon(Icons.cloud),
              text: AppConfig.serverMode == 'ollama' 
                  ? 'Ollama (${_serverKnowledgeBases.length})'
                  : 'Server (${_serverKnowledgeBases.length})',
            ),
            Tab(
              icon: const Icon(Icons.sync),
              text: 'Synced (${_syncedKnowledgeBases.length})',
            ),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value.startsWith('sort_')) {
                setState(() {
                  _sortBy = value.substring(5);
                  _ascending = !_ascending;
                });
              } else if (value.startsWith('filter_')) {
                setState(() {
                  _filterType = value.substring(7);
                });
              }
            },
            itemBuilder: (context) => [
              const PopupMenuDivider(),
              const PopupMenuItem(
                value: 'header_sort',
                enabled: false,
                child: Text('Sort By', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
              PopupMenuItem(
                value: 'sort_name',
                child: Row(
                  children: [
                    Icon(_sortBy == 'name' ? Icons.check : null),
                    const SizedBox(width: 8),
                    const Text('Name'),
                  ],
                ),
              ),
              PopupMenuItem(
                value: 'sort_date',
                child: Row(
                  children: [
                    Icon(_sortBy == 'date' ? Icons.check : null),
                    const SizedBox(width: 8),
                    const Text('Date'),
                  ],
                ),
              ),
              PopupMenuItem(
                value: 'sort_size',
                child: Row(
                  children: [
                    Icon(_sortBy == 'size' ? Icons.check : null),
                    const SizedBox(width: 8),
                    const Text('Size'),
                  ],
                ),
              ),
            ],
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
                    _buildKnowledgeBaseList(_localKnowledgeBases, isLocal: true),
                    _buildKnowledgeBaseList(_serverKnowledgeBases, isLocal: false),
                    _buildKnowledgeBaseList(_syncedKnowledgeBases, isSynced: true),
                  ],
                ),
      floatingActionButton: _buildFloatingActionButton(),
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

  Widget _buildKnowledgeBaseList(
    List<Map<String, dynamic>> knowledgeBases, {
    bool isLocal = false,
    bool isSynced = false,
  }) {
    if (knowledgeBases.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isLocal
                  ? Icons.phone_android
                  : isSynced
                      ? Icons.sync
                      : Icons.cloud,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              isLocal
                  ? 'No local knowledge bases'
                  : isSynced
                      ? 'No synced knowledge bases'
                      : 'No server knowledge bases',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (!isSynced) ...[
              const SizedBox(height: 8),
              ElevatedButton.icon(
                onPressed: () => _createKnowledgeBase(isLocal),
                icon: const Icon(Icons.add),
                label: Text('Create ${isLocal ? "Local" : "Server"} Knowledge Base'),
              ),
            ],
          ],
        ),
      );
    }

    // Apply sorting
    final sorted = List<Map<String, dynamic>>.from(knowledgeBases);
    sorted.sort((a, b) {
      var aValue = a[_sortBy] ?? '';
      var bValue = b[_sortBy] ?? '';
      
      int result;
      if (aValue is num && bValue is num) {
        result = aValue.compareTo(bValue);
      } else {
        result = aValue.toString().compareTo(bValue.toString());
      }
      
      return _ascending ? result : -result;
    });

    final isMobile = ResponsiveHelper.isMobile(context);
    final padding = ResponsiveHelper.getScreenPadding(context);

    return RefreshIndicator(
      onRefresh: _loadKnowledgeBases,
      child: ListView.builder(
        padding: padding,
        itemCount: sorted.length,
        itemBuilder: (context, index) => _buildKnowledgeBaseItem(
          sorted[index],
          isLocal: isLocal,
          isSynced: isSynced,
        ),
      ),
    );
  }

  Widget _buildKnowledgeBaseItem(
    Map<String, dynamic> kb, {
    bool isLocal = false,
    bool isSynced = false,
  }) {
    final bool canSync = kb['can_sync'] ?? false;
    final bool canDownload = kb['can_download'] ?? false;
    
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
                    backgroundColor: isLocal
                        ? Colors.blue.shade100
                        : isSynced
                            ? Colors.green.shade100
                            : Colors.orange.shade100,
                    child: Icon(
                      isLocal
                          ? Icons.phone_android
                          : isSynced
                              ? Icons.cloud_done
                              : Icons.cloud,
                      color: isLocal
                          ? Colors.blue
                          : isSynced
                              ? Colors.green
                              : Colors.orange,
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
                  PopupMenuButton<String>(
                    onSelected: (value) => _handleAction(value, kb, isLocal),
                    itemBuilder: (context) => [
                      if (canSync)
                        const PopupMenuItem(
                          value: 'sync',
                          child: Row(
                            children: [
                              Icon(Icons.cloud_upload),
                              SizedBox(width: 8),
                              Text('Upload to Server'),
                            ],
                          ),
                        ),
                      if (canDownload)
                        const PopupMenuItem(
                          value: 'download',
                          child: Row(
                            children: [
                              Icon(Icons.cloud_download),
                              SizedBox(width: 8),
                              Text('Download to Local'),
                            ],
                          ),
                        ),
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
                  if (kb['device_name'] != null) ...[
                    const SizedBox(width: 16),
                    Icon(
                      Icons.devices,
                      size: 16,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      kb['device_name'],
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ],
              ),
              if (kb['is_synced'] == true) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.green.shade100,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.sync, size: 14, color: Colors.green.shade700),
                      const SizedBox(width: 4),
                      Text(
                        'Synced',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.green.shade700,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  void _handleAction(String action, Map<String, dynamic> kb, bool isLocal) async {
    switch (action) {
      case 'sync':
        await _syncToServer(kb);
        break;
      case 'download':
        await _downloadFromServer(kb);
        break;
      case 'delete':
        await _deleteKnowledgeBase(kb, isLocal);
        break;
    }
  }

  Future<void> _deleteKnowledgeBase(Map<String, dynamic> kb, bool isLocal) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Knowledge Base'),
        content: Text('Are you sure you want to delete "${kb['name']}"?'),
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
        await _service.deleteKnowledgeBase(
          kbId: kb['id'],
          isLocal: kb['location'] == 'local',
        );
        
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

  String _formatDate(String? dateStr) {
    if (dateStr == null) return 'Unknown';
    try {
      final date = DateTime.parse(dateStr);
      return DateFormat.yMMMd().format(date);
    } catch (_) {
      return dateStr;
    }
  }

  Widget? _buildFloatingActionButton() {
    if (_tabController.index == 0) {
      // Local tab
      return FloatingActionButton.extended(
        onPressed: () => _createKnowledgeBase(true),
        icon: const Icon(Icons.add),
        label: const Text('Create Local'),
      );
    } else if (_tabController.index == 1 && AppConfig.serverMode == 'multiagent') {
      // Server tab
      return FloatingActionButton.extended(
        onPressed: () => _createKnowledgeBase(false),
        icon: const Icon(Icons.add),
        label: const Text('Create Server'),
      );
    }
    return null;
  }
}
