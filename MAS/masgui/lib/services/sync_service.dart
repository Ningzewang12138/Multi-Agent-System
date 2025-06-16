// lib/services/sync_service.dart

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_config.dart';

class Device {
  final String id;
  final String name;
  final String type;
  final String platform;
  final String ipAddress;
  final int port;
  final String version;
  final List<String> capabilities;
  final String lastSeen;
  final String status;

  Device({
    required this.id,
    required this.name,
    required this.type,
    required this.platform,
    required this.ipAddress,
    required this.port,
    required this.version,
    required this.capabilities,
    required this.lastSeen,
    required this.status,
  });

  factory Device.fromJson(Map<String, dynamic> json) {
    return Device(
      id: json['id'],
      name: json['name'],
      type: json['type'],
      platform: json['platform'],
      ipAddress: json['ip_address'],
      port: json['port'],
      version: json['version'],
      capabilities: List<String>.from(json['capabilities']),
      lastSeen: json['last_seen'],
      status: json['status'],
    );
  }
}

class SyncStatus {
  final String syncId;
  final String status;
  final int documentsSynced;
  final int conflictsCount;
  final String startedAt;
  final String? completedAt;
  final String? errorMessage;

  SyncStatus({
    required this.syncId,
    required this.status,
    required this.documentsSynced,
    required this.conflictsCount,
    required this.startedAt,
    this.completedAt,
    this.errorMessage,
  });

  factory SyncStatus.fromJson(Map<String, dynamic> json) {
    return SyncStatus(
      syncId: json['sync_id'],
      status: json['status'],
      documentsSynced: json['documents_synced'],
      conflictsCount: json['conflicts_count'],
      startedAt: json['started_at'],
      completedAt: json['completed_at'],
      errorMessage: json['error_message'],
    );
  }
}

class SyncHistory {
  final String syncId;
  final String kbId;
  final String sourceDeviceId;
  final String targetDeviceId;
  final String sourceDeviceName;
  final String targetDeviceName;
  final String syncType;
  final String status;
  final int documentsSynced;
  final int conflictsCount;
  final String startedAt;
  final String? completedAt;
  final String? errorMessage;

  SyncHistory({
    required this.syncId,
    required this.kbId,
    required this.sourceDeviceId,
    required this.targetDeviceId,
    required this.sourceDeviceName,
    required this.targetDeviceName,
    required this.syncType,
    required this.status,
    required this.documentsSynced,
    required this.conflictsCount,
    required this.startedAt,
    this.completedAt,
    this.errorMessage,
  });

  factory SyncHistory.fromJson(Map<String, dynamic> json) {
    return SyncHistory(
      syncId: json['sync_id'],
      kbId: json['kb_id'],
      sourceDeviceId: json['source_device_id'],
      targetDeviceId: json['target_device_id'],
      sourceDeviceName: json['source_device_name'] ?? 'Unknown',
      targetDeviceName: json['target_device_name'] ?? 'Unknown',
      syncType: json['sync_type'],
      status: json['status'],
      documentsSynced: json['documents_synced'],
      conflictsCount: json['conflicts_count'],
      startedAt: json['started_at'],
      completedAt: json['completed_at'],
      errorMessage: json['error_message'],
    );
  }
}

class SyncService {
  static final SyncService _instance = SyncService._internal();
  factory SyncService() => _instance;
  SyncService._internal();

  http.Client? _client;

  http.Client get client {
    _client ??= http.Client();
    return _client!;
  }

  void dispose() {
    _client?.close();
    _client = null;
  }

  String get baseUrl {
    if (AppConfig.serverMode == 'multiagent') {
      return AppConfig.multiAgentServer;
    }
    throw Exception('Multi-agent server not configured');
  }

  // 设备发现相关方法

