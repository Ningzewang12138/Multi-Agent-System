# Flutter客户端消息通信集成指南

## 概述

本指南展示如何在Flutter应用中集成客户端间的消息通信功能，支持实时聊天、消息历史和在线状态。

## 实现特点

- **WebSocket实时通信**：消息即时送达
- **消息持久化**：所有消息保存在服务器
- **离线消息**：支持离线时接收消息
- **已读回执**：消息状态追踪
- **设备发现**：自动发现其他客户端

## API端点

### WebSocket连接
```
ws://server:8000/api/messages/ws/{device_id}
```

### REST API
- `POST /api/messages/send` - 发送消息
- `POST /api/messages/list` - 获取消息列表
- `GET /api/messages/sessions` - 获取会话列表
- `GET /api/messages/online` - 获取在线设备
- `PUT /api/messages/status` - 更新消息状态
- `GET /api/messages/unread` - 获取未读数

## Flutter实现示例

### 1. 添加依赖

```yaml
dependencies:
  web_socket_channel: ^2.4.0
  http: ^1.1.0
```

### 2. 消息模型

```dart
// lib/models/message_models.dart

enum MessageType { text, image, file, system }

enum MessageStatus { pending, sent, delivered, read, failed }

class Message {
  final String id;
  final String senderId;
  final String senderName;
  final String recipientId;
  final String recipientName;
  final String content;
  final MessageType type;
  final MessageStatus status;
  final DateTime createdAt;
  final DateTime? deliveredAt;
  final DateTime? readAt;
  final Map<String, dynamic> metadata;

  Message({
    required this.id,
    required this.senderId,
    required this.senderName,
    required this.recipientId,
    required this.recipientName,
    required this.content,
    this.type = MessageType.text,
    this.status = MessageStatus.pending,
    required this.createdAt,
    this.deliveredAt,
    this.readAt,
    this.metadata = const {},
  });

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'],
      senderId: json['sender_id'],
      senderName: json['sender_name'],
      recipientId: json['recipient_id'],
      recipientName: json['recipient_name'],
      content: json['content'],
      type: MessageType.values.firstWhere(
        (e) => e.name == json['type'],
        orElse: () => MessageType.text,
      ),
      status: MessageStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => MessageStatus.sent,
      ),
      createdAt: DateTime.parse(json['created_at']),
      deliveredAt: json['delivered_at'] != null
          ? DateTime.parse(json['delivered_at'])
          : null,
      readAt: json['read_at'] != null ? DateTime.parse(json['read_at']) : null,
      metadata: json['metadata'] ?? {},
    );
  }
}

class ChatSession {
  final String id;
  final List<String> participantIds;
  final List<String> participantNames;
  final Message? lastMessage;
  final DateTime lastActivity;
  final Map<String, int> unreadCount;
  final DateTime createdAt;
  final bool? isOnline;

  ChatSession({
    required this.id,
    required this.participantIds,
    required this.participantNames,
    this.lastMessage,
    required this.lastActivity,
    this.unreadCount = const {},
    required this.createdAt,
    this.isOnline,
  });

  factory ChatSession.fromJson(Map<String, dynamic> json) {
    return ChatSession(
      id: json['id'],
      participantIds: List<String>.from(json['participant_ids']),
      participantNames: List<String>.from(json['participant_names']),
      lastMessage: json['last_message'] != null
          ? Message.fromJson(json['last_message'])
          : null,
      lastActivity: DateTime.parse(json['last_activity']),
      unreadCount: Map<String, int>.from(json['unread_count'] ?? {}),
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
```

### 3. 消息服务

