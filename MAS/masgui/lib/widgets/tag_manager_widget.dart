import 'package:flutter/material.dart';

class TagManagerWidget extends StatelessWidget {
  final List<String> tags;
  final bool isEditing;
  final Function(List<String>) onTagsChanged;

  const TagManagerWidget({
    super.key,
    required this.tags,
    required this.isEditing,
    required this.onTagsChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container();
  }
}