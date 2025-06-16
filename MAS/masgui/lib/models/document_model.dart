import 'package:flutter/material.dart';

class DocumentModel {
  final String id;
  final String title;
  final String? content;
  final String? contentPreview;
  final Map<String, dynamic>? metadata;
  final String? fileType;
  final int? size;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final List<String>? tags;
  final String? source;
  final int? chunkCount;
  final Map<String, dynamic>? embeddings;

  DocumentModel({
    required this.id,
    required this.title,
    this.content,
    this.contentPreview,
    this.metadata,
    this.fileType,
    this.size,
    this.createdAt,
    this.updatedAt,
    this.tags,
    this.source,
    this.chunkCount,
    this.embeddings,
  });

  factory DocumentModel.fromJson(Map<String, dynamic> json) {
    // 从内容或元数据中提取标题
    String extractTitle() {
      if (json['metadata']?['title'] != null) {
        return json['metadata']['title'];
      } else if (json['metadata']?['filename'] != null) {
        return json['metadata']['filename'];
      } else if (json['metadata']?['original_filename'] != null) {
        return json['metadata']['original_filename'];
      } else if (json['content'] != null) {
        // 从内容中提取前50个字符作为标题
        final content = json['content'].toString();
        return content.length > 50 
            ? '${content.substring(0, 50)}...' 
            : content;
      }
      return 'Untitled Document';
    }

    // 提取文件类型
    String? extractFileType() {
      if (json['metadata']?['file_type'] != null) {
        return json['metadata']['file_type'];
      } else if (json['metadata']?['extension'] != null) {
        return json['metadata']['extension'];
      } else if (json['metadata']?['filename'] != null) {
        final filename = json['metadata']['filename'].toString();
        final parts = filename.split('.');
        if (parts.length > 1) {
          return parts.last.toLowerCase();
        }
      }
      return null;
    }

    // 生成内容预览
    String? generatePreview(String? content) {
      if (content == null || content.isEmpty) return null;
      
      // 清理内容：移除多余的空白字符
      final cleaned = content.replaceAll(RegExp(r'\s+'), ' ').trim();
      
      // 截取前200个字符
      return cleaned.length > 200 
          ? '${cleaned.substring(0, 200)}...' 
          : cleaned;
    }

    return DocumentModel(
      id: json['id'],
      title: extractTitle(),
      content: json['content'],
      contentPreview: json['content_preview'] ?? generatePreview(json['content']),
      metadata: json['metadata'],
      fileType: extractFileType(),
      size: json['size'] ?? json['metadata']?['size'],
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : (json['metadata']?['added_at'] != null 
              ? DateTime.parse(json['metadata']['added_at'])
              : null),
      updatedAt: json['updated_at'] != null 
          ? DateTime.parse(json['updated_at']) 
          : null,
      tags: json['tags'] != null 
          ? List<String>.from(json['tags']) 
          : (json['metadata']?['tags'] != null 
              ? List<String>.from(json['metadata']['tags'])
              : null),
      source: json['source'] ?? json['metadata']?['source'],
      chunkCount: json['chunk_count'] ?? json['metadata']?['total_chunks'],
      embeddings: json['embeddings'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'content': content,
      'content_preview': contentPreview,
      'metadata': metadata,
      'file_type': fileType,
      'size': size,
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'tags': tags,
      'source': source,
      'chunk_count': chunkCount,
      if (embeddings != null) 'embeddings': embeddings,
    };
  }

  // 便捷方法
  bool get hasContent => content != null && content!.isNotEmpty;
  
  bool get hasMetadata => metadata != null && metadata!.isNotEmpty;
  
  bool get hasTags => tags != null && tags!.isNotEmpty;
  
  String get displayTitle {
    if (title.isNotEmpty) return title;
    if (metadata?['title'] != null) return metadata!['title'];
    if (metadata?['filename'] != null) return metadata!['filename'];
    return 'Untitled Document';
  }
  
  String get displayFileType {
    if (fileType != null) return fileType!.toUpperCase();
    return 'UNKNOWN';
  }
  
  String get formattedSize {
    if (size == null) return '';
    
    final bytes = size!;
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    }
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }
  
  String get formattedDate {
    final date = updatedAt ?? createdAt;
    if (date == null) return '';
    
    final now = DateTime.now();
    final difference = now.difference(date);
    
    if (difference.inDays == 0) {
      if (difference.inHours == 0) {
        if (difference.inMinutes == 0) {
          return 'Just now';
        }
        return '${difference.inMinutes} min ago';
      }
      return '${difference.inHours} hours ago';
    } else if (difference.inDays == 1) {
      return 'Yesterday';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} days ago';
    } else if (difference.inDays < 30) {
      final weeks = (difference.inDays / 7).floor();
      return '$weeks week${weeks > 1 ? 's' : ''} ago';
    } else {
      return '${date.day}/${date.month}/${date.year}';
    }
  }
  
  IconData get fileIcon {
    switch (fileType?.toLowerCase()) {
      case 'pdf':
        return Icons.picture_as_pdf;
      case 'doc':
      case 'docx':
        return Icons.description;
      case 'txt':
        return Icons.text_snippet;
      case 'md':
        return Icons.code;
      case 'html':
        return Icons.language;
      case 'csv':
      case 'xls':
      case 'xlsx':
        return Icons.table_chart;
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
        return Icons.image;
      default:
        return Icons.insert_drive_file;
    }
  }
  
  Color get fileColor {
    switch (fileType?.toLowerCase()) {
      case 'pdf':
        return Colors.red;
      case 'doc':
      case 'docx':
        return Colors.blue;
      case 'txt':
        return Colors.grey;
      case 'md':
        return Colors.green;
      case 'html':
        return Colors.orange;
      case 'csv':
      case 'xls':
      case 'xlsx':
        return Colors.teal;
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
        return Colors.purple;
      default:
        return Colors.blueGrey;
    }
  }

  // 复制并修改
  DocumentModel copyWith({
    String? id,
    String? title,
    String? content,
    String? contentPreview,
    Map<String, dynamic>? metadata,
    String? fileType,
    int? size,
    DateTime? createdAt,
    DateTime? updatedAt,
    List<String>? tags,
    String? source,
    int? chunkCount,
    Map<String, dynamic>? embeddings,
  }) {
    return DocumentModel(
      id: id ?? this.id,
      title: title ?? this.title,
      content: content ?? this.content,
      contentPreview: contentPreview ?? this.contentPreview,
      metadata: metadata ?? this.metadata,
      fileType: fileType ?? this.fileType,
      size: size ?? this.size,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      tags: tags ?? this.tags,
      source: source ?? this.source,
      chunkCount: chunkCount ?? this.chunkCount,
      embeddings: embeddings ?? this.embeddings,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is DocumentModel && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;
}