```dart
// lib/services/message_service.dart

import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

class MessageService {
  final String baseUrl;
  final String deviceId;
  final String deviceName;
  
  WebSocketChannel? _channel;
  final _messageController = StreamController<Message>.broadcast();
  final _connectionController = StreamController<bool>.broadcast();
  final _typingController = StreamController<Map<String, bool>>.broadcast();
  
  Stream<Message> get messageStream => _messageController.stream;
  Stream<bool> get connectionStream => _connectionController.stream;
  Stream<Map<String, bool>> get typingStream => _typingController.stream;
  
  Timer? _heartbeatTimer;
  
  MessageService({
    required this.baseUrl,
    required this.deviceId,
    required this.deviceName,
  });
  
  // 连接WebSocket
  Future<void> connect() async {
    try {
      final wsUrl = baseUrl.replaceFirst('http', 'ws');
      _channel = WebSocketChannel.connect(
        Uri.parse('$wsUrl/api/messages/ws/$deviceId'),
      );
      
      _connectionController.add(true);
      
      // 监听消息
      _channel!.stream.listen(
        (data) {
          final json = jsonDecode(data);
          _handleWebSocketMessage(json);
        },
        onError: (error) {
          print('WebSocket error: $error');
          _connectionController.add(false);
        },
        onDone: () {
          _connectionController.add(false);
          // 自动重连
          Future.delayed(Duration(seconds: 5), connect);
        },
      );
      
      // 发送心跳
      _startHeartbeat();
      
    } catch (e) {
      print('Failed to connect WebSocket: $e');
      _connectionController.add(false);
    }
  }
  
  // 处理WebSocket消息
  void _handleWebSocketMessage(Map<String, dynamic> data) {
    switch (data['type']) {
      case 'message':
        final message = Message.fromJson(data['message']);
        _messageController.add(message);
        break;
        
      case 'receipt':
        // 处理消息回执
        print('Message ${data['message_id']} status: ${data['status']}');
        break;
        
      case 'typing':
        // 处理输入状态
        _typingController.add({
          data['sender_id']: data['is_typing'],
        });
        break;
        
      case 'connection':
        print('Connection status: ${data['status']}');
        break;
    }
  }
  
  // 发送心跳
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(Duration(seconds: 30), (_) {
      _channel?.sink.add(jsonEncode({'type': 'ping'}));
    });
  }
  
  // 发送消息
  Future<Map<String, dynamic>> sendMessage({
    required String recipientId,
    required String content,
    MessageType type = MessageType.text,
    Map<String, dynamic>? metadata,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/messages/send'),
      headers: {
        'Content-Type': 'application/json',
        'X-Device-ID': deviceId,
      },
      body: jsonEncode({
        'recipient_id': recipientId,
        'content': content,
        'type': type.name,
        'metadata': metadata ?? {},
      }),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to send message: ${response.body}');
    }
  }
  
  // 获取消息列表
  Future<List<Message>> getMessages({
    String? sessionId,
    String? deviceId,
    int limit = 50,
    String? beforeId,
    String? afterId,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/messages/list'),
      headers: {
        'Content-Type': 'application/json',
        'X-Device-ID': this.deviceId,
      },
      body: jsonEncode({
        if (sessionId != null) 'session_id': sessionId,
        if (deviceId != null) 'device_id': deviceId,
        'limit': limit,
        if (beforeId != null) 'before_id': beforeId,
        if (afterId != null) 'after_id': afterId,
      }),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return (data['messages'] as List)
          .map((json) => Message.fromJson(json))
          .toList();
    } else {
      throw Exception('Failed to get messages: ${response.body}');
    }
  }
  
  // 获取会话列表
  Future<List<ChatSession>> getSessions() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/messages/sessions'),
      headers: {'X-Device-ID': deviceId},
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return (data['sessions'] as List)
          .map((json) => ChatSession.fromJson(json))
          .toList();
    } else {
      throw Exception('Failed to get sessions: ${response.body}');
    }
  }
  
  // 获取在线设备
  Future<List<Map<String, dynamic>>> getOnlineDevices() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/messages/online'),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return List<Map<String, dynamic>>.from(data['online_devices']);
    } else {
      throw Exception('Failed to get online devices: ${response.body}');
    }
  }
  
  // 更新消息状态
  Future<void> updateMessageStatus(
    List<String> messageIds,
    MessageStatus status,
  ) async {
    final response = await http.put(
      Uri.parse('$baseUrl/api/messages/status'),
      headers: {
        'Content-Type': 'application/json',
        'X-Device-ID': deviceId,
      },
      body: jsonEncode({
        'message_ids': messageIds,
        'status': status.name,
      }),
    );
    
    if (response.statusCode != 200) {
      throw Exception('Failed to update message status: ${response.body}');
    }
  }
  
  // 发送输入状态
  void sendTypingIndicator(String recipientId, bool isTyping) {
    _channel?.sink.add(jsonEncode({
      'type': 'typing',
      'recipient_id': recipientId,
      'is_typing': isTyping,
    }));
  }
  
  // 断开连接
  void disconnect() {
    _heartbeatTimer?.cancel();
    _channel?.sink.close();
    _messageController.close();
    _connectionController.close();
    _typingController.close();
  }
}
```

