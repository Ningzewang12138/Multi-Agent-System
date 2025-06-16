import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../device_id_service.dart';

/// MCP服务信息
class MCPServiceInfo {
  final String name;
  final String description;
  final List<MCPToolInfo> tools;
  final bool enabled;

  MCPServiceInfo({
    required this.name,
    required this.description,
    required this.tools,
    this.enabled = true,
  });

  factory MCPServiceInfo.fromJson(Map<String, dynamic> json) {
    return MCPServiceInfo(
      name: json['name'],
      description: json['description'],
      tools: (json['tools'] as List)
          .map((tool) => MCPToolInfo.fromJson(tool))
          .toList(),
      enabled: json['enabled'] ?? true,
    );
  }
}

/// MCP工具信息
class MCPToolInfo {
  final String name;
  final String description;
  final String category;
  final List<Map<String, dynamic>> parameters;

  MCPToolInfo({
    required this.name,
    required this.description,
    required this.category,
    required this.parameters,
  });

  factory MCPToolInfo.fromJson(Map<String, dynamic> json) {
    return MCPToolInfo(
      name: json['name'],
      description: json['description'],
      category: json['category'],
      parameters: List<Map<String, dynamic>>.from(json['parameters'] ?? []),
    );
  }
}

/// 工具调用结果
class ToolCallResult {
  final bool success;
  final dynamic result;
  final String? error;
  final Map<String, dynamic> metadata;
  final String sessionId;
  final Map<String, dynamic>? workspaceInfo;

  ToolCallResult({
    required this.success,
    required this.result,
    this.error,
    required this.metadata,
    required this.sessionId,
    this.workspaceInfo,
  });

  factory ToolCallResult.fromJson(Map<String, dynamic> json) {
    return ToolCallResult(
      success: json['success'],
      result: json['result'],
      error: json['error'],
      metadata: Map<String, dynamic>.from(json['metadata'] ?? {}),
      sessionId: json['session_id'],
      workspaceInfo: json['workspace_info'] != null
          ? Map<String, dynamic>.from(json['workspace_info'])
          : null,
    );
  }
}

/// 工作空间文件信息
class WorkspaceFileInfo {
  final String name;
  final int size;
  final String modified;
  final bool isDirectory;

  WorkspaceFileInfo({
    required this.name,
    required this.size,
    required this.modified,
    required this.isDirectory,
  });

  factory WorkspaceFileInfo.fromJson(Map<String, dynamic> json) {
    return WorkspaceFileInfo(
      name: json['name'],
      size: json['size'],
      modified: json['modified'],
      isDirectory: json['is_directory'],
    );
  }
}

/// MCP服务
class MCPService extends ChangeNotifier {
  final String _baseUrl;
  final DeviceIdService _deviceIdService;
  
  List<MCPServiceInfo> _services = [];
  bool _isLoading = false;
  String? _error;
  String? _currentSessionId;

  MCPService({
    required String baseUrl,
    required DeviceIdService deviceIdService,
  }) : _baseUrl = baseUrl,
       _deviceIdService = deviceIdService;

  // Getters
  List<MCPServiceInfo> get services => _services;
  bool get isLoading => _isLoading;
  String? get error => _error;
  String? get currentSessionId => _currentSessionId;

  /// 获取MCP服务列表
  Future<void> fetchMCPServices() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/mcp/services'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        _services = data.map((item) => MCPServiceInfo.fromJson(item)).toList();
        _error = null;
      } else {
        _error = '获取MCP服务失败: ${response.statusCode}';
      }
    } catch (e) {
      _error = '获取MCP服务出错: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 执行MCP工具
  Future<ToolCallResult?> executeTool({
    required String toolName,
    required Map<String, dynamic> parameters,
    String? sessionId,
  }) async {
    try {
      final deviceId = await _deviceIdService.getDeviceId();
      
      final requestBody = {
        'tool_name': toolName,
        'parameters': parameters,
        'device_id': deviceId,
        'session_id': sessionId ?? _currentSessionId,
      };

      final response = await http.post(
        Uri.parse('$_baseUrl/api/mcp/execute'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(requestBody),
      );

      if (response.statusCode == 200) {
        final result = ToolCallResult.fromJson(json.decode(response.body));
        _currentSessionId = result.sessionId;
        return result;
      } else {
        _error = '执行工具失败: ${response.statusCode}';
        return null;
      }
    } catch (e) {
      _error = '执行工具出错: $e';
      return null;
    }
  }

  /// 创建工作空间
  Future<Map<String, dynamic>?> createWorkspace({String? sessionId}) async {
    try {
      final deviceId = await _deviceIdService.getDeviceId();
      
      final requestBody = {
        'device_id': deviceId,
        'session_id': sessionId,
      };

      final response = await http.post(
        Uri.parse('$_baseUrl/api/mcp/workspace/create'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(requestBody),
      );

      if (response.statusCode == 200) {
        final result = json.decode(response.body);
        _currentSessionId = result['session_id'];
        return result;
      } else {
        _error = '创建工作空间失败: ${response.statusCode}';
        return null;
      }
    } catch (e) {
      _error = '创建工作空间出错: $e';
      return null;
    }
  }

  /// 列出工作空间文件
  Future<List<WorkspaceFileInfo>> listWorkspaceFiles(String sessionId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/mcp/workspace/$sessionId/files'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((item) => WorkspaceFileInfo.fromJson(item)).toList();
      } else {
        _error = '获取文件列表失败: ${response.statusCode}';
        return [];
      }
    } catch (e) {
      _error = '获取文件列表出错: $e';
      return [];
    }
  }

  /// 下载工作空间文件
  Future<Map<String, dynamic>?> downloadWorkspaceFile(
    String sessionId,
    String filename,
  ) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/mcp/workspace/$sessionId/file/$filename'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        _error = '下载文件失败: ${response.statusCode}';
        return null;
      }
    } catch (e) {
      _error = '下载文件出错: $e';
      return null;
    }
  }

  /// 上传文件到工作空间
  Future<bool> uploadFileToWorkspace(
    String sessionId,
    String filename,
    List<int> bytes,
  ) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_baseUrl/api/mcp/workspace/$sessionId/upload'),
      );

      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: filename,
        ),
      );

      final response = await request.send();
      
      if (response.statusCode == 200) {
        return true;
      } else {
        _error = '上传文件失败: ${response.statusCode}';
        return false;
      }
    } catch (e) {
      _error = '上传文件出错: $e';
      return false;
    }
  }

  /// 删除工作空间
  Future<bool> deleteWorkspace(String sessionId) async {
    try {
      final response = await http.delete(
        Uri.parse('$_baseUrl/api/mcp/workspace/$sessionId'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        if (_currentSessionId == sessionId) {
          _currentSessionId = null;
        }
        return true;
      } else {
        _error = '删除工作空间失败: ${response.statusCode}';
        return false;
      }
    } catch (e) {
      _error = '删除工作空间出错: $e';
      return false;
    }
  }

  /// 清理旧的工作空间
  Future<void> cleanupOldWorkspaces({int maxAgeHours = 24}) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/mcp/workspace/cleanup'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'max_age_hours': maxAgeHours}),
      );

      if (response.statusCode != 200) {
        _error = '清理工作空间失败: ${response.statusCode}';
      }
    } catch (e) {
      _error = '清理工作空间出错: $e';
    }
  }
}
