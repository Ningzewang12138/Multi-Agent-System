import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../../config/app_config.dart';

class Device {
  final String id;
  final String name;
  final String type;
  final String platform;
  final String ipAddress;
  final int port;
  final String version;
  final List<String> capabilities;
  final DateTime lastSeen;
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
      lastSeen: DateTime.parse(json['last_seen']),
      status: json['status'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'type': type,
      'platform': platform,
      'ip_address': ipAddress,
      'port': port,
      'version': version,
      'capabilities': capabilities,
      'last_seen': lastSeen.toIso8601String(),
      'status': status,
    };
  }

  bool get isOnline => status == 'online';
  bool get supportsKnowledgeBase => capabilities.contains('knowledge_base');
  bool get supportsMCP => capabilities.contains('mcp');
  bool get supportsChat => capabilities.contains('chat');
  
  String get deviceTypeIcon {
    switch (type) {
      case 'server':
        return '🖥️';
      case 'desktop':
        return '💻';
      case 'mobile':
        return '📱';
      default:
        return '📟';
    }
  }
  
  String get platformIcon {
    switch (platform.toLowerCase()) {
      case 'windows':
        return '🪟';
      case 'macos':
      case 'darwin':
        return '🍎';
      case 'linux':
        return '🐧';
      case 'android':
        return '🤖';
      case 'ios':
        return '📱';
      default:
        return '💻';
    }
  }
}

class DeviceDiscoveryService {
  static final DeviceDiscoveryService _instance = DeviceDiscoveryService._internal();
  factory DeviceDiscoveryService() => _instance;
  DeviceDiscoveryService._internal();

  final String baseUrl = AppConfig.apiBaseUrl;
  Timer? _refreshTimer;
  
  // 设备列表流
  final _devicesController = StreamController<List<Device>>.broadcast();
  Stream<List<Device>> get devicesStream => _devicesController.stream;
  
  // 当前设备信息
  Device? _currentDevice;
  Device? get currentDevice => _currentDevice;
  
  // 已发现的设备
  final Map<String, Device> _devices = {};
  List<Device> get devices => _devices.values.toList();
  List<Device> get onlineDevices => 
      _devices.values.where((d) => d.isOnline).toList();
  
  // 初始化服务
  Future<void> initialize() async {
    try {
      // 获取当前设备信息
      await _fetchCurrentDevice();
      
      // 开始定期刷新
      startAutoRefresh();
      
      // 立即获取一次设备列表
      await refreshDevices();
    } catch (e) {
      print('Failed to initialize device discovery: $e');
    }
  }
  
  // 获取当前设备信息
  Future<void> _fetchCurrentDevice() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/sync/device/info'),
      );
      
      if (response.statusCode == 200) {
        _currentDevice = Device.fromJson(json.decode(response.body));
      }
    } catch (e) {
      print('Failed to fetch current device info: $e');
    }
  }
  
  // 刷新设备列表
  Future<void> refreshDevices() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/sync/devices'),
      );
      
      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        _devices.clear();
        
        for (final deviceJson in data) {
          final device = Device.fromJson(deviceJson);
          _devices[device.id] = device;
        }
        
        _devicesController.add(devices);
      }
    } catch (e) {
      print('Failed to refresh devices: $e');
    }
  }
  
  // 手动扫描设备
  Future<void> scanDevices() async {
    try {
      await http.post(
        Uri.parse('$baseUrl/api/sync/devices/scan'),
      );
      
      // 等待一段时间后刷新列表
      await Future.delayed(const Duration(seconds: 2));
      await refreshDevices();
    } catch (e) {
      print('Failed to scan devices: $e');
    }
  }
  
  // 开始自动刷新
  void startAutoRefresh({Duration interval = const Duration(seconds: 10)}) {
    stopAutoRefresh();
    _refreshTimer = Timer.periodic(interval, (_) => refreshDevices());
  }
  
  // 停止自动刷新
  void stopAutoRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
  }
  
  // 根据ID获取设备
  Device? getDeviceById(String deviceId) {
    return _devices[deviceId];
  }
  
  // 获取可同步的设备（在线且支持知识库）
  List<Device> getSyncableDevices() {
    return onlineDevices
        .where((d) => d.supportsKnowledgeBase && d.id != _currentDevice?.id)
        .toList();
  }
  
  // 清理资源
  void dispose() {
    stopAutoRefresh();
    _devicesController.close();
  }
}
