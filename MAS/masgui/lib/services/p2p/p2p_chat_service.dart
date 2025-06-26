import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter/foundation.dart';
import '../device_id_service.dart';
import '../../config/app_config.dart';

/// P2P聊天消息模型
class P2PChatMessage {
  final String id;
  final String fromDeviceId;
  final String toDeviceId;
  final String content;
  final String messageType;
  final DateTime timestamp;
  final String status;
  final Map<String, dynamic>? metadata;

  P2PChatMessage({
    required this.id,
    required this.fromDeviceId,
    required this.toDeviceId,
    required this.content,
    required this.messageType,
    required this.timestamp,
    required this.status,
    this.metadata,
  });

  factory P2PChatMessage.fromJson(Map<String, dynamic> json) {
    return P2PChatMessage(
      id: json['id'],
      fromDeviceId: json['from_device_id'],
      toDeviceId: json['to_device_id'],
      content: json['content'],
      messageType: json['message_type'] ?? 'text',
      timestamp: DateTime.parse(json['timestamp']),
      status: json['status'],
      metadata: json['metadata'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'from_device_id': fromDeviceId,
      'to_device_id': toDeviceId,
      'content': content,
      'message_type': messageType,
      'timestamp': timestamp.toIso8601String(),
      'status': status,
      'metadata': metadata,
    };
  }

  bool isSent(String? currentDeviceId) => fromDeviceId == currentDeviceId;
}

/// P2P聊天会话模型
class P2PChatSession {
  final String sessionId;
  final String otherDeviceId;
  final DateTime createdAt;
  final DateTime? lastMessageAt;
  final int unreadCount;
  final P2PChatMessage? lastMessage;
  final bool isOnline;
  final Map<String, dynamic>? otherDevice;

  P2PChatSession({
    required this.sessionId,
    required this.otherDeviceId,
    required this.createdAt,
    this.lastMessageAt,
    required this.unreadCount,
    this.lastMessage,
    required this.isOnline,
    this.otherDevice,
  });

  factory P2PChatSession.fromJson(Map<String, dynamic> json) {
    return P2PChatSession(
      sessionId: json['session_id'],
      otherDeviceId: json['other_device_id'],
      createdAt: DateTime.parse(json['created_at']),
      lastMessageAt: json['last_message_at'] != null
          ? DateTime.parse(json['last_message_at'])
          : null,
      unreadCount: json['unread_count'] ?? 0,
      lastMessage: json['last_message'] != null
          ? P2PChatMessage.fromJson(json['last_message'])
          : null,
      isOnline: json['is_online'] ?? false,
      otherDevice: json['other_device'],
    );
  }

  String get displayName {
    if (otherDevice != null) {
      return otherDevice!['name'] ?? 'Unknown Device';
    }
    return otherDeviceId;
  }

  String get deviceType {
    if (otherDevice != null) {
      return otherDevice!['type'] ?? 'unknown';
    }
    return 'unknown';
  }
}

/// P2P聊天服务
class P2PChatService extends ChangeNotifier {
  static final P2PChatService _instance = P2PChatService._internal();
  factory P2PChatService() => _instance;
  P2PChatService._internal();

  WebSocketChannel? _channel;
  StreamSubscription? _messageSubscription;
  String? _currentDeviceId;
  bool _isConnected = false;

  final _messagesController = StreamController<P2PChatMessage>.broadcast();
  final _typingController = StreamController<Map<String, dynamic>>.broadcast();
  final _connectionController = StreamController<bool>.broadcast();

  Stream<P2PChatMessage> get messageStream => _messagesController.stream;
  Stream<Map<String, dynamic>> get typingStream => _typingController.stream;
  Stream<bool> get connectionStream => _connectionController.stream;
  bool get isConnected => _isConnected;

  /// 初始化服务
  Future<void> initialize() async {
    _currentDeviceId = await DeviceIdService().getDeviceId();
    await _connectWebSocket();
  }

  /// 连接WebSocket
  Future<void> _connectWebSocket() async {
    try {
      final wsUrl = AppConfig.multiAgentServer
          .replaceFirst('http://', 'ws://')
          .replaceFirst('https://', 'wss://');
      
      _channel = WebSocketChannel.connect(
        Uri.parse('$wsUrl/api/p2p/chat/ws/$_currentDeviceId'),
      );

      _messageSubscription = _channel!.stream.listen(
        _handleWebSocketMessage,
        onError: (error) {
          print('WebSocket error: $error');
          _handleDisconnect();
        },
        onDone: () {
          print('WebSocket closed');
          _handleDisconnect();
        },
      );

      // 发送心跳
      _startHeartbeat();

      _isConnected = true;
      _connectionController.add(true);
      notifyListeners();
    } catch (e) {
      print('Failed to connect WebSocket: $e');
      _handleDisconnect();
    }
  }

