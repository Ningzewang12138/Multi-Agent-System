class KnowledgeBase {
  final String id;
  final String name;
  final String? description;
  final DateTime createdAt;
  final int documentCount;
  final String? deviceId;
  final String? deviceName;
  final bool isDraft;
  final bool isSynced;
  final Map<String, dynamic>? metadata;

  KnowledgeBase({
    required this.id,
    required this.name,
    this.description,
    required this.createdAt,
    this.documentCount = 0,
    this.deviceId,
    this.deviceName,
    this.isDraft = false,
    this.isSynced = false,
    this.metadata,
  });

  factory KnowledgeBase.fromJson(Map<String, dynamic> json) {
    try {
      // Parse date, handling different possible formats
      DateTime createdAt;
      final createdAtValue = json['created_at'];
      
      if (createdAtValue == null || createdAtValue == '') {
        // If created_at is null or empty, use current time
        createdAt = DateTime.now();
      } else if (createdAtValue is String) {
        try {
          createdAt = DateTime.parse(createdAtValue);
        } catch (e) {
          print('Failed to parse date: $createdAtValue, using current time');
          createdAt = DateTime.now();
        }
      } else if (createdAtValue is int) {
        // Unix timestamp
        createdAt = DateTime.fromMillisecondsSinceEpoch(createdAtValue * 1000);
      } else {
        // Default to now if can't parse
        createdAt = DateTime.now();
      }
      
      // 检查元数据中的草稿状态
      final metadata = json['metadata'] as Map<String, dynamic>?;
      bool isDraft = false;
      if (metadata != null) {
        // ChromaDB可能将布尔值存储为整数
        final draftValue = metadata['is_draft'];
        if (draftValue is bool) {
          isDraft = draftValue;
        } else if (draftValue is int) {
          isDraft = draftValue != 0;
        }
      }
      // 如果json中直接有is_draft字段，优先使用
      if (json.containsKey('is_draft')) {
        final directDraftValue = json['is_draft'];
        if (directDraftValue is bool) {
          isDraft = directDraftValue;
        } else if (directDraftValue is int) {
          isDraft = directDraftValue != 0;
        }
      }
      
      // 调试输出
      print('KnowledgeBase.fromJson: ${json['name']}, is_draft in json: ${json.containsKey('is_draft')}, isDraft: $isDraft');
      if (metadata != null) {
        print('Metadata: $metadata');
      }
      
      // 如果仍然没有is_draft信息，默认为已发布（更安全的做法）
      // 因为只有草稿可以被删除，所以默认为已发布更安全
      if (!json.containsKey('is_draft') && (metadata == null || !metadata.containsKey('is_draft'))) {
        isDraft = false;
        print('No is_draft info found, defaulting to published (safer)');
      }
      
      return KnowledgeBase(
        id: json['id']?.toString() ?? '',
        name: json['name']?.toString() ?? 'Unnamed',
        description: json['description']?.toString(),
        createdAt: createdAt,
        documentCount: json['document_count'] is int 
            ? json['document_count'] 
            : int.tryParse(json['document_count']?.toString() ?? '0') ?? 0,
        deviceId: json['device_id']?.toString(),
        deviceName: json['device_name']?.toString(),
        isDraft: isDraft,
        isSynced: json['is_synced'] == true,
        metadata: metadata,
      );
    } catch (e) {
      print('Error parsing KnowledgeBase from JSON: $json');
      print('Error details: $e');
      rethrow;
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'created_at': createdAt.toIso8601String(),
      'document_count': documentCount,
      'device_id': deviceId,
      'device_name': deviceName,
      'is_draft': isDraft,
      'is_synced': isSynced,
      'metadata': metadata,
    };
  }
}