### 4. 聊天界面示例

```dart
// lib/screens/chat_screen.dart

import 'package:flutter/material.dart';
import '../services/message_service.dart';
import '../models/message_models.dart';

class ChatScreen extends StatefulWidget {
  final String recipientId;
  final String recipientName;
  final String deviceId;
  final String deviceName;
  final String serverUrl;
  
  const ChatScreen({
    Key? key,
    required this.recipientId,
    required this.recipientName,
    required this.deviceId,
    required this.deviceName,
    required this.serverUrl,
  }) : super(key: key);
  
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late MessageService _messageService;
  final TextEditingController _textController = TextEditingController();
  final List<Message> _messages = [];
  bool _isConnected = false;
  bool _isTyping = false;
  Timer? _typingTimer;
  
  @override
  void initState() {
    super.initState();
    _initializeService();
  }
  
  void _initializeService() async {
    _messageService = MessageService(
      baseUrl: widget.serverUrl,
      deviceId: widget.deviceId,
      deviceName: widget.deviceName,
    );
    
    // 监听连接状态
    _messageService.connectionStream.listen((connected) {
      setState(() {
        _isConnected = connected;
      });
    });
    
    // 监听新消息
    _messageService.messageStream.listen((message) {
      if (message.senderId == widget.recipientId ||
          message.recipientId == widget.recipientId) {
        setState(() {
          _messages.add(message);
        });
        
        // 标记为已读
        if (message.recipientId == widget.deviceId) {
          _messageService.updateMessageStatus(
            [message.id],
            MessageStatus.read,
          );
        }
      }
    });
    
    // 监听输入状态
    _messageService.typingStream.listen((typing) {
      setState(() {
        _isTyping = typing[widget.recipientId] ?? false;
      });
    });
    
    // 连接WebSocket
    await _messageService.connect();
    
    // 加载历史消息
    _loadMessages();
  }
  
  void _loadMessages() async {
    try {
      final messages = await _messageService.getMessages(
        deviceId: widget.recipientId,
        limit: 50,
      );
      setState(() {
        _messages.clear();
        _messages.addAll(messages);
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load messages: $e')),
      );
    }
  }
  
  void _sendMessage() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    
    _textController.clear();
    _stopTyping();
    
    try {
      await _messageService.sendMessage(
        recipientId: widget.recipientId,
        content: text,
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to send message: $e')),
      );
    }
  }
  
  void _onTextChanged(String text) {
    if (text.isNotEmpty && _typingTimer == null) {
      // 开始输入
      _messageService.sendTypingIndicator(widget.recipientId, true);
    }
    
    // 重置输入计时器
    _typingTimer?.cancel();
    _typingTimer = Timer(Duration(seconds: 2), _stopTyping);
  }
  
  void _stopTyping() {
    _typingTimer?.cancel();
    _typingTimer = null;
    _messageService.sendTypingIndicator(widget.recipientId, false);
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.recipientName),
            if (_isTyping)
              Text(
                'typing...',
                style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
              ),
          ],
        ),
        actions: [
          Container(
            width: 12,
            height: 12,
            margin: EdgeInsets.only(right: 16),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _isConnected ? Colors.green : Colors.red,
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              reverse: true,
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[_messages.length - 1 - index];
                final isMe = message.senderId == widget.deviceId;
                
                return Align(
                  alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                    padding: EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isMe ? Colors.blue : Colors.grey[300],
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          message.content,
                          style: TextStyle(
                            color: isMe ? Colors.white : Colors.black,
                          ),
                        ),
                        SizedBox(height: 4),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              _formatTime(message.createdAt),
                              style: TextStyle(
                                fontSize: 10,
                                color: isMe ? Colors.white70 : Colors.black54,
                              ),
                            ),
                            if (isMe) ...[
                              SizedBox(width: 4),
                              Icon(
                                _getStatusIcon(message.status),
                                size: 12,
                                color: Colors.white70,
                              ),
                            ],
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          Container(
            padding: EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black12,
                  blurRadius: 4,
                  offset: Offset(0, -2),
                ),
              ],
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _textController,
                    onChanged: _onTextChanged,
                    decoration: InputDecoration(
                      hintText: 'Type a message...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                      ),
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                SizedBox(width: 8),
                IconButton(
                  icon: Icon(Icons.send),
                  onPressed: _sendMessage,
                  color: Colors.blue,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  String _formatTime(DateTime time) {
    return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }
  
  IconData _getStatusIcon(MessageStatus status) {
    switch (status) {
      case MessageStatus.sent:
        return Icons.check;
      case MessageStatus.delivered:
        return Icons.done_all;
      case MessageStatus.read:
        return Icons.done_all;
      default:
        return Icons.access_time;
    }
  }
  
  @override
  void dispose() {
    _stopTyping();
    _messageService.disconnect();
    _textController.dispose();
    super.dispose();
  }
}
```

