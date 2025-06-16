import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:intl/intl.dart';
import '../services/multi_agent_service.dart';
import '../utils/responsive_helper.dart';
import '../widgets/document_preview_dialog.dart';
import '../widgets/add_document_dialog.dart';
import '../services/knowledge_base_service.dart';
import '../services/device_id_service.dart';

class KnowledgeBaseDetailScreen extends StatefulWidget {
  final Map<String, dynamic> knowledgeBase;
  final VoidCallback? onUpdate;

  const KnowledgeBaseDetailScreen({
    Key? key,
    required this.knowledgeBase,
    this.onUpdate,
  }) : super(key: key);

  @override
  State<KnowledgeBaseDetailScreen> createState() => _KnowledgeBaseDetailScreenState();
}

class _KnowledgeBaseDetailScreenState extends State<KnowledgeBaseDetailScreen> 
    with SingleTickerProviderStateMixin {
  final MultiAgentService _service = MultiAgentService();
  late TabController _tabController;
  
  // 文档列表相关
  List<Map<String, dynamic>> _documents = [];
  bool _isLoadingDocuments = true;
  String? _documentsError;
  int _currentPage = 1;
  final int _pageSize = 20;
  int _totalDocuments = 0;
  
  // 搜索和筛选
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String _selectedFileType = 'all';
  String _sortBy = 'created_at';
  bool _sortAscending = false;
  
  // 选择模式
  bool _selectionMode = false;
  final Set<String> _selectedDocumentIds = {};
  
  // 统计信息
  Map<String, dynamic> _stats = {};
  bool _isLoadingStats = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadDocuments();
    _loadStats();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadDocuments() async {
    setState(() {
      _isLoadingDocuments = true;
      _documentsError = null;
    });

    try {
      final result = await _service.getDocumentsPaginated(
        widget.knowledgeBase['id'],
        page: _currentPage,
        pageSize: _pageSize,
        searchQuery: _searchQuery.isEmpty ? null : _searchQuery,
        fileType: _selectedFileType == 'all' ? null : _selectedFileType,
        sortBy: _sortBy,
        ascending: _sortAscending,
      );

      setState(() {
        _documents = result['documents'] ?? [];
        _totalDocuments = result['total'] ?? 0;
        _isLoadingDocuments = false;
      });
    } catch (e) {
      setState(() {
        _documentsError = e.toString();
        _isLoadingDocuments = false;
      });
    }
  }

  Future<void> _loadStats() async {
    setState(() {
      _isLoadingStats = true;
    });

    try {
      final stats = await _service.getDocumentsStats(widget.knowledgeBase['id']);
      setState(() {
        _stats = stats;
        _isLoadingStats = false;
      });
    } catch (e) {
      print('Error loading stats: $e');
      setState(() {
        _isLoadingStats = false;
      });
    }
  }

  Future<void> _uploadFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'doc', 'docx', 'txt', 'md'],
      allowMultiple: true,
    );

    if (result != null) {
      final totalFiles = result.files.length;
      int successCount = 0;
      
      // 显示进度对话框
      StateSetter? setDialogState;
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => WillPopScope(
          onWillPop: () async => false,
          child: StatefulBuilder(
            builder: (context, setState) {
              setDialogState = setState;
              return AlertDialog(
                title: const Text('Uploading Files'),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    LinearProgressIndicator(
                      value: totalFiles > 0 ? successCount / totalFiles : 0,
                    ),
                    const SizedBox(height: 16),
                    Text('$successCount / $totalFiles files uploaded'),
                  ],
                ),
              );
            },
          ),
        ),
      );

      for (final file in result.files) {
        if (file.path != null) {
          try {
            await _service.uploadDocument(
              widget.knowledgeBase['id'],
              file.path!,
            );
            successCount++;
            // 更新进度对话框
            if (mounted && setDialogState != null) {
              setDialogState!(() {});
            }
          } catch (e) {
            print('Error uploading ${file.name}: $e');
          }
        }
      }

      // 关闭进度对话框
      if (mounted) {
        Navigator.of(context).pop();
      }

      // 刷新文档列表和统计
      await _loadDocuments();
      await _loadStats();
      
      // 调用更新回调
      widget.onUpdate?.call();

      // 显示结果
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Uploaded $successCount of $totalFiles files'),
            backgroundColor: successCount == totalFiles 
                ? Theme.of(context).colorScheme.primary
                : Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }

  Future<void> _addTextDocument() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => const AddDocumentDialog(),
    );

    if (result != null) {
      try {
        await _service.addDocument(
          widget.knowledgeBase['id'],
          result['content'],
          metadata: result['metadata'],
        );
        
        await _loadDocuments();
        await _loadStats();
        widget.onUpdate?.call();
        
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Document added successfully')),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to add document: $e')),
        );
      }
    }
  }

  Future<void> _deleteSelectedDocuments() async {
    if (_selectedDocumentIds.isEmpty) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Documents'),
        content: Text(
          'Are you sure you want to delete ${_selectedDocumentIds.length} document(s)? '
          'This action cannot be undone.',
        ),
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
        await _service.deleteDocuments(
          widget.knowledgeBase['id'],
          _selectedDocumentIds.toList(),
        );
        
        setState(() {
          _selectedDocumentIds.clear();
          _selectionMode = false;
        });
        
        await _loadDocuments();
        await _loadStats();
        widget.onUpdate?.call();
        
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Documents deleted successfully')),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to delete documents: $e')),
        );
      }
    }
  }

  Future<void> _cleanupKnowledgeBase() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cleanup Knowledge Base'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'This will delete ALL documents in this knowledge base!',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text('Total documents to be deleted: $_totalDocuments'),
            const SizedBox(height: 8),
            const Text(
              'This action cannot be undone.',
              style: TextStyle(color: Colors.red),
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
            style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Delete All'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        final result = await _service.cleanupKnowledgeBase(
          widget.knowledgeBase['id'],
          true,
        );
        
        await _loadDocuments();
        await _loadStats();
        widget.onUpdate?.call();
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Deleted ${result['deleted_count'] ?? 0} documents'),
          ),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to cleanup: $e')),
        );
      }
    }
  }

  void _showDocumentPreview(Map<String, dynamic> document) {
    showDialog(
      context: context,
      builder: (context) => DocumentPreviewDialog(
        document: document,
        knowledgeBaseId: widget.knowledgeBase['id'],
      ),
    );
  }

  Widget _buildDocumentsList() {
    if (_isLoadingDocuments) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_documentsError != null) {
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
            Text('Error loading documents: $_documentsError'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadDocuments,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_documents.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.description_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            const Text('No documents yet'),
            const SizedBox(height: 8),
            const Text('Upload files or add text documents to get started'),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        await _loadDocuments();
        await _loadStats();
      },
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _documents.length + 1, // +1 for pagination
        itemBuilder: (context, index) {
          if (index == _documents.length) {
            // Pagination controls
            return _buildPaginationControls();
          }
          
          final doc = _documents[index];
          final isSelected = _selectedDocumentIds.contains(doc['id']);
          
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: _selectionMode
                  ? Checkbox(
                      value: isSelected,
                      onChanged: (bool? value) {
                        setState(() {
                          if (value == true) {
                            _selectedDocumentIds.add(doc['id']);
                          } else {
                            _selectedDocumentIds.remove(doc['id']);
                          }
                        });
                      },
                    )
                  : CircleAvatar(
                      backgroundColor: Theme.of(context).colorScheme.secondaryContainer,
                      child: Icon(
                        _getFileIcon(doc['metadata']?['extension'] ?? 'txt'),
                        color: Theme.of(context).colorScheme.onSecondaryContainer,
                      ),
                    ),
              title: Text(
                // 优先使用 original_filename，其次是 filename
                doc['metadata']?['original_filename'] ?? 
                doc['metadata']?['filename'] ?? 
                'Document ${doc['id'].substring(0, 8)}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (doc['content_preview'] != null)
                    Text(
                      doc['content_preview'],
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(
                        Icons.access_time,
                        size: 12,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        _formatDate(doc['created_at'] ?? doc['metadata']?['added_at']),
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                      const SizedBox(width: 16),
                      if (doc['metadata']?['file_size'] != null) ...[
                        Icon(
                          Icons.storage,
                          size: 12,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          _formatFileSize(doc['metadata']['file_size']),
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                      ],
                    ],
                  ),
                ],
              ),
              trailing: _selectionMode
                  ? null
                  : PopupMenuButton<String>(
                      onSelected: (value) {
                        switch (value) {
                          case 'preview':
                            _showDocumentPreview(doc);
                            break;
                          case 'delete':
                            _deleteDocument(doc);
                            break;
                        }
                      },
                      itemBuilder: (context) => [
                        const PopupMenuItem(
                          value: 'preview',
                          child: Row(
                            children: [
                              Icon(Icons.visibility),
                              SizedBox(width: 8),
                              Text('Preview'),
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
              onTap: _selectionMode
                  ? () {
                      setState(() {
                        if (isSelected) {
                          _selectedDocumentIds.remove(doc['id']);
                        } else {
                          _selectedDocumentIds.add(doc['id']);
                        }
                      });
                    }
                  : () => _showDocumentPreview(doc),
              onLongPress: () {
                if (!_selectionMode) {
                  setState(() {
                    _selectionMode = true;
                    _selectedDocumentIds.add(doc['id']);
                  });
                }
              },
            ),
          );
        },
      ),
    );
  }

  Widget _buildPaginationControls() {
    final totalPages = (_totalDocuments / _pageSize).ceil();
    
    if (totalPages <= 1) return const SizedBox.shrink();
    
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          IconButton(
            onPressed: _currentPage > 1
                ? () {
                    setState(() {
                      _currentPage--;
                    });
                    _loadDocuments();
                  }
                : null,
            icon: const Icon(Icons.chevron_left),
          ),
          const SizedBox(width: 16),
          Text('Page $_currentPage of $totalPages'),
          const SizedBox(width: 16),
          IconButton(
            onPressed: _currentPage < totalPages
                ? () {
                    setState(() {
                      _currentPage++;
                    });
                    _loadDocuments();
                  }
                : null,
            icon: const Icon(Icons.chevron_right),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsTab() {
    if (_isLoadingStats) {
      return const Center(child: CircularProgressIndicator());
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Overview cards
          Row(
            children: [
              Expanded(
                child: _buildStatCard(
                  'Total Documents',
                  (_stats['total_documents'] ?? 0).toString(),
                  Icons.description,
                  Theme.of(context).colorScheme.primary,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildStatCard(
                  'Total Files',
                  (_stats['total_files'] ?? 0).toString(),
                  Icons.folder,
                  Theme.of(context).colorScheme.secondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildStatCard(
                  'Total Size',
                  _formatFileSize(_stats['total_size'] ?? 0),
                  Icons.storage,
                  Theme.of(context).colorScheme.tertiary,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildStatCard(
                  'File Types',
                  (_stats['file_types_count'] ?? 0).toString(),
                  Icons.category,
                  Theme.of(context).colorScheme.error,
                ),
              ),
            ],
          ),
          const SizedBox(height: 32),
          
          // File types breakdown
          if (_stats['file_types'] != null && (_stats['file_types'] as Map).isNotEmpty) ...[
            Text(
              'File Types',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ...(_stats['file_types'] as Map).entries.map((entry) {
              final percentage = (_stats['total_documents'] ?? 1) > 0
                  ? (entry.value / _stats['total_documents'] * 100).toStringAsFixed(1)
                  : '0';
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    Icon(
                      _getFileIcon(entry.key),
                      size: 20,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      entry.key.toUpperCase(),
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const Spacer(),
                    Text(
                      '${entry.value} ($percentage%)',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              );
            }).toList(),
          ],
        ],
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color, size: 24),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSettingsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Knowledge Base Information',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  _buildInfoRow('ID', widget.knowledgeBase['id']),
                  _buildInfoRow('Name', widget.knowledgeBase['name']),
                  if (widget.knowledgeBase['description'] != null)
                    _buildInfoRow('Description', widget.knowledgeBase['description']),
                  _buildInfoRow('Created', _formatDate(widget.knowledgeBase['created_at'])),
                  _buildInfoRow('Documents', '${widget.knowledgeBase['document_count'] ?? 0}'),
                  if (_deviceId != null)
                    _buildInfoRow('Device', widget.knowledgeBase['device_name'] ?? _deviceId!),
                  _buildInfoRow('Status', _isDraft ? 'Draft' : 'Published'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Danger Zone',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: _cleanupKnowledgeBase,
                      icon: const Icon(Icons.cleaning_services),
                      label: const Text('Clean Up (Delete All Documents)'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Theme.of(context).colorScheme.error,
                        side: BorderSide(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteDocument(Map<String, dynamic> document) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Document'),
        content: const Text('Are you sure you want to delete this document?'),
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
        await _service.deleteDocument(
          widget.knowledgeBase['id'],
          document['id'],
        );
        
        await _loadDocuments();
        await _loadStats();
        widget.onUpdate?.call();
        
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Document deleted successfully')),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to delete document: $e')),
        );
      }
    }
  }

  IconData _getFileIcon(String extension) {
    switch (extension.toLowerCase()) {
      case 'pdf':
        return Icons.picture_as_pdf;
      case 'doc':
      case 'docx':
        return Icons.description;
      case 'txt':
        return Icons.text_snippet;
      case 'md':
        return Icons.code;
      default:
        return Icons.insert_drive_file;
    }
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  String _formatDate(String? dateStr) {
    if (dateStr == null) return 'Unknown';
    try {
      final date = DateTime.parse(dateStr);
      return DateFormat.yMMMd().add_jm().format(date);
    } catch (e) {
      return dateStr;
    }
  }

  // 检查是否是草稿
  bool get _isDraft {
    // 从元数据中检查
    final metadata = widget.knowledgeBase['metadata'] as Map<String, dynamic>?;
    if (metadata != null && metadata.containsKey('is_draft')) {
      final draftValue = metadata['is_draft'];
      if (draftValue is bool) return draftValue;
      if (draftValue is int) return draftValue != 0;
    }
    // 从根级别检查
    if (widget.knowledgeBase.containsKey('is_draft')) {
      final draftValue = widget.knowledgeBase['is_draft'];
      if (draftValue is bool) return draftValue;
      if (draftValue is int) return draftValue != 0;
    }
    return false;
  }

  // 获取设备ID
  String? get _deviceId {
    return widget.knowledgeBase['device_id'] ?? 
           (widget.knowledgeBase['metadata'] as Map<String, dynamic>?)?['device_id'];
  }

  // 发布知识库
  Future<void> _publishKnowledgeBase() async {
    final deviceService = DeviceIdService();
    final currentDeviceId = await deviceService.getDeviceId();
    
    // 验证权限
    final creatorDeviceId = (widget.knowledgeBase['metadata'] as Map<String, dynamic>?)?['creator_device_id'] ?? _deviceId;
    if (creatorDeviceId != currentDeviceId) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Only the creator can publish this knowledge base')),
      );
      return;
    }
    
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Publish Knowledge Base'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Do you want to publish "${widget.knowledgeBase['name']}"?'),
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
        final kbService = KnowledgeBaseService();
        await kbService.publishKnowledgeBase(
          widget.knowledgeBase['id'],
          currentDeviceId,
        );
        
        widget.onUpdate?.call();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Knowledge base published successfully')),
          );
          // 返回上一个页面
          Navigator.pop(context, true);
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Expanded(
              child: Text(
                widget.knowledgeBase['name'],
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (_isDraft) ...[   
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.description), text: 'Documents'),
            Tab(icon: Icon(Icons.analytics), text: 'Stats'),
            Tab(icon: Icon(Icons.settings), text: 'Settings'),
          ],
        ),
        actions: [
          if (_isDraft && !_selectionMode && _tabController.index != 1) ...[  // 不在Stats tab显示
            IconButton(
              icon: const Icon(Icons.publish),
              onPressed: _publishKnowledgeBase,
              tooltip: 'Publish Knowledge Base',
            ),
          ],
          if (_selectionMode) ...[
            IconButton(
              icon: const Icon(Icons.select_all),
              onPressed: () {
                setState(() {
                  if (_selectedDocumentIds.length == _documents.length) {
                    _selectedDocumentIds.clear();
                  } else {
                    _selectedDocumentIds.clear();
                    _selectedDocumentIds.addAll(
                      _documents.map((doc) => doc['id'] as String),
                    );
                  }
                });
              },
              tooltip: 'Select All',
            ),
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: _selectedDocumentIds.isNotEmpty
                  ? _deleteSelectedDocuments
                  : null,
              tooltip: 'Delete Selected',
            ),
            IconButton(
              icon: const Icon(Icons.close),
              onPressed: () {
                setState(() {
                  _selectionMode = false;
                  _selectedDocumentIds.clear();
                });
              },
              tooltip: 'Cancel Selection',
            ),
          ] else ...[
            if (_tabController.index == 0) ...[
              IconButton(
                icon: const Icon(Icons.search),
                onPressed: () {
                  showSearch(
                    context: context,
                    delegate: DocumentSearchDelegate(
                      knowledgeBaseId: widget.knowledgeBase['id'],
                      onDocumentSelected: _showDocumentPreview,
                    ),
                  );
                },
                tooltip: 'Search',
              ),
              PopupMenuButton<String>(
                onSelected: (value) {
                  switch (value) {
                    case 'sort_date_asc':
                      setState(() {
                        _sortBy = 'created_at';
                        _sortAscending = true;
                      });
                      _loadDocuments();
                      break;
                    case 'sort_date_desc':
                      setState(() {
                        _sortBy = 'created_at';
                        _sortAscending = false;
                      });
                      _loadDocuments();
                      break;
                    case 'sort_name_asc':
                      setState(() {
                        _sortBy = 'filename';
                        _sortAscending = true;
                      });
                      _loadDocuments();
                      break;
                    case 'sort_name_desc':
                      setState(() {
                        _sortBy = 'filename';
                        _sortAscending = false;
                      });
                      _loadDocuments();
                      break;
                    case 'filter_all':
                      setState(() {
                        _selectedFileType = 'all';
                      });
                      _loadDocuments();
                      break;
                    case 'filter_pdf':
                      setState(() {
                        _selectedFileType = 'pdf';
                      });
                      _loadDocuments();
                      break;
                    case 'filter_doc':
                      setState(() {
                        _selectedFileType = 'doc';
                      });
                      _loadDocuments();
                      break;
                    case 'filter_txt':
                      setState(() {
                        _selectedFileType = 'txt';
                      });
                      _loadDocuments();
                      break;
                  }
                },
                itemBuilder: (context) => [
                  const PopupMenuItem(
                    value: 'sort_date_desc',
                    child: Row(
                      children: [
                        Icon(Icons.arrow_downward),
                        SizedBox(width: 8),
                        Text('Newest First'),
                      ],
                    ),
                  ),
                  const PopupMenuItem(
                    value: 'sort_date_asc',
                    child: Row(
                      children: [
                        Icon(Icons.arrow_upward),
                        SizedBox(width: 8),
                        Text('Oldest First'),
                      ],
                    ),
                  ),
                  const PopupMenuItem(
                    value: 'sort_name_asc',
                    child: Row(
                      children: [
                        Icon(Icons.sort_by_alpha),
                        SizedBox(width: 8),
                        Text('Name A-Z'),
                      ],
                    ),
                  ),
                  const PopupMenuItem(
                    value: 'sort_name_desc',
                    child: Row(
                      children: [
                        Icon(Icons.sort_by_alpha),
                        SizedBox(width: 8),
                        Text('Name Z-A'),
                      ],
                    ),
                  ),
                  const PopupMenuDivider(),
                  PopupMenuItem(
                    value: 'filter_all',
                    child: Row(
                      children: [
                        Icon(
                          _selectedFileType == 'all' ? Icons.check : null,
                        ),
                        const SizedBox(width: 8),
                        const Text('All Files'),
                      ],
                    ),
                  ),
                  PopupMenuItem(
                    value: 'filter_pdf',
                    child: Row(
                      children: [
                        Icon(
                          _selectedFileType == 'pdf' ? Icons.check : null,
                        ),
                        const SizedBox(width: 8),
                        const Text('PDF Only'),
                      ],
                    ),
                  ),
                  PopupMenuItem(
                    value: 'filter_doc',
                    child: Row(
                      children: [
                        Icon(
                          _selectedFileType == 'doc' ? Icons.check : null,
                        ),
                        const SizedBox(width: 8),
                        const Text('DOC/DOCX Only'),
                      ],
                    ),
                  ),
                  PopupMenuItem(
                    value: 'filter_txt',
                    child: Row(
                      children: [
                        Icon(
                          _selectedFileType == 'txt' ? Icons.check : null,
                        ),
                        const SizedBox(width: 8),
                        const Text('TXT Only'),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ],
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildDocumentsList(),
          _buildStatsTab(),
          _buildSettingsTab(),
        ],
      ),
      floatingActionButton: _tabController.index == 0 && !_selectionMode
          ? SpeedDial(
              icon: Icons.add,
              activeIcon: Icons.close,
              children: [
                SpeedDialChild(
                  child: const Icon(Icons.upload_file),
                  label: 'Upload Files',
                  onTap: _uploadFile,
                ),
                SpeedDialChild(
                  child: const Icon(Icons.text_fields),
                  label: 'Add Text',
                  onTap: _addTextDocument,
                ),
              ],
            )
          : null,
    );
  }
}

// SpeedDial widget
class SpeedDial extends StatefulWidget {
  final IconData icon;
  final IconData activeIcon;
  final List<SpeedDialChild> children;

  const SpeedDial({
    Key? key,
    required this.icon,
    required this.activeIcon,
    required this.children,
  }) : super(key: key);

  @override
  State<SpeedDial> createState() => _SpeedDialState();
}

class _SpeedDialState extends State<SpeedDial> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  bool _isOpen = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggle() {
    setState(() {
      _isOpen = !_isOpen;
      if (_isOpen) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        ...widget.children.asMap().entries.map((entry) {
          final index = entry.key;
          final child = entry.value;
          
          return AnimatedOpacity(
            opacity: _isOpen ? 1.0 : 0.0,
            duration: Duration(milliseconds: 200 + (index * 50)),
            child: AnimatedContainer(
              duration: Duration(milliseconds: 200 + (index * 50)),
              transform: Matrix4.translationValues(
                0,
                _isOpen ? 0 : 20.0,
                0,
              ),
              child: Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (child.label != null)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surface,
                          borderRadius: BorderRadius.circular(4),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.2),
                              blurRadius: 4,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Text(
                          child.label!,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    const SizedBox(width: 16),
                    FloatingActionButton.small(
                      heroTag: 'speed_dial_$index',
                      onPressed: () {
                        _toggle();
                        child.onTap?.call();
                      },
                      child: child.child,
                    ),
                  ],
                ),
              ),
            ),
          );
        }).toList().reversed,
        FloatingActionButton(
          onPressed: _toggle,
          child: AnimatedRotation(
            turns: _isOpen ? 0.125 : 0,
            duration: const Duration(milliseconds: 200),
            child: Icon(_isOpen ? widget.activeIcon : widget.icon),
          ),
        ),
      ],
    );
  }
}