  /// 处理WebSocket消息
  void _handleWebSocketMessage(dynamic data) {
    try {
      final message = json.decode(data);
      final type = message['type'];

      switch (type) {
        case 'connected':
          print('Connected to chat service');
          break;
        
        case 'message':
          final chatMessage = P2PChatMessage.fromJson(message['message']);
          _messagesController.add(chatMessage);
          break;
        
        case 'message_sent':
          // 消息发送确认
          break;
        
        case 'message_read':
          // 消息已读确认
          break;
        
        case 'typing_status':
          _typingController.add({
            'session_id': message['session_id'],
            'device_id': message['device_id'],
            'is_typing': message['is_typing'],
          });
          break;
        
        case 'pong':
          // 心跳响应
          break;
      }
    } catch (e) {
      print('Error handling WebSocket message: $e');
    }
  }

  /// 发送心跳
  void _startHeartbeat() {
    Timer.periodic(Duration(seconds: 30), (timer) {
      if (_isConnected && _channel != null) {
        _channel!.sink.add(json.encode({'type': 'ping'}));
      } else {
        timer.cancel();
      }
    });
  }

  /// 处理断开连接
  void _handleDisconnect() {
    _isConnected = false;
    _connectionController.add(false);
    notifyListeners();

    // 尝试重连
    Future.delayed(Duration(seconds: 5), () {
      if (!_isConnected) {
        _connectWebSocket();
      }
    });
  }

  /// 发送消息
  Future<P2PChatMessage?> sendMessage({
    required String toDeviceId,
    required String content,
    String messageType = 'text',
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.multiAgentServer}/api/p2p/chat/send'),
        headers: {
          'Content-Type': 'application/json',
          'X-Device-ID': _currentDeviceId!,
        },
        body: json.encode({
          'to_device_id': toDeviceId,
          'content': content,
          'message_type': messageType,
          'metadata': metadata,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return P2PChatMessage.fromJson(data['message']);
      } else {
        throw Exception('Failed to send message: ${response.body}');
      }
    } catch (e) {
      print('Error sending message: $e');
      return null;
    }
  }

  /// 获取聊天会话列表
  Future<List<P2PChatSession>> getChatSessions() async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.multiAgentServer}/api/p2p/chat/sessions'),
        headers: {
          'X-Device-ID': _currentDeviceId!,
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return (data['sessions'] as List)
            .map((s) => P2PChatSession.fromJson(s))
            .toList();
      } else {
        throw Exception('Failed to get sessions: ${response.body}');
      }
    } catch (e) {
      print('Error getting sessions: $e');
      return [];
    }
  }

  /// 获取会话消息
  Future<List<P2PChatMessage>> getMessages({
    required String sessionId,
    int limit = 50,
    String? beforeId,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.multiAgentServer}/api/p2p/chat/messages'),
        headers: {
          'Content-Type': 'application/json',
          'X-Device-ID': _currentDeviceId!,
        },
        body: json.encode({
          'session_id': sessionId,
          'limit': limit,
          'before_id': beforeId,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return (data['messages'] as List)
            .map((m) => P2PChatMessage.fromJson(m))
            .toList();
      } else {
        throw Exception('Failed to get messages: ${response.body}');
      }
    } catch (e) {
      print('Error getting messages: $e');
      return [];
    }
  }

  /// 标记消息已读
  Future<void> markMessagesRead({
    required String sessionId,
    required List<String> messageIds,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.multiAgentServer}/api/p2p/chat/read'),
        headers: {
          'Content-Type': 'application/json',
          'X-Device-ID': _currentDeviceId!,
        },
        body: json.encode({
          'session_id': sessionId,
          'message_ids': messageIds,
        }),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to mark messages read: ${response.body}');
      }
    } catch (e) {
      print('Error marking messages read: $e');
    }
  }

  /// 发送输入状态
  Future<void> sendTypingStatus({
    required String sessionId,
    required bool isTyping,
  }) async {
    try {
      if (_isConnected && _channel != null) {
        _channel!.sink.add(json.encode({
          'type': 'typing',
          'session_id': sessionId,
          'is_typing': isTyping,
        }));
      }
    } catch (e) {
      print('Error sending typing status: $e');
    }
  }

  /// 获取在线设备
  Future<List<Map<String, dynamic>>> getOnlineDevices() async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.multiAgentServer}/api/p2p/chat/online'),
        headers: {
          'X-Device-ID': _currentDeviceId!,
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return List<Map<String, dynamic>>.from(data['devices']);
      } else {
        throw Exception('Failed to get online devices: ${response.body}');
      }
    } catch (e) {
      print('Error getting online devices: $e');
      return [];
    }
  }

  @override
  void dispose() {
    _messageSubscription?.cancel();
    _channel?.sink.close();
    _messagesController.close();
    _typingController.close();
    _connectionController.close();
    super.dispose();
  }
}
