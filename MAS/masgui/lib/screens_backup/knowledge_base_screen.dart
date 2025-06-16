import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'dart:io';
import '../services/multi_agent_service.dart';
import '../config/app_config.dart';
import 'knowledge_base_detail_screen.dart';

class KnowledgeBaseScreen extends StatefulWidget {
  const KnowledgeBaseScreen({super.key});

  @override
  State<KnowledgeBaseScreen> createState() => _KnowledgeBaseScreenState();
}

class _KnowledgeBaseScreenState extends State<KnowledgeBaseScreen> {
  final MultiAgentService _service = MultiAgentService();
  List<Map<String, dynamic>> knowledgeBases = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadKnowledgeBases();
  }

  Future<void> _loadKnowledgeBases() async {
    setState(() => isLoading = true);
    try {
      final kbs = await _service.getKnowledgeBases();
      setState(() {
        knowledgeBases = kbs;
        isLoading = false;
      });
    } catch (e) {
      setState(() => isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load knowledge bases: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Knowledge Base Management'),
        actions: [
          IconButton(
            icon: const Icon(Icons.share),
            tooltip: 'Share Knowledge Base',
            onPressed: _showShareDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadKnowledgeBases,
          ),
        ],
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : knowledgeBases.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.folder_outlined,
                        size: 64,
                        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.3),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No knowledge bases yet',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                            ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Create your first knowledge base to get started',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                            ),
                      ),
                    ],
                  ),
                )
              : GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    childAspectRatio: 1.5,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                  ),
                  itemCount: knowledgeBases.length,
                  itemBuilder: (context, index) {
                    final kb = knowledgeBases[index];
                    return Card(
                      elevation: 2,
                      child: InkWell(
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => KnowledgeBaseDetailScreen(
                                knowledgeBase: kb,
                                onUpdate: _loadKnowledgeBases,
                              ),
                            ),
                          );
                        },
                        borderRadius: BorderRadius.circular(12),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(
                                    Icons.folder,
                                    color: Theme.of(context).colorScheme.primary,
                                    size: 32,
                                  ),
                                  const Spacer(),
                                  PopupMenuButton(
                                    itemBuilder: (context) => [
                                      const PopupMenuItem(
                                        value: 'upload',
                                        child: Row(
                                          children: [
                                            Icon(Icons.upload_file),
                                            SizedBox(width: 8),
                                            Text('Upload File'),
                                          ],
                                        ),
                                      ),
                                      const PopupMenuItem(
                                        value: 'add',
                                        child: Row(
                                          children: [
                                            Icon(Icons.add),
                                            SizedBox(width: 8),
                                            Text('Add Text'),
                                          ],
                                        ),
                                      ),
                                      const PopupMenuItem(
                                        value: 'share',
                                        child: Row(
                                          children: [
                                            Icon(Icons.share),
                                            SizedBox(width: 8),
                                            Text('Share'),
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
                                    onSelected: (value) {
                                      switch (value) {
                                        case 'upload':
                                          _uploadFile(kb['id']);
                                          break;
                                        case 'add':
                                          _showAddDocumentDialog(kb['id']);
                                          break;
                                        case 'share':
                                          _shareKnowledgeBase(kb);
                                          break;
                                        case 'delete':
                                          _confirmDelete(kb);
                                          break;
                                      }
                                    },
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Text(
                                kb['name'],
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 16,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '${kb['document_count']} documents',
                                style: TextStyle(
                                  color: Theme.of(context).textTheme.bodySmall?.color,
                                ),
                              ),
                              if (kb['description'] != null && kb['description'].toString().isNotEmpty)
                                Expanded(
                                  child: Padding(
                                    padding: const EdgeInsets.only(top: 4),
                                    child: Text(
                                      kb['description'],
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: Theme.of(context).textTheme.bodySmall?.color,
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showCreateKnowledgeBaseDialog,
        icon: const Icon(Icons.add),
        label: const Text('New Knowledge Base'),
      ),
    );
  }

  void _showCreateKnowledgeBaseDialog() {
    final nameController = TextEditingController();
    final descController = TextEditingController();

    showDialog(
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
                hintText: 'e.g., Technical Documentation',
              ),
              autofocus: true,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: descController,
              decoration: const InputDecoration(
                labelText: 'Description',
                hintText: 'Brief description of this knowledge base',
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            child: const Text('Cancel'),
            onPressed: () => Navigator.pop(context),
          ),
          FilledButton(
            child: const Text('Create'),
            onPressed: () async {
              if (nameController.text.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Name is required')),
                );
                return;
              }
              
              try {
                await _service.createKnowledgeBase(
                  nameController.text,
                  descController.text,
                );
                if (mounted) {
                  Navigator.pop(context);
                  _loadKnowledgeBases();
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
            },
          ),
        ],
      ),
    );
  }

  void _showAddDocumentDialog(String kbId) {
    final contentController = TextEditingController();
    final titleController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Document'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleController,
                decoration: const InputDecoration(
                  labelText: 'Title (optional)',
                  hintText: 'Document title',
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: contentController,
                decoration: const InputDecoration(
                  labelText: 'Content',
                  hintText: 'Paste your document content here',
                ),
                maxLines: 10,
                minLines: 5,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            child: const Text('Cancel'),
            onPressed: () => Navigator.pop(context),
          ),
          FilledButton(
            child: const Text('Add'),
            onPressed: () async {
              if (contentController.text.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Content is required')),
                );
                return;
              }
              
              try {
                await _service.addDocument(
                  kbId,
                  contentController.text,
                  metadata: titleController.text.isNotEmpty
                      ? {'title': titleController.text}
                      : null,
                );
                if (mounted) {
                  Navigator.pop(context);
                  _loadKnowledgeBases();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Document added')),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Failed to add document: $e')),
                  );
                }
              }
            },
          ),
        ],
      ),
    );
  }

  Future<void> _uploadFile(String kbId) async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['txt', 'pdf', 'doc', 'docx', 'md'],
        allowMultiple: true,
      );

      if (result != null) {
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (context) => const AlertDialog(
            content: Row(
              children: [
                CircularProgressIndicator(),
                SizedBox(width: 16),
                Text('Uploading files...'),
              ],
            ),
          ),
        );

        int successCount = 0;
        int failCount = 0;

        for (var file in result.files) {
          try {
            if (file.path != null) {
              await _service.uploadDocument(kbId, file.path!);
              successCount++;
            }
          } catch (e) {
            failCount++;
            print('Failed to upload ${file.name}: $e');
          }
        }

        if (mounted) {
          Navigator.pop(context); // 关闭加载对话框
          
          String message = '';
          if (successCount > 0) {
            message += '$successCount file(s) uploaded successfully. ';
          }
          if (failCount > 0) {
            message += '$failCount file(s) failed to upload.';
          }
          
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(message)),
          );
          
          _loadKnowledgeBases();
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error selecting files: $e')),
        );
      }
    }
  }

  void _confirmDelete(Map<String, dynamic> kb) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Knowledge Base'),
        content: Text(
          'Are you sure you want to delete "${kb['name']}"?\nThis will remove all ${kb['document_count']} documents.',
        ),
        actions: [
          TextButton(
            child: const Text('Cancel'),
            onPressed: () => Navigator.pop(context),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Colors.red,
            ),
            child: const Text('Delete'),
            onPressed: () async {
              Navigator.pop(context);
              try {
                await _service.deleteKnowledgeBase(kb['id']);
                _loadKnowledgeBases();
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
            },
          ),
        ],
      ),
    );
  }

  void _showShareDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Share Knowledge Base'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Share your knowledge bases with other devices on the same network.'),
            const SizedBox(height: 16),
            Text(
              'Server URL: ${AppConfig.multiAgentServer}',
              style: const TextStyle(fontFamily: 'monospace'),
            ),
            const SizedBox(height: 8),
            const Text(
              'Other devices can connect to this URL to access the same knowledge bases.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            child: const Text('Close'),
            onPressed: () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }

  void _shareKnowledgeBase(Map<String, dynamic> kb) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Share "${kb['name']}"'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Knowledge Base ID:'),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(
                kb['id'],
                style: const TextStyle(fontFamily: 'monospace'),
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Share this ID with other users to grant them access to this knowledge base.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            child: const Text('Close'),
            onPressed: () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }
}
