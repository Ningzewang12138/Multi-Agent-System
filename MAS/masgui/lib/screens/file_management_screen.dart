import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../services/multi_agent_service.dart';
import 'document_viewer_screen.dart';

class FileManagementScreen extends StatefulWidget {
  final Map<String, dynamic> knowledgeBase;
  final VoidCallback? onUpdate;

  const FileManagementScreen({
    super.key,
    required this.knowledgeBase,
    this.onUpdate,
  });

  @override
  State<FileManagementScreen> createState() => _FileManagementScreenState();
}

class _FileManagementScreenState extends State<FileManagementScreen> {
  final MultiAgentService _service = MultiAgentService();
  
  // 分页和搜索
  int _currentPage = 1;
  final int _pageSize = 20;
  int _totalDocuments = 0;
  String _searchQuery = '';
  String _selectedFileType = 'all';
  String _sortBy = 'created_at';
  bool _ascending = false;
  
  // 文档列表
  List<Map<String, dynamic>> _documents = [];
  bool _isLoading = false;
  Set<String> _selectedDocumentIds = {};
  bool _isSelectionMode = false;
  
  // 统计信息
  Map<String, dynamic>? _stats;

  @override
  void initState() {
    super.initState();
    _loadDocuments();
    _loadStats();
  }

  Future<void> _loadDocuments() async {
    setState(() => _isLoading = true);
    
    try {
      final result = await _service.getDocumentsPaginated(
        widget.knowledgeBase['id'],
        page: _currentPage,
        pageSize: _pageSize,
        searchQuery: _searchQuery.isEmpty ? null : _searchQuery,
        fileType: _selectedFileType,
        sortBy: _sortBy,
        ascending: _ascending,
      );
      
      // 安全地转换文档列表
      final documents = result['documents'];
      final List<Map<String, dynamic>> documentsList = [];
      
      if (documents is List) {
        for (var doc in documents) {
          if (doc is Map) {
            documentsList.add(Map<String, dynamic>.from(doc));
          }
        }
      }
      
      setState(() {
        _documents = documentsList;
        _totalDocuments = result['total'] ?? documentsList.length;
      });
    } catch (e) {
      print('Error loading documents: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load documents: $e')),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadStats() async {
    try {
      final stats = await _service.getDocumentsStats(widget.knowledgeBase['id']);
      if (mounted) {
        setState(() => _stats = stats);
      }
    } catch (e) {
      print('Failed to load stats: $e');
      // 不影响主功能，继续执行
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          _buildSearchBar(),
          if (_stats != null) _buildStatsBar(),
          Expanded(
            child: _isLoading && _documents.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : _buildDocumentList(),
          ),
          if (_totalDocuments > _pageSize) _buildPagination(),
        ],
      ),
      floatingActionButton: _buildFloatingActionButton(),
    );
  }

  Widget _buildSearchBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: InputDecoration(
                    hintText: 'Search documents...',
                    prefixIcon: const Icon(Icons.search),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                  ),
                  onChanged: (value) {
                    _searchQuery = value;
                  },
                  onSubmitted: (_) {
                    _currentPage = 1;
                    _loadDocuments();
                  },
                ),
              ),
              const SizedBox(width: 8),
              PopupMenuButton<String>(
                icon: const Icon(Icons.filter_list),
                tooltip: 'Filter',
                itemBuilder: (context) => [
                  const PopupMenuItem(
                    value: 'all',
                    child: Text('All Files'),
                  ),
                  const PopupMenuItem(
                    value: 'pdf',
                    child: Text('PDF'),
                  ),
                  const PopupMenuItem(
                    value: 'docx',
                    child: Text('Word'),
                  ),
                  const PopupMenuItem(
                    value: 'txt',
                    child: Text('Text'),
                  ),
                  const PopupMenuItem(
                    value: 'md',
                    child: Text('Markdown'),
                  ),
                ],
                onSelected: (value) {
                  setState(() {
                    _selectedFileType = value;
                    _currentPage = 1;
                  });
                  _loadDocuments();
                },
              ),
              PopupMenuButton<String>(
                icon: const Icon(Icons.sort),
                tooltip: 'Sort',
                itemBuilder: (context) => [
                  PopupMenuItem(
                    value: 'created_at',
                    child: Row(
                      children: [
                        const Text('Date Added'),
                        if (_sortBy == 'created_at')
                          Icon(
                            _ascending ? Icons.arrow_upward : Icons.arrow_downward,
                            size: 16,
                          ),
                      ],
                    ),
                  ),
                  PopupMenuItem(
                    value: 'filename',
                    child: Row(
                      children: [
                        const Text('Name'),
                        if (_sortBy == 'filename')
                          Icon(
                            _ascending ? Icons.arrow_upward : Icons.arrow_downward,
                            size: 16,
                          ),
                      ],
                    ),
                  ),
                  PopupMenuItem(
                    value: 'file_size',
                    child: Row(
                      children: [
                        const Text('Size'),
                        if (_sortBy == 'file_size')
                          Icon(
                            _ascending ? Icons.arrow_upward : Icons.arrow_downward,
                            size: 16,
                          ),
                      ],
                    ),
                  ),
                ],
                onSelected: (value) {
                  setState(() {
                    if (_sortBy == value) {
                      _ascending = !_ascending;
                    } else {
                      _sortBy = value;
                      _ascending = false;
                    }
                    _currentPage = 1;
                  });
                  _loadDocuments();
                },
              ),
              if (_isSelectionMode) ...[
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.close),
                  tooltip: 'Cancel Selection',
                  onPressed: () {
                    setState(() {
                      _isSelectionMode = false;
                      _selectedDocumentIds.clear();
                    });
                  },
                ),
              ],
            ],
          ),
          if (_isSelectionMode)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(
                children: [
                  TextButton.icon(
                    icon: const Icon(Icons.select_all),
                    label: const Text('Select All'),
                    onPressed: () {
                      setState(() {
                        _selectedDocumentIds = _documents
                            .map((doc) => doc['id'] as String)
                            .toSet();
                      });
                    },
                  ),
                  const SizedBox(width: 8),
                  TextButton.icon(
                    icon: const Icon(Icons.deselect),
                    label: const Text('Deselect All'),
                    onPressed: () {
                      setState(() {
                        _selectedDocumentIds.clear();
                      });
                    },
                  ),
                  const Spacer(),
                  Text('${_selectedDocumentIds.length} selected'),
                  const SizedBox(width: 16),
                  FilledButton.icon(
                    icon: const Icon(Icons.delete),
                    label: const Text('Delete'),
                    style: FilledButton.styleFrom(
                      backgroundColor: Colors.red,
                    ),
                    onPressed: _selectedDocumentIds.isEmpty
                        ? null
                        : _deleteSelectedDocuments,
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildStatsBar() {
    if (_stats == null || _stats!.isEmpty) return const SizedBox.shrink();
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildStatItem(
                'Total Files',
                (_stats!['total_documents'] ?? _totalDocuments).toString(),
                Icons.folder,
              ),
              if (_stats!['total_size'] != null)
                _buildStatItem(
                  'Total Size',
                  _formatFileSize(_stats!['total_size'] ?? 0),
                  Icons.storage,
                ),
              if (_stats!['file_types'] != null)
                _buildStatItem(
                  'File Types',
                  (_stats!['file_types'] as Map).length.toString(),
                  Icons.category,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  Widget _buildDocumentList() {
    if (_documents.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.folder_open,
              size: 64,
              color: Theme.of(context).disabledColor,
            ),
            const SizedBox(height: 16),
            Text(
              _searchQuery.isEmpty ? 'No documents' : 'No results found',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              _searchQuery.isEmpty
                  ? 'Add documents to get started'
                  : 'Try a different search query',
            ),
            if (_searchQuery.isEmpty) ...[
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _uploadDocument,
                icon: const Icon(Icons.add),
                label: const Text('Add Document'),
              ),
            ],
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadDocuments,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: _documents.length,
        itemBuilder: (context, index) {
          final document = _documents[index];
          final isSelected = _selectedDocumentIds.contains(document['id']);
          
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: _isSelectionMode
                  ? Checkbox(
                      value: isSelected,
                      onChanged: (value) {
                        setState(() {
                          if (value!) {
                            _selectedDocumentIds.add(document['id'] ?? '');
                          } else {
                            _selectedDocumentIds.remove(document['id'] ?? '');
                          }
                        });
                      },
                    )
                  : CircleAvatar(
                      backgroundColor: _getFileColor(document['file_type'] ?? document['extension']),
                      child: Text(
                        _getFileExtension(document['filename'] ?? document['name'] ?? 'file').toUpperCase(),
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
              title: Text(
                document['filename'] ?? document['name'] ?? 'Untitled',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Size: ${_formatFileSize(document['file_size'] ?? 0)}',
                  ),
                  Text(
                    'Added: ${_formatDate(document['created_at'] ?? document['added_at'])}',
                  ),
                  if (document['tags'] != null && 
                      (document['tags'] as List).isNotEmpty)
                    Wrap(
                      spacing: 4,
                      children: (document['tags'] as List).map((tag) {
                        return Chip(
                          label: Text(tag.toString(), style: const TextStyle(fontSize: 10)),
                          visualDensity: VisualDensity.compact,
                          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        );
                      }).toList(),
                    ),
                ],
              ),
              trailing: _isSelectionMode
                  ? null
                  : PopupMenuButton<String>(
                      itemBuilder: (context) => [
                        const PopupMenuItem(
                          value: 'view',
                          child: Row(
                            children: [
                              Icon(Icons.visibility),
                              SizedBox(width: 8),
                              Text('View'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'download',
                          child: Row(
                            children: [
                              Icon(Icons.download),
                              SizedBox(width: 8),
                              Text('Download'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'tags',
                          child: Row(
                            children: [
                              Icon(Icons.label),
                              SizedBox(width: 8),
                              Text('Tags'),
                            ],
                          ),
                        ),
                        const PopupMenuDivider(),
                        const PopupMenuItem(
                          value: 'delete',
                          child: Row(
                            children: [
                              Icon(Icons.delete, color: Colors.red),
                              SizedBox(width: 8),
                              Text('Delete', style: TextStyle(color: Colors.red)),
                            ],
                          ),
                        ),
                      ],
                      onSelected: (value) => _handleDocumentAction(value, document),
                    ),
              onTap: _isSelectionMode
                  ? () {
                      setState(() {
                        if (isSelected) {
                          _selectedDocumentIds.remove(document['id']);
                        } else {
                          _selectedDocumentIds.add(document['id']);
                        }
                      });
                    }
                  : () => _viewDocument(document),
              onLongPress: !_isSelectionMode
                  ? () {
                      setState(() {
                        _isSelectionMode = true;
                        _selectedDocumentIds.add(document['id']);
                      });
                    }
                  : null,
            ),
          );
        },
      ),
    );
  }

  Widget _buildPagination() {
    final totalPages = (_totalDocuments / _pageSize).ceil();
    
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          IconButton(
            icon: const Icon(Icons.first_page),
            onPressed: _currentPage > 1
                ? () {
                    setState(() => _currentPage = 1);
                    _loadDocuments();
                  }
                : null,
          ),
          IconButton(
            icon: const Icon(Icons.chevron_left),
            onPressed: _currentPage > 1
                ? () {
                    setState(() => _currentPage--);
                    _loadDocuments();
                  }
                : null,
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Text('Page $_currentPage of $totalPages'),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            onPressed: _currentPage < totalPages
                ? () {
                    setState(() => _currentPage++);
                    _loadDocuments();
                  }
                : null,
          ),
          IconButton(
            icon: const Icon(Icons.last_page),
            onPressed: _currentPage < totalPages
                ? () {
                    setState(() => _currentPage = totalPages);
                    _loadDocuments();
                  }
                : null,
          ),
        ],
      ),
    );
  }

  Widget _buildFloatingActionButton() {
    if (_isSelectionMode) return const SizedBox.shrink();
    
    return FloatingActionButton.extended(
      onPressed: _uploadDocument,
      icon: const Icon(Icons.add),
      label: const Text('Add Document'),
    );
  }

  Color _getFileColor(String? fileType) {
    switch (fileType?.toLowerCase()) {
      case 'pdf':
        return Colors.red;
      case 'doc':
      case 'docx':
        return Colors.blue;
      case 'txt':
        return Colors.grey;
      case 'md':
        return Colors.purple;
      default:
        return Colors.teal;
    }
  }

  String _getFileExtension(String? filename) {
    if (filename == null || !filename.contains('.')) return 'FILE';
    return filename.split('.').last.toLowerCase();
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / 1024 / 1024).toStringAsFixed(1)} MB';
    }
    return '${(bytes / 1024 / 1024 / 1024).toStringAsFixed(1)} GB';
  }

  String _formatDate(String? dateStr) {
    if (dateStr == null) return 'Unknown';
    try {
      final date = DateTime.parse(dateStr);
      final now = DateTime.now();
      final diff = now.difference(date);
      
      if (diff.inDays == 0) {
        if (diff.inHours == 0) {
          if (diff.inMinutes == 0) {
            return 'Just now';
          }
          return '${diff.inMinutes} min ago';
        }
        return '${diff.inHours} hours ago';
      } else if (diff.inDays < 7) {
        return '${diff.inDays} days ago';
      }
      
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    } catch (e) {
      return dateStr;
    }
  }

  Future<void> _uploadDocument() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        allowMultiple: true,
        type: FileType.custom,
        allowedExtensions: ['pdf', 'doc', 'docx', 'txt', 'md'],
      );
      
      if (result != null) {
        setState(() => _isLoading = true);
        
        int successCount = 0;
        int failCount = 0;
        
        for (final file in result.files) {
          if (file.path != null) {
            try {
              await _service.uploadDocument(
                widget.knowledgeBase['id'],
                file.path!,
              );
              successCount++;
            } catch (e) {
              failCount++;
            }
          }
        }
        
        if (mounted) {
          if (successCount > 0) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(
                  'Uploaded $successCount file(s)${failCount > 0 ? ', $failCount failed' : ''}',
                ),
              ),
            );
            _loadDocuments();
            _loadStats();
            widget.onUpdate?.call();
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Failed to upload files'),
                backgroundColor: Colors.red,
              ),
            );
          }
        }
        
        setState(() => _isLoading = false);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  void _handleDocumentAction(String action, Map<String, dynamic> document) {
    switch (action) {
      case 'view':
        _viewDocument(document);
        break;
      case 'download':
        // TODO: Implement download
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Download feature coming soon')),
        );
        break;
      case 'tags':
        _showTagsDialog(document);
        break;
      case 'delete':
        _confirmDeleteDocument(document);
        break;
    }
  }

  void _viewDocument(Map<String, dynamic> document) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => DocumentViewerScreen(
          document: document,
          knowledgeBaseId: widget.knowledgeBase['id'],
        ),
      ),
    );
  }

  void _showTagsDialog(Map<String, dynamic> document) {
    final currentTags = List<String>.from(document['tags'] ?? []);
    final tagsController = TextEditingController(
      text: currentTags.join(', '),
    );
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Tags'),
        content: TextField(
          controller: tagsController,
          decoration: const InputDecoration(
            hintText: 'Enter tags separated by commas',
            helperText: 'e.g., important, todo, reference',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              Navigator.pop(context);
              
              final newTags = tagsController.text
                  .split(',')
                  .map((tag) => tag.trim())
                  .where((tag) => tag.isNotEmpty)
                  .toList();
              
              try {
                await _service.updateDocumentTags(
                  widget.knowledgeBase['id'],
                  document['id'],
                  newTags,
                );
                
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Tags updated')),
                  );
                  _loadDocuments();
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Failed to update tags: $e')),
                  );
                }
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _confirmDeleteDocument(Map<String, dynamic> document) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Document'),
        content: Text(
          'Are you sure you want to delete "${document['filename']}"?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () async {
              Navigator.pop(context);
              
              try {
                await _service.deleteDocument(
                  widget.knowledgeBase['id'],
                  document['id'],
                );
                
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Document deleted')),
                  );
                  _loadDocuments();
                  _loadStats();
                  widget.onUpdate?.call();
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Failed to delete: $e')),
                  );
                }
              }
            },
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteSelectedDocuments() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Documents'),
        content: Text(
          'Are you sure you want to delete ${_selectedDocumentIds.length} document(s)?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    
    if (confirmed != true) return;
    
    setState(() => _isLoading = true);
    
    try {
      await _service.deleteDocuments(
        widget.knowledgeBase['id'],
        _selectedDocumentIds.toList(),
      );
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Deleted ${_selectedDocumentIds.length} document(s)'),
          ),
        );
        
        setState(() {
          _isSelectionMode = false;
          _selectedDocumentIds.clear();
        });
        
        _loadDocuments();
        _loadStats();
        widget.onUpdate?.call();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to delete documents: $e')),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }
}
