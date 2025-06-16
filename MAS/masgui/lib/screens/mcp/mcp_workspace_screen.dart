import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import 'package:file_picker/file_picker.dart';
import '../../services/mcp/mcp_service.dart';

class MCPWorkspaceScreen extends StatefulWidget {
  final String sessionId;

  const MCPWorkspaceScreen({Key? key, required this.sessionId})
      : super(key: key);

  @override
  State<MCPWorkspaceScreen> createState() => _MCPWorkspaceScreenState();
}

class _MCPWorkspaceScreenState extends State<MCPWorkspaceScreen> {
  List<WorkspaceFileInfo> _files = [];
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadFiles();
  }

  Future<void> _loadFiles() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final mcpService = context.read<MCPService>();
      final files = await mcpService.listWorkspaceFiles(widget.sessionId);
      
      setState(() {
        _files = files;
        _error = mcpService.error;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('工作空间'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadFiles,
          ),
          IconButton(
            icon: const Icon(Icons.upload_file),
            onPressed: _uploadFile,
          ),
          IconButton(
            icon: const Icon(Icons.delete_forever),
            onPressed: () => _confirmDelete(context),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              '加载失败',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              _error!,
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadFiles,
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        // 会话信息
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          color: Theme.of(context).primaryColor.withOpacity(0.1),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '会话ID',
                style: TextStyle(
                  fontSize: 12,
                  color: Theme.of(context).primaryColor,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              SelectableText(
                widget.sessionId,
                style: const TextStyle(fontFamily: 'monospace'),
              ),
            ],
          ),
        ),
        
        // 文件列表
        Expanded(
          child: _files.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.folder_open,
                        size: 64,
                        color: Theme.of(context).brightness == Brightness.dark
                            ? Colors.grey.shade600
                            : Colors.grey,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        '工作空间为空',
                        style: TextStyle(
                          color: Theme.of(context).brightness == Brightness.dark
                              ? Colors.grey.shade600
                              : Colors.grey,
                        ),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _files.length,
                  itemBuilder: (context, index) {
                    final file = _files[index];
                    return _buildFileCard(file);
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildFileCard(WorkspaceFileInfo file) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          file.isDirectory ? Icons.folder : _getFileIcon(file.name),
          size: 32,
          color: Theme.of(context).primaryColor,
        ),
        title: Text(file.name),
        subtitle: Text(
          '${_formatFileSize(file.size)} • ${_formatDate(file.modified)}',
        ),
        trailing: file.isDirectory
            ? null
            : Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    icon: const Icon(Icons.visibility),
                    onPressed: () => _viewFile(file.name),
                    tooltip: '查看',
                  ),
                  IconButton(
                    icon: const Icon(Icons.download),
                    onPressed: () => _downloadFile(file.name),
                    tooltip: '下载',
                  ),
                ],
              ),
      ),
    );
  }

  IconData _getFileIcon(String filename) {
    final extension = filename.split('.').last.toLowerCase();
    switch (extension) {
      case 'txt':
        return Icons.description;
      case 'json':
        return Icons.data_object;
      case 'csv':
        return Icons.table_chart;
      case 'pdf':
        return Icons.picture_as_pdf;
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
        return Icons.image;
      default:
        return Icons.insert_drive_file;
    }
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  String _formatDate(String dateStr) {
    try {
      final date = DateTime.parse(dateStr);
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} '
          '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
    } catch (e) {
      return dateStr;
    }
  }

  Future<void> _viewFile(String filename) async {
    final mcpService = context.read<MCPService>();
    final fileData = await mcpService.downloadWorkspaceFile(
      widget.sessionId,
      filename,
    );

    if (fileData != null && mounted) {
      showDialog(
        context: context,
        builder: (context) => Dialog(
          child: Container(
            constraints: const BoxConstraints(
              maxWidth: 800,
              maxHeight: 600,
            ),
            child: Column(
              children: [
                // 标题栏
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Theme.of(context).primaryColor,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(4),
                      topRight: Radius.circular(4),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _getFileIcon(filename),
                        color: Colors.white,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          filename,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: Colors.white),
                        onPressed: () => Navigator.pop(context),
                      ),
                    ],
                  ),
                ),
                // 内容区域
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    color: Theme.of(context).brightness == Brightness.dark
                        ? Colors.grey.shade900
                        : Colors.white,
                    child: SingleChildScrollView(
                      child: SelectableText(
                        fileData['type'] == 'text'
                            ? fileData['content']
                            : '二进制文件，无法预览',
                        style: TextStyle(
                          fontFamily: 'monospace',
                          color: Theme.of(context).brightness == Brightness.dark
                              ? Colors.white
                              : Colors.black87,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(mcpService.error ?? '无法查看文件'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _downloadFile(String filename) async {
    // TODO: 实现文件下载到本地
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('文件下载功能正在开发中')),
    );
  }

  Future<void> _uploadFile() async {
    try {
      final result = await FilePicker.platform.pickFiles();
      
      if (result != null && result.files.isNotEmpty) {
        final file = result.files.first;
        
        if (file.bytes != null) {
          final mcpService = context.read<MCPService>();
          final success = await mcpService.uploadFileToWorkspace(
            widget.sessionId,
            file.name,
            file.bytes!,
          );

          if (success) {
            await _loadFiles();
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('文件上传成功')),
              );
            }
          } else if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(mcpService.error ?? '文件上传失败'),
                backgroundColor: Colors.red,
              ),
            );
          }
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('上传失败: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _confirmDelete(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除工作空间'),
        content: const Text('确定要删除这个工作空间吗？此操作不可撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);
              await _deleteWorkspace();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
            ),
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteWorkspace() async {
    final mcpService = context.read<MCPService>();
    final success = await mcpService.deleteWorkspace(widget.sessionId);

    if (mounted) {
      if (success) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('工作空间已删除')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(mcpService.error ?? '删除失败'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}