  Future<List<Device>> getDevices({String? status}) async {
    try {
      final queryParams = status != null ? '?status=$status' : '';
      final response = await client.get(
        Uri.parse('$baseUrl/api/sync/devices$queryParams'),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => Device.fromJson(json)).toList();
      } else {
        throw Exception('Failed to get devices: ${response.statusCode}');
      }
    } catch (e) {
      print('Error getting devices: $e');
      throw e;
    }
  }

  Future<Device> getDevice(String deviceId) async {
    try {
      final response = await client.get(
        Uri.parse('$baseUrl/api/sync/devices/$deviceId'),
      );

      if (response.statusCode == 200) {
        return Device.fromJson(json.decode(response.body));
      } else {
        throw Exception('Failed to get device: ${response.statusCode}');
      }
    } catch (e) {
      print('Error getting device: $e');
      throw e;
    }
  }

  Future<void> scanDevices() async {
    try {
      final response = await client.post(
        Uri.parse('$baseUrl/api/sync/devices/scan'),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to scan devices: ${response.statusCode}');
      }
    } catch (e) {
      print('Error scanning devices: $e');
      throw e;
    }
  }

  Future<Device> getCurrentDeviceInfo() async {
    try {
      final response = await client.get(
        Uri.parse('$baseUrl/api/sync/device/info'),
      );

      if (response.statusCode == 200) {
        return Device.fromJson(json.decode(response.body));
      } else {
        throw Exception('Failed to get current device info: ${response.statusCode}');
      }
    } catch (e) {
      print('Error getting current device info: $e');
      throw e;
    }
  }

  // 同步相关方法

  Future<String> initiateSync({
    required String kbId,
    required String targetDeviceId,
    String syncType = 'bidirectional',
    Map<String, dynamic>? filterCriteria,
  }) async {
    try {
      final response = await client.post(
        Uri.parse('$baseUrl/api/sync/sync/initiate'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'kb_id': kbId,
          'target_device_id': targetDeviceId,
          'sync_type': syncType,
          'filter_criteria': filterCriteria,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['sync_id'];
      } else {
        throw Exception('Failed to initiate sync: ${response.statusCode}');
      }
    } catch (e) {
      print('Error initiating sync: $e');
      throw e;
    }
  }

  Future<SyncStatus> getSyncStatus(String syncId) async {
    try {
      final response = await client.get(
        Uri.parse('$baseUrl/api/sync/sync/status/$syncId'),
      );

      if (response.statusCode == 200) {
        return SyncStatus.fromJson(json.decode(response.body));
      } else {
        throw Exception('Failed to get sync status: ${response.statusCode}');
      }
    } catch (e) {
      print('Error getting sync status: $e');
      throw e;
    }
  }

  Future<List<SyncHistory>> getSyncHistory({
    String? kbId,
    String? deviceId,
    int limit = 50,
  }) async {
    try {
      final queryParams = <String, String>{};
      if (kbId != null) queryParams['kb_id'] = kbId;
      if (deviceId != null) queryParams['device_id'] = deviceId;
      queryParams['limit'] = limit.toString();

      final uri = Uri.parse('$baseUrl/api/sync/sync/history')
          .replace(queryParameters: queryParams);

      final response = await client.get(uri);

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => SyncHistory.fromJson(json)).toList();
      } else {
        throw Exception('Failed to get sync history: ${response.statusCode}');
      }
    } catch (e) {
      print('Error getting sync history: $e');
      throw e;
    }
  }

  // 同步设置相关方法

  Future<Map<String, dynamic>> getSyncSettings() async {
    try {
      final response = await client.get(
        Uri.parse('$baseUrl/api/sync/sync/settings'),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to get sync settings: ${response.statusCode}');
      }
    } catch (e) {
      print('Error getting sync settings: $e');
      throw e;
    }
  }

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

      final response = await client.put(
        Uri.parse('$baseUrl/api/sync/sync/settings')
            .replace(queryParameters: queryParams),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to update sync settings: ${response.statusCode}');
      }
    } catch (e) {
      print('Error updating sync settings: $e');
      throw e;
    }
  }

  // 辅助方法

  Future<void> syncMultipleDevices({
    required String kbId,
    required List<String> deviceIds,
    String syncType = 'bidirectional',
  }) async {
    // 并发发起多个同步任务
    final futures = deviceIds.map((deviceId) => initiateSync(
      kbId: kbId,
      targetDeviceId: deviceId,
      syncType: syncType,
    ));

    await Future.wait(futures);
  }

  // 监控同步进度
  Stream<SyncStatus> monitorSyncProgress(String syncId) async* {
    while (true) {
      try {
        final status = await getSyncStatus(syncId);
        yield status;

        // 如果同步完成或失败，停止监控
        if (status.status == 'completed' || status.status == 'failed') {
          break;
        }

        // 每秒检查一次
        await Future.delayed(Duration(seconds: 1));
      } catch (e) {
        print('Error monitoring sync progress: $e');
        break;
      }
    }
  }
}