### 5. 会话列表界面

```dart
// lib/screens/sessions_screen.dart

import 'package:flutter/material.dart';
import '../services/message_service.dart';
import '../models/message_models.dart';
import 'chat_screen.dart';

class SessionsScreen extends StatefulWidget {
  final String deviceId;
  final String deviceName;
  final String serverUrl;
  
  const SessionsScreen({
    Key? key,
    required this.deviceId,
    required this.deviceName,
    required this.serverUrl,
  }) : super(key: key);
  
  @override
  _SessionsScreenState createState() => _SessionsScreenState();
}

class _SessionsScreenState extends State<SessionsScreen> {
  late MessageService _messageService;
  List<ChatSession> _sessions = [];
  List<Map<String, dynamic>> _onlineDevices = [];
  bool _isLoading = true;
  
  @override
  void initState() {
    super.initState();
    _initializeService();
  }
  
  void _initializeService() async {
    _messageService = MessageService(
      baseUrl: widget.serverUrl,
      deviceId: widget.deviceId,
      deviceName: widget.deviceName,
    );
    
    // 监听新消息以更新会话列表
    _messageService.messageStream.listen((_) {
      _loadSessions();
    });
    
    await _messageService.connect();
    _loadData();
  }
  
  void _loadData() async {
    setState(() {
      _isLoading = true;
    });
    
    try {
      final sessions = await _messageService.getSessions();
      final onlineDevices = await _messageService.getOnlineDevices();
      
      setState(() {
        _sessions = sessions;
        _onlineDevices = onlineDevices;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load data: $e')),
      );
    }
  }
  
  void _loadSessions() async {
    try {
      final sessions = await _messageService.getSessions();
      setState(() {
        _sessions = sessions;
      });
    } catch (e) {
      // Silent update failure
    }
  }
  
  void _openChat(String deviceId, String deviceName) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ChatScreen(
          recipientId: deviceId,
          recipientName: deviceName,
          deviceId: widget.deviceId,
          deviceName: widget.deviceName,
          serverUrl: widget.serverUrl,
        ),
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Messages'),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () async => _loadData(),
              child: ListView(
                children: [
                  // Online devices section
                  if (_onlineDevices.isNotEmpty) ...[
                    Padding(
                      padding: EdgeInsets.all(16),
                      child: Text(
                        'Online Devices',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    ..._onlineDevices.map((device) {
                      final hasSession = _sessions.any((s) =>
                          s.participantIds.contains(device['id']));
                      
                      if (!hasSession && device['id'] != widget.deviceId) {
                        return ListTile(
                          leading: CircleAvatar(
                            backgroundColor: Colors.green,
                            child: Text(device['name'][0].toUpperCase()),
                          ),
                          title: Text(device['name']),
                          subtitle: Text('${device['type']} - ${device['platform']}'),
                          trailing: Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: Colors.green,
                            ),
                          ),
                          onTap: () => _openChat(device['id'], device['name']),
                        );
                      }
                      return SizedBox.shrink();
                    }).toList(),
                  ],
                  
                  // Sessions section
                  if (_sessions.isNotEmpty) ...[
                    Padding(
                      padding: EdgeInsets.all(16),
                      child: Text(
                        'Recent Chats',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    ..._sessions.map((session) {
                      final otherParticipant = session.participantNames
                          .firstWhere((name) => name != widget.deviceName,
                              orElse: () => 'Unknown');
                      final otherParticipantId = session.participantIds
                          .firstWhere((id) => id != widget.deviceId,
                              orElse: () => '');
                      
                      final isOnline = _onlineDevices
                          .any((d) => d['id'] == otherParticipantId);
                      
                      final unreadCount =
                          session.unreadCount[widget.deviceId] ?? 0;
                      
                      return ListTile(
                        leading: Stack(
                          children: [
                            CircleAvatar(
                              child: Text(otherParticipant[0].toUpperCase()),
                            ),
                            if (isOnline)
                              Positioned(
                                right: 0,
                                bottom: 0,
                                child: Container(
                                  width: 12,
                                  height: 12,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: Colors.green,
                                    border: Border.all(
                                      color: Colors.white,
                                      width: 2,
                                    ),
                                  ),
                                ),
                              ),
                          ],
                        ),
                        title: Text(otherParticipant),
                        subtitle: session.lastMessage != null
                            ? Text(
                                session.lastMessage!.content,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              )
                            : Text('No messages'),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              _formatTime(session.lastActivity),
                              style: TextStyle(fontSize: 12),
                            ),
                            if (unreadCount > 0)
                              Container(
                                margin: EdgeInsets.only(top: 4),
                                padding: EdgeInsets.symmetric(
                                  horizontal: 8,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: Colors.blue,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(
                                  unreadCount.toString(),
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                          ],
                        ),
                        onTap: () => _openChat(
                          otherParticipantId,
                          otherParticipant,
                        ),
                      );
                    }).toList(),
                  ],
                  
                  if (_sessions.isEmpty && _onlineDevices.length <= 1)
                    Center(
                      child: Padding(
                        padding: EdgeInsets.all(32),
                        child: Text(
                          'No devices found.\nMake sure other devices are online.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.grey),
                        ),
                      ),
                    ),
                ],
              ),
            ),
    );
  }
  
  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final diff = now.difference(time);
    
    if (diff.inDays > 0) {
      return '${diff.inDays}d ago';
    } else if (diff.inHours > 0) {
      return '${diff.inHours}h ago';
    } else if (diff.inMinutes > 0) {
      return '${diff.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }
  
  @override
  void dispose() {
    _messageService.disconnect();
    super.dispose();
  }
}
```

