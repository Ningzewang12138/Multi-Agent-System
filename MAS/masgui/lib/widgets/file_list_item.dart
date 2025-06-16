import 'package:flutter/material.dart';

class FileListItem extends StatelessWidget {
  final Map<String, dynamic> document;
  final bool isSelected;
  final bool isSelectionMode;
  final VoidCallback onTap;
  final VoidCallback? onLongPress;
  final VoidCallback? onDelete;
  final VoidCallback? onDownload;
  final VoidCallback? onShare;

  const FileListItem({
    super.key,
    required this.document,
    required this.isSelected,
    required this.isSelectionMode,
    required this.onTap,
    this.onLongPress,
    this.onDelete,
    this.onDownload,
    this.onShare,
  });

  @override
  Widget build(BuildContext context) {
    return Container();
  }
}