class SpeedDialChild {
  final Widget child;
  final String? label;
  final VoidCallback? onTap;

  SpeedDialChild({
    required this.child,
    this.label,
    this.onTap,
  });
}

// Document Search Delegate
class DocumentSearchDelegate extends SearchDelegate<Map<String, dynamic>?> {
  final String knowledgeBaseId;
  final Function(Map<String, dynamic>) onDocumentSelected;
  final MultiAgentService _service = MultiAgentService();

  DocumentSearchDelegate({
    required this.knowledgeBaseId,
    required this.onDocumentSelected,
  });

  @override
  List<Widget> buildActions(BuildContext context) {
    return [
      IconButton(
        icon: const Icon(Icons.clear),
        onPressed: () {
          query = '';
        },
      ),
    ];
  }

  @override
  Widget buildLeading(BuildContext context) {
    return IconButton(
      icon: const Icon(Icons.arrow_back),
      onPressed: () {
        close(context, null);
      },
    );
  }

  @override
  Widget buildResults(BuildContext context) {
    return _buildSearchResults();
  }

  @override
  Widget buildSuggestions(BuildContext context) {
    if (query.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('Enter keywords to search documents'),
          ],
        ),
      );
    }
    return _buildSearchResults();
  }

  Widget _buildSearchResults() {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _service.searchDocuments(knowledgeBaseId, query, limit: 20),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }

        if (snapshot.hasError) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, size: 64, color: Colors.red),
                const SizedBox(height: 16),
                Text('Error: ${snapshot.error}'),
              ],
            ),
          );
        }

        final results = snapshot.data ?? [];

        if (results.isEmpty) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.search_off, size: 64, color: Colors.grey),
                SizedBox(height: 16),
                Text('No documents found'),
              ],
            ),
          );
        }

        return ListView.builder(
          itemCount: results.length,
          itemBuilder: (context, index) {
            final doc = results[index];
            final score = (doc['score'] ?? 0.0);
            
            return ListTile(
              leading: CircleAvatar(
                child: Text('${(score * 100).toInt()}%'),
              ),
              title: Text(
                doc['metadata']?['original_filename'] ?? 
                doc['metadata']?['filename'] ?? 
                'Document ${doc['id'].substring(0, 8)}',
              ),
              subtitle: Text(
                doc['content'],
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              onTap: () {
                close(context, doc);
                onDocumentSelected(doc);
              },
            );
          },
        );
      },
    );
  }
}
