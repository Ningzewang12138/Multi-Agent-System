import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../services/multi_agent_service.dart';

class DocumentPreviewDialog extends StatefulWidget {
  final Map<String, dynamic> document;
  final String knowledgeBaseId;

  const DocumentPreviewDialog({
    Key? key,
    required this.document,
    required this.knowledgeBaseId,
  }) : super(key: key);

  @override
  State<DocumentPreviewDialog> createState() => _DocumentPreviewDialogState();
}

class _DocumentPreviewDialogState extends State<DocumentPreviewDialog> {
  final MultiAgentService _service = MultiAgentService();
  Map<String, dynamic>? _fullDocument;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadFullDocument();
  }

  Future<void> _loadFullDocument() async {
    try {
      final doc = await _service.getDocumentDetail(
        widget.knowledgeBaseId,
        widget.document['id'],
      );
      setState(() {
        _fullDocument = doc;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final metadata = widget.document['metadata'] ?? {};
    final filename = metadata['filename'] ?? 
                    metadata['original_filename'] ?? 
                    'Document ${widget.document['id'].substring(0, 8)}';

    return Dialog(
      child: Container(
        constraints: BoxConstraints(
          maxWidth: 800,
          maxHeight: MediaQuery.of(context).size.height * 0.8,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(12),
                  topRight: Radius.circular(12),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    _getFileIcon(metadata['extension'] ?? 'txt'),
                    color: Theme.of(context).colorScheme.onPrimaryContainer,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          filename,
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: Theme.of(context).colorScheme.onPrimaryContainer,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (metadata['file_size'] != null)
                          Text(
                            _formatFileSize(metadata['file_size']),
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onPrimaryContainer.withOpacity(0.7),
                            ),
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                    color: Theme.of(context).colorScheme.onPrimaryContainer,
                  ),
                ],
              ),
            ),
            
            // Content
            Expanded(
              child: _buildContent(),
            ),
            
            // Footer with metadata
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceVariant,
                borderRadius: const BorderRadius.only(
                  bottomLeft: Radius.circular(12),
                  bottomRight: Radius.circular(12),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Document Information',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 8),
                  _buildMetadataRow('ID', widget.document['id']),
                  if (metadata['added_at'] != null)
                    _buildMetadataRow('Added', _formatDate(metadata['added_at'])),
                  if (metadata['source'] != null)
                    _buildMetadataRow('Source', metadata['source']),
                  if (metadata['chunk_index'] != null)
                    _buildMetadataRow(
                      'Chunk',
                      '${metadata['chunk_index'] + 1} of ${metadata['total_chunks']}',
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
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
              size: 48,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text('Error loading document: $_error'),
            const SizedBox(height: 16),
            TextButton(
              onPressed: _loadFullDocument,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    final content = _fullDocument?['content'] ?? 
                   widget.document['content'] ?? 
                   widget.document['content_preview'] ?? 
                   'No content available';

    final extension = widget.document['metadata']?['extension']?.toLowerCase() ?? 'txt';

    // For markdown files, render as markdown
    if (extension == 'md') {
      return Container(
        padding: const EdgeInsets.all(16),
        child: Markdown(
          data: content,
          selectable: true,
        ),
      );
    }

    // For other files, show as plain text
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: SelectableText(
        content,
        style: const TextStyle(fontFamily: 'monospace'),
      ),
    );
  }

  Widget _buildMetadataRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodySmall,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
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

  String _formatDate(String dateStr) {
    try {
      final date = DateTime.parse(dateStr);
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} '
             '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
    } catch (e) {
      return dateStr;
    }
  }
}
