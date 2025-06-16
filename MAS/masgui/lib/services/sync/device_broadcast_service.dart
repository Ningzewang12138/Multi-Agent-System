import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import '../device_id_service.dart';
import '../../config/app_config.dart';

class DeviceBroadcastService {
  static final DeviceBroadcastService _instance = DeviceBroadcastService._internal();
  factory DeviceBroadcastService() => _instance;
  DeviceBroadcastService._internal();

  RawDatagramSocket? _socket;
  Timer? _broadcastTimer;
  Timer? _listenTimer;
  bool _isRunning = false;
  
  // 广播配置
  static const int broadcastPort = 8001;
  static const Duration broadcastInterval = Duration(seconds: 5);
  static const Duration deviceTimeout = Duration(seconds: 30);
  
  // 设备信息
  Map<String, Map<String, dynamic>> _discoveredDevices = {};
  final _devicesController = StreamController<List<Map<String, dynamic>>>.broadcast();
  Stream<List<Map<String, dynamic>>> get devicesStream => _devicesController.stream;
  
  // 启动广播服务
  Future<void> start() async {
    if (_isRunning) return;
    
    try {
      // 创建UDP socket
      _socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, broadcastPort);
      _socket!.broadcastEnabled = true;
      
      _isRunning = true;
      
      // 开始监听
      _startListening();
      
      // 开始广播
      _startBroadcasting();
      
      debugPrint('Device broadcast service started on port $broadcastPort');
    } catch (e) {
      debugPrint('Failed to start broadcast service: $e');
      _isRunning = false;
    }
  }
  
  // 停止广播服务
  void stop() {
    _isRunning = false;
    _broadcastTimer?.cancel();
    _listenTimer?.cancel();
    _socket?.close();
    _socket = null;
    debugPrint('Device broadcast service stopped');
  }
  
  // 开始监听广播
  void _startListening() {
    if (_socket == null) return;
    
    _socket!.listen((RawSocketEvent event) {
      if (event == RawSocketEvent.read) {
        final datagram = _socket!.receive();
        if (datagram != null) {
          _handleReceivedData(datagram.data, datagram.address);
        }
      }
    });
    
    // 定期清理离线设备
    _listenTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      _cleanupOfflineDevices();
    });
  }
  
  // 开始发送广播
  void _startBroadcasting() {
    _sendBroadcast(); // 立即发送一次
    
    _broadcastTimer = Timer.periodic(broadcastInterval, (_) {
      _sendBroadcast();
    });
  }
  
  // 发送广播消息
  void _sendBroadcast() async {
    if (_socket == null || !_isRunning) return;
    
    try {
      // 获取设备信息
      final deviceInfo = await _getDeviceInfo();
      
      // 创建广播消息
      final message = {
        'type': 'device_announcement',
        'device': deviceInfo,
      };
      
      final data = utf8.encode(json.encode(message));
      
      // 发送广播到所有网络接口
      final broadcastAddress = InternetAddress('255.255.255.255');
      _socket!.send(data, broadcastAddress, broadcastPort);
      
      debugPrint('Broadcast sent: ${deviceInfo['name']} (${deviceInfo['ip_address']})');
    } catch (e) {
      debugPrint('Failed to send broadcast: $e');
    }
  }
  
  // 处理接收到的数据
  void _handleReceivedData(List<int> data, InternetAddress address) async {
    try {
      final jsonStr = utf8.decode(data);
      final message = json.decode(jsonStr);
      
      if (message['type'] == 'device_announcement') {
        final device = message['device'] as Map<String, dynamic>;
        
        // 更新设备的实际IP地址
        device['ip_address'] = address.address;
        device['last_seen'] = DateTime.now().toIso8601String();
        
        // 忽略自己的广播
        final deviceId = device['id'];
        final myDeviceId = await DeviceIdService().getDeviceId();
        if (deviceId != myDeviceId) {
          _discoveredDevices[deviceId] = device;
          _notifyDevicesChanged();
          
          debugPrint('Device discovered: ${device['name']} (${device['ip_address']})');
        }
      }
    } catch (e) {
      debugPrint('Failed to handle received data: $e');
    }
  }
  
  // 清理离线设备
  void _cleanupOfflineDevices() {
    final now = DateTime.now();
    final toRemove = <String>[];
    
    _discoveredDevices.forEach((id, device) {
      final lastSeen = DateTime.parse(device['last_seen']);
      if (now.difference(lastSeen) > deviceTimeout) {
        toRemove.add(id);
      }
    });
    
    if (toRemove.isNotEmpty) {
      toRemove.forEach(_discoveredDevices.remove);
      _notifyDevicesChanged();
      debugPrint('Removed ${toRemove.length} offline devices');
    }
  }
  
  // 通知设备列表变化
  void _notifyDevicesChanged() {
    final devices = _discoveredDevices.values.toList();
    _devicesController.add(devices);
  }
  
  // 获取设备信息
  Future<Map<String, dynamic>> _getDeviceInfo() async {
    final deviceId = await DeviceIdService().getDeviceId();
    final deviceName = await _getDeviceName();
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
  
  // 获取设备名称
  Future<String> _getDeviceName() async {
    if (Platform.isAndroid || Platform.isIOS) {
      // 在移动设备上，使用设备ID的一部分作为名称
      final deviceId = await DeviceIdService().getDeviceId();
      return 'Mobile-${deviceId.substring(0, 8)}';
    } else if (Platform.isWindows || Platform.isMacOS || Platform.isLinux) {
      // 在桌面设备上，使用主机名
      try {
        return Platform.localHostname;
      } catch (e) {
        final deviceId = await DeviceIdService().getDeviceId();
        return 'Desktop-${deviceId.substring(0, 8)}';
      }
    }
    final deviceId = await DeviceIdService().getDeviceId();
    return 'Unknown-${deviceId.substring(0, 8)}';
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
  
  // 手动发送一次广播
  void sendBroadcast() {
    _sendBroadcast();
  }
  
  // 获取已发现的设备
  List<Map<String, dynamic>> get discoveredDevices => _discoveredDevices.values.toList();
  
  // 清理资源
  void dispose() {
    stop();
    _devicesController.close();
  }
}