## 使用示例

```dart
// 在应用中使用
void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MAS Chat',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: SessionsScreen(
        deviceId: 'flutter-device-${DateTime.now().millisecondsSinceEpoch}',
        deviceName: 'Flutter Device',
        serverUrl: 'http://192.168.1.100:8000', // 替换为实际服务器地址
      ),
    );
  }
}
```

## 测试步骤

1. **启动服务器**
   ```bash
   cd server
   python main.py
   ```

2. **运行测试脚本**
   ```bash
   # 测试基本功能
   python tests/test_messaging.py
   
   # 交互式聊天
   python tests/test_messaging.py chat
   ```

3. **运行Flutter应用**
   ```bash
   cd masgui
   flutter run
   ```

## 功能特性

1. **实时消息**：通过WebSocket实现消息即时推送
2. **离线消息**：服务器保存所有消息，上线后可接收
3. **消息状态**：已发送、已送达、已读状态追踪
4. **输入指示器**：显示对方正在输入
5. **在线状态**：实时显示设备在线状态
6. **消息持久化**：所有消息保存在服务器数据库

## 注意事项

1. 确保服务器和客户端在同一网络
2. 防火墙需要开放8000端口
3. WebSocket连接会自动重连
4. 消息使用SQLite存储，支持大量消息

## 故障排除

1. **连接失败**
   - 检查服务器是否运行
   - 确认IP地址和端口正确
   - 检查防火墙设置

2. **消息发送失败**
   - 确认接收设备在线
   - 检查网络连接
   - 查看服务器日志

3. **WebSocket断开**
   - 会自动重连
   - 检查网络稳定性
   - 确认服务器正常运行
