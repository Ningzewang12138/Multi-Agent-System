import 'package:flutter/material.dart';

class DocumentViewerScreen extends StatelessWidget {
  final Map<String, dynamic> document;
  final String knowledgeBaseId;
  final VoidCallback? onUpdate;

  const DocumentViewerScreen({
    super.key,
    required this.document,
    required this.knowledgeBaseId,
    this.onUpdate,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Document Viewer'),
      ),
      body: const Center(
        child: Text('Document Viewer'),
      ),
    );
  }
}