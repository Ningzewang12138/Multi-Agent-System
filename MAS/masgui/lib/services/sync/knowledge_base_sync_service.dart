import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../config/app_config.dart';
import 'device_discovery_service.dart';

enum SyncType { push, pull, bidirectional }
enum SyncStatus { pending, inProgress, completed, failed }

class SyncRecord {
  final String syncId;
  final String kbId;
  final String sourceDeviceId;
  final String targetDeviceId;
  final String syncType;
  final SyncStatus status;
  final int documentsSynced;
  final int conflictsCount;
  final DateTime startedAt;
  final DateTime? completedAt;
  final String? errorMessage;
  final String? sourceDeviceName;
  final String? targetDeviceName;

  SyncRecord({
    required this.syncId,
    required this.kbId,
    required this.sourceDeviceId,
    required this.targetDeviceId,
    required this.syncType,
    required this.status,
    required this.documentsSynced,
    required this.conflictsCount,
    required this.startedAt,
    this.completedAt,
    this.errorMessage,
    this.sourceDeviceName,
    this.targetDeviceName,
  });

  factory SyncRecord.fromJson(Map<String, dynamic> json) {
    return SyncRecord(
      syncId: json['sync_id'],
      kbId: json['kb_id'],
      sourceDeviceId: json['source_device_id'],
      targetDeviceId: json['target_device_id'],
      syncType: json['sync_type'],
      status: _parseStatus(json['status']),
      documentsSynced: json['documents_synced'] ?? 0,
      conflictsCount: json['conflicts_count'] ?? 0,
      startedAt: DateTime.parse(json['started_at']),
      completedAt: json['completed_at'] != null 
          ? DateTime.parse(json['completed_at']) 
          : null,
      errorMessage: json['error_message'],
      sourceDeviceName: json['source_device_name'],
      targetDeviceName: json['target_device_name'],
    );
  }

  static SyncStatus _parseStatus(String status) {
    switch (status) {
      case 'pending':
        return SyncStatus.pending;
      case 'in_progress':
        return SyncStatus.inProgress;
      case 'completed':
        return SyncStatus.completed;
      case 'failed':
        return SyncStatus.failed;
      default:
        return SyncStatus.pending;
    }
  }

  String get statusText {
    switch (status) {
      case SyncStatus.pending:
        return 'Pending';
      case SyncStatus.inProgress:
        return 'In Progress';
      case SyncStatus.completed:
        return 'Completed';
      case SyncStatus.failed:
        return 'Failed';
    }
  }

  Duration? get duration {
    if (completedAt != null) {
      return completedAt!.difference(startedAt);
    }
    return null;
  }
}

class KnowledgeBaseSyncService {
  static final KnowledgeBaseSyncService _instance = KnowledgeBaseSyncService._internal();
  factory KnowledgeBaseSyncService() => _instance;
  KnowledgeBaseSyncService._internal();

  final String baseUrl = AppConfig.apiBaseUrl;
  
  // 发起同步
  Future<String> initiateSync({
    required String kbId,
    required String targetDeviceId,
    SyncType syncType = SyncType.bidirectional,
    Map<String, dynamic>? filterCriteria,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/sync/sync/initiate'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'kb_id': kbId,
          'target_device_id': targetDeviceId,
          'sync_type': _syncTypeToString(syncType),
          if (filterCriteria != null) 'filter_criteria': filterCriteria,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['sync_id'];
      } else {
        throw Exception('Failed to initiate sync: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  // 获取同步状态
  Future<SyncRecord> getSyncStatus(String syncId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/sync/sync/status/$syncId'),
      );

      if (response.statusCode == 200) {
        return SyncRecord.fromJson(json.decode(response.body));
      } else {
        throw Exception('Failed to get sync status: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  // 获取同步历史
  Future<List<SyncRecord>> getSyncHistory({
    String? kbId,
    String? deviceId,
    int limit = 50,
  }) async {
    try {
      final queryParams = <String, String>{
        if (kbId != null) 'kb_id': kbId,
        if (deviceId != null) 'device_id': deviceId,
        'limit': limit.toString(),
      };

      final uri = Uri.parse('$baseUrl/api/sync/sync/history')
          .replace(queryParameters: queryParams);

      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => SyncRecord.fromJson(json)).toList();
      } else {
        throw Exception('Failed to get sync history: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  // 获取同步设置
  Future<Map<String, dynamic>> getSyncSettings() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/sync/sync/settings'),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to get sync settings');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  // 更新同步设置
  Future<void> updateSyncSettings({
    String? conflictResolution,
    int? chunkSize,
  }) async {
    try {
      final queryParams = <String, String>{};
      if (conflictResolution != null) {
        queryParams['conflict_resolution'] = conflictResolution;
      }
      if (chunkSize != null) {
        queryParams['chunk_size'] = chunkSize.toString();
      }

      final uri = Uri.parse('$baseUrl/api/sync/sync/settings')
          .replace(queryParameters: queryParams);

      final response = await http.put(uri);

      if (response.statusCode != 200) {
        throw Exception('Failed to update sync settings');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  // 私有方法
  String _syncTypeToString(SyncType type) {
    switch (type) {
      case SyncType.push:
        return 'push';
      case SyncType.pull:
        return 'pull';
      case SyncType.bidirectional:
        return 'bidirectional';
    }
  }

  // 计算同步摘要
  static Map<String, dynamic> calculateSyncSummary(List<SyncRecord> records) {
    if (records.isEmpty) {
      return {
        'total_syncs': 0,
        'successful_syncs': 0,
        'failed_syncs': 0,
        'total_documents': 0,
        'total_conflicts': 0,
      };
    }

    int successful = 0;
    int failed = 0;
    int totalDocuments = 0;
    int totalConflicts = 0;

    for (final record in records) {
      if (record.status == SyncStatus.completed) {
        successful++;
        totalDocuments += record.documentsSynced;
      } else if (record.status == SyncStatus.failed) {
        failed++;
      }
      totalConflicts += record.conflictsCount;
    }

    return {
      'total_syncs': records.length,
      'successful_syncs': successful,
      'failed_syncs': failed,
      'total_documents': totalDocuments,
      'total_conflicts': totalConflicts,
      'success_rate': records.isEmpty ? 0 : (successful / records.length * 100),
    };
  }
}
