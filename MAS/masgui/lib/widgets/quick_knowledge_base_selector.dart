import 'package:flutter/material.dart';
import '../services/multi_agent_service.dart';
import '../config/app_config.dart';

class QuickKnowledgeBaseSelector extends StatefulWidget {
  final String? selectedKnowledgeBaseId;
  final Function(String?) onKnowledgeBaseSelected;
  final bool useRAG;
  final Function(bool) onRAGToggled;

  const QuickKnowledgeBaseSelector({
    super.key,
    this.selectedKnowledgeBaseId,
    required this.onKnowledgeBaseSelected,
    required this.useRAG,
    required this.onRAGToggled,
  });

  @override
  State<QuickKnowledgeBaseSelector> createState() => _QuickKnowledgeBaseSelectorState();
}

class _QuickKnowledgeBaseSelectorState extends State<QuickKnowledgeBaseSelector> {
  final MultiAgentService _service = MultiAgentService();
  List<Map<String, dynamic>> knowledgeBases = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    if (AppConfig.serverMode == 'multiagent') {
      _loadKnowledgeBases();
    }
  }

  Future<void> _loadKnowledgeBases() async {
    try {
      final kbs = await _service.getKnowledgeBases();
      if (mounted) {
        setState(() {
          knowledgeBases = kbs;
          isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (AppConfig.serverMode != 'multiagent') {
      return const SizedBox.shrink();
    }

    return Container(
      height: 40,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.3),
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).dividerColor,
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          // RAG Toggle
          InkWell(
            onTap: () => widget.onRAGToggled(!widget.useRAG),
            borderRadius: BorderRadius.circular(20),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: widget.useRAG
                    ? Theme.of(context).colorScheme.primary.withOpacity(0.2)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: widget.useRAG
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).dividerColor,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    widget.useRAG ? Icons.folder : Icons.folder_outlined,
                    size: 16,
                    color: widget.useRAG
                        ? Theme.of(context).colorScheme.primary
                        : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'RAG',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: widget.useRAG ? FontWeight.bold : FontWeight.normal,
                      color: widget.useRAG
                          ? Theme.of(context).colorScheme.primary
                          : Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ),
          
          if (widget.useRAG) ...[
            const SizedBox(width: 8),
            const Text('|', style: TextStyle(color: Colors.grey)),
            const SizedBox(width: 8),
            
            // Knowledge Base Selector
            Expanded(
              child: isLoading
                  ? const Center(
                      child: SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  : knowledgeBases.isEmpty
                      ? InkWell(
                          onTap: () {
                            Navigator.pushNamed(context, '/knowledge-bases');
                          },
                          child: const Text(
                            'No knowledge bases. Create one →',
                            style: TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                        )
                      : SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: Row(
                            children: [
                              for (var kb in knowledgeBases)
                                Padding(
                                  padding: const EdgeInsets.only(right: 8),
                                  child: InkWell(
                                    onTap: () => widget.onKnowledgeBaseSelected(kb['id']),
                                    borderRadius: BorderRadius.circular(16),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 12,
                                        vertical: 4,
                                      ),
                                      decoration: BoxDecoration(
                                        color: widget.selectedKnowledgeBaseId == kb['id']
                                            ? Theme.of(context).colorScheme.primary
                                            : Theme.of(context).colorScheme.surfaceVariant,
                                        borderRadius: BorderRadius.circular(16),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(
                                            Icons.folder,
                                            size: 14,
                                            color: widget.selectedKnowledgeBaseId == kb['id']
                                                ? Theme.of(context).colorScheme.onPrimary
                                                : Theme.of(context).colorScheme.onSurfaceVariant,
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            kb['name'],
                                            style: TextStyle(
                                              fontSize: 12,
                                              color: widget.selectedKnowledgeBaseId == kb['id']
                                                  ? Theme.of(context).colorScheme.onPrimary
                                                  : Theme.of(context).colorScheme.onSurfaceVariant,
                                            ),
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            '(${kb['document_count']})',
                                            style: TextStyle(
                                              fontSize: 10,
                                              color: widget.selectedKnowledgeBaseId == kb['id']
                                                  ? Theme.of(context).colorScheme.onPrimary.withOpacity(0.7)
                                                  : Theme.of(context).colorScheme.onSurfaceVariant.withOpacity(0.7),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
            
            const SizedBox(width: 8),
            
            // Manage Button
            IconButton(
              icon: const Icon(Icons.settings, size: 18),
              tooltip: 'Manage Knowledge Bases',
              onPressed: () {
                Navigator.pushNamed(context, '/knowledge-bases').then((_) {
                  _loadKnowledgeBases();
                });
              },
            ),
          ],
        ],
      ),
    );
  }
}
