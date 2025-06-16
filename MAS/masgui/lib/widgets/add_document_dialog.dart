import 'package:flutter/material.dart';

class AddDocumentDialog extends StatefulWidget {
  const AddDocumentDialog({Key? key}) : super(key: key);

  @override
  State<AddDocumentDialog> createState() => _AddDocumentDialogState();
}

class _AddDocumentDialogState extends State<AddDocumentDialog> {
  final TextEditingController _contentController = TextEditingController();
  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _sourceController = TextEditingController();
  final TextEditingController _topicController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _contentController.dispose();
    _titleController.dispose();
    _sourceController.dispose();
    _topicController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        constraints: const BoxConstraints(
          maxWidth: 600,
          maxHeight: 600,
        ),
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Add Text Document',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 24),
              
              // Title field
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Title (Optional)',
                  hintText: 'Document title',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.title),
                ),
              ),
              const SizedBox(height: 16),
              
              // Content field
              Expanded(
                child: TextFormField(
                  controller: _contentController,
                  maxLines: null,
                  expands: true,
                  textAlignVertical: TextAlignVertical.top,
                  decoration: const InputDecoration(
                    labelText: 'Content',
                    hintText: 'Enter your document content here...',
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Content is required';
                    }
                    return null;
                  },
                ),
              ),
              const SizedBox(height: 16),
              
              // Metadata fields
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _sourceController,
                      decoration: const InputDecoration(
                        labelText: 'Source (Optional)',
                        hintText: 'e.g., manual entry',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.source),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: TextFormField(
                      controller: _topicController,
                      decoration: const InputDecoration(
                        labelText: 'Topic (Optional)',
                        hintText: 'e.g., technical',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.category),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              
              // Action buttons
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: _submit,
                    child: const Text('Add Document'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _submit() {
    if (_formKey.currentState!.validate()) {
      final metadata = <String, dynamic>{
        'source': _sourceController.text.isNotEmpty 
            ? _sourceController.text 
            : 'manual entry',
        'added_at': DateTime.now().toIso8601String(),
        'extension': 'txt',
      };
      
      if (_titleController.text.isNotEmpty) {
        metadata['filename'] = _titleController.text;
        metadata['title'] = _titleController.text;
      }
      
      if (_topicController.text.isNotEmpty) {
        metadata['topic'] = _topicController.text;
      }
      
      Navigator.of(context).pop({
        'content': _contentController.text.trim(),
        'metadata': metadata,
      });
    }
  }
}
