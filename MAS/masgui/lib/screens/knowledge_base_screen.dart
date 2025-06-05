import 'package:flutter/material.dart';
import '../services/multi_agent_service.dart';
import '../config/app_config.dart';

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
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: knowledgeBases.length,
                  itemBuilder: (context, index) {
                    final kb = knowledgeBases[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                          child: const Icon(Icons.folder),
                        ),
                        title: Text(
                          kb['name'],
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('${kb['document_count']} documents'),
                            if (kb['description'] != null && kb['description'].toString().isNotEmpty)
                              Text(
                                kb['description'],
                                style: TextStyle(
                                  color: Theme.of(context).textTheme.bodySmall?.color,
                                ),
                              ),
                          ],
                        ),
                        isThreeLine: kb['description'] != null && kb['description'].toString().isNotEmpty,
                        trailing: PopupMenuButton(
                          itemBuilder: (context) => [
                            const PopupMenuItem(
                              value: 'add',
                              child: Row(
                                children: [
                                  Icon(Icons.add),
                                  SizedBox(width: 8),
                                  Text('Add Document'),
                                ],
                              ),
                            ),
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
                            if (value == 'add') {
                              _showAddDocumentDialog(kb['id']);
                            } else if (value == 'delete') {
                              _confirmDelete(kb);
                            }
                          },
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
            onPressed: () {
              Navigator.pop(context);
              // TODO: Implement delete API call when available
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Delete functionality coming soon')),
              );
            },
          ),
        ],
      ),
    );
  }
}
