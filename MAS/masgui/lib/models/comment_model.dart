class CommentModel {
  final String id;
  final String content;

  CommentModel({required this.id, required this.content});
  
  factory CommentModel.fromJson(Map<String, dynamic> json) {
    return CommentModel(
      id: json['id'] ?? '',
      content: json['content'] ?? '',
    );
  }
}