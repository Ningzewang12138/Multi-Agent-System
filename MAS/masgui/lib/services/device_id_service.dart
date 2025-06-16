import 'dart:io';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

class DeviceIdService {
  static const String _deviceIdKey = 'device_unique_id';
  static const String _deviceNameKey = 'device_custom_name';
  
  static final DeviceIdService _instance = DeviceIdService._internal();
  factory DeviceIdService() => _instance;
  DeviceIdService._internal();
  
  String? _cachedDeviceId;
  String? _cachedDeviceName;
  
  // 获取设备唯一ID（持久化）
  Future<String> getDeviceId() async {
    if (_cachedDeviceId != null) {
      return _cachedDeviceId!;
    }
    
    final prefs = await SharedPreferences.getInstance();
    String? deviceId = prefs.getString(_deviceIdKey);
    
    if (deviceId == null) {
      // 生成新的设备ID
      deviceId = const Uuid().v4();
      await prefs.setString(_deviceIdKey, deviceId);
    }
    
    _cachedDeviceId = deviceId;
    return deviceId;
  }
  
  // 获取设备名称
  Future<String> getDeviceName() async {
    if (_cachedDeviceName != null) {
      return _cachedDeviceName!;
    }
    
    final prefs = await SharedPreferences.getInstance();
    String? deviceName = prefs.getString(_deviceNameKey);
    
    if (deviceName == null) {
      // 生成默认设备名称
      deviceName = _generateDefaultDeviceName();
      await prefs.setString(_deviceNameKey, deviceName);
    }
    
    _cachedDeviceName = deviceName;
    return deviceName;
  }
  
  // 设置自定义设备名称
  Future<void> setDeviceName(String name) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_deviceNameKey, name);
    _cachedDeviceName = name;
  }
  
  // 生成默认设备名称
  String _generateDefaultDeviceName() {
    String platform = '';
    String suffix = DateTime.now().millisecondsSinceEpoch.toString().substring(7);
    
    if (Platform.isAndroid) {
      platform = 'Android';
    } else if (Platform.isIOS) {
      platform = 'iPhone';
    } else if (Platform.isWindows) {
      platform = 'Windows';
    } else if (Platform.isMacOS) {
      platform = 'Mac';
    } else if (Platform.isLinux) {
      platform = 'Linux';
    } else {
      platform = Platform.operatingSystem;
    }
    
    // 尝试获取主机名（桌面平台）
    if (Platform.isWindows || Platform.isMacOS || Platform.isLinux) {
      try {
        final hostname = Platform.localHostname;
        if (hostname.isNotEmpty && hostname != 'localhost') {
          return hostname;
        }
      } catch (e) {
        // 忽略错误，使用默认名称
      }
    }
    
    return '$platform-$suffix';
  }
  
  // 获取设备信息
  Future<Map<String, String>> getDeviceInfo() async {
    return {
      'id': await getDeviceId(),
      'name': await getDeviceName(),
      'platform': Platform.operatingSystem,
      'version': Platform.operatingSystemVersion,
    };
  }
  
  // 重置设备ID（谨慎使用）
  Future<void> resetDeviceId() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_deviceIdKey);
    _cachedDeviceId = null;
  }
}
