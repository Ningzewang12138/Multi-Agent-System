import 'package:flutter/material.dart';

class CreateKnowledgeBaseDialog extends StatefulWidget {
  final String? title;
  
  const CreateKnowledgeBaseDialog({Key? key, this.title}) : super(key: key);

  @override
  State<CreateKnowledgeBaseDialog> createState() => _CreateKnowledgeBaseDialogState();
}

class _CreateKnowledgeBaseDialogState extends State<CreateKnowledgeBaseDialog> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title ?? 'Create Knowledge Base'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Name',
                hintText: 'Enter knowledge base name',
                border: OutlineInputBorder(),
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Name is required';
                }
                return null;
              },
              autofocus: true,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description (Optional)',
                hintText: 'Enter a brief description',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              final result = <String, String>{
                'name': _nameController.text.trim(),
              };
              
              final description = _descriptionController.text.trim();
              if (description.isNotEmpty) {
                result['description'] = description;
              }
              
              Navigator.of(context).pop(result);
            }
          },
          child: const Text('Create'),
        ),
      ],
    );
  }
}
