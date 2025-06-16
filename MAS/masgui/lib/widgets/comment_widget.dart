import 'package:flutter/material.dart';

class CommentWidget extends StatelessWidget {
  final Map<String, dynamic> comment;
  final Function(Map<String, dynamic>) onReply;
  final Function(Map<String, dynamic>) onEdit; 
  final Function(Map<String, dynamic>) onDelete;

  const CommentWidget({
    super.key,
    required this.comment,
    required this.onReply,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Container();
  }
}