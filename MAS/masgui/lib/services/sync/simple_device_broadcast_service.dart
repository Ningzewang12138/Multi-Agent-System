import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../device_id_service.dart';
import '../../config/app_config.dart';

class SimpleDeviceBroadcastService {
  static final SimpleDeviceBroadcastService _instance = SimpleDeviceBroadcastService._internal();
  factory SimpleDeviceBroadcastService() => _instance;
  SimpleDeviceBroadcastService._internal();

  Timer? _registerTimer;
  bool _isRunning = false;
  
  // 注册间隔
  static const Duration registerInterval = Duration(seconds: 10);
  
  // 启动服务
  Future<void> start() async {
    if (_isRunning) return;
    
    _isRunning = true;
    
    // 立即注册一次
    await _registerDevice();
    
    // 定期注册
    _registerTimer = Timer.periodic(registerInterval, (_) async {
      await _registerDevice();
    });
    
    debugPrint('Simple device broadcast service started');
  }
  
  // 停止服务
  void stop() {
    _isRunning = false;
    _registerTimer?.cancel();
    _registerTimer = null;
    debugPrint('Simple device broadcast service stopped');
  }
  
  // 注册设备
  Future<void> _registerDevice() async {
    if (!_isRunning) return;
    
    try {
      // 获取设备信息
      final deviceInfo = await _getDeviceInfo();
      
      // 发送到服务器
      final response = await http.post(
        Uri.parse('${AppConfig.apiBaseUrl}/api/sync/device/register'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'device': deviceInfo}),
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        debugPrint('Device registered successfully');
      } else {
        debugPrint('Failed to register device: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error registering device: $e');
    }
  }
  
  // 获取设备信息
  Future<Map<String, dynamic>> _getDeviceInfo() async {
    final deviceId = await DeviceIdService().getDeviceId();
    final deviceName = await DeviceIdService().getDeviceName();
    final platform = _getPlatformName();
    final ipAddress = await _getLocalIpAddress();
    
    return {
      'id': deviceId,
      'name': deviceName,
      'type': _getDeviceType(),
      'platform': platform,
      'ip_address': ipAddress,
      'port': int.parse(AppConfig.apiBaseUrl.split(':').last.replaceAll('/', '')),
      'version': '1.0.0',
      'capabilities': ['knowledge_base', 'chat'],
      'last_seen': DateTime.now().toIso8601String(),
      'status': 'online',
    };
  }
  
  // 获取平台名称
  String _getPlatformName() {
    if (Platform.isAndroid) return 'android';
    if (Platform.isIOS) return 'ios';
    if (Platform.isWindows) return 'windows';
    if (Platform.isMacOS) return 'macos';
    if (Platform.isLinux) return 'linux';
    return 'unknown';
  }
  
  // 获取设备类型
  String _getDeviceType() {
    if (Platform.isAndroid || Platform.isIOS) {
      return 'mobile';
    } else {
      return 'desktop';
    }
  }
  
  // 获取本地IP地址
  Future<String> _getLocalIpAddress() async {
    try {
      for (var interface in await NetworkInterface.list()) {
        for (var addr in interface.addresses) {
          if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
            return addr.address;
          }
        }
      }
    } catch (e) {
      debugPrint('Failed to get local IP: $e');
    }
    return '127.0.0.1';
  }
  
  // 清理资源
  void dispose() {
    stop();
  }
}
