import 'package:flutter/material.dart';
import 'package:masgui/services/p2p/p2p_chat_service.dart';
import 'package:masgui/screens/p2p/p2p_chat_screen.dart';
import 'package:intl/intl.dart';

/// P2P聊天会话列表界面
class P2PChatListScreen extends StatefulWidget {
  const P2PChatListScreen({Key? key}) : super(key: key);

  @override
  State<P2PChatListScreen> createState() => _P2PChatListScreenState();
}

class _P2PChatListScreenState extends State<P2PChatListScreen> {
  final P2PChatService _chatService = P2PChatService();
  List<P2PChatSession> _sessions = [];
  List<Map<String, dynamic>> _onlineDevices = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    await _chatService.initialize();
    await _loadData();
    
    // 监听新消息
    _chatService.messageStream.listen((message) {
      if (mounted) {
        _loadData();
      }
    });
  }

  Future<void> _loadData() async {
    try {
      final sessions = await _chatService.getChatSessions();
      final devices = await _chatService.getOnlineDevices();
      
      if (mounted) {
        setState(() {
          _sessions = sessions;
          _onlineDevices = devices;
          _isLoading = false;
        });
      }
    } catch (e) {
      print('Error loading chat data: $e');
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Widget _buildSessionItem(P2PChatSession session) {
    final hasUnread = session.unreadCount > 0;
    final lastMessageTime = session.lastMessageAt ?? session.createdAt;
    final timeFormat = DateFormat.Hm();
    
    return ListTile(
      leading: Stack(
        children: [
          CircleAvatar(
            radius: 24,
            backgroundColor: session.isOnline ? Colors.green : Colors.grey,
            child: Icon(
              _getDeviceIcon(session.deviceType),
              color: Colors.white,
            ),
          ),
          if (session.isOnline)
            Positioned(
              right: 0,
              bottom: 0,
              child: Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: Colors.green,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2),
                ),
              ),
            ),
        ],
      ),
      title: Text(
        session.displayName,
        style: TextStyle(
          fontWeight: hasUnread ? FontWeight.bold : FontWeight.normal,
        ),
      ),
      subtitle: session.lastMessage != null
          ? Text(
              session.lastMessage!.content,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: hasUnread ? Theme.of(context).primaryColor : null,
              ),
            )
          : Text(
              'No messages yet',
              style: TextStyle(fontStyle: FontStyle.italic),
            ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            timeFormat.format(lastMessageTime),
            style: TextStyle(
              fontSize: 12,
              color: hasUnread ? Theme.of(context).primaryColor : Colors.grey,
            ),
          ),
          if (hasUnread)
            Container(
              margin: EdgeInsets.only(top: 4),
              padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Theme.of(context).primaryColor,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '${session.unreadCount}',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                ),
              ),
            ),
        ],
      ),
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (context) => P2PChatScreen(
              session: session,
            ),
          ),
        ).then((_) => _loadData());
      },
    );
  }

  Widget _buildOnlineDeviceItem(Map<String, dynamic> device) {
    final deviceId = device['id'];
    final deviceName = device['name'] ?? 'Unknown Device';
    final deviceType = device['type'] ?? 'unknown';
    
    // 检查是否已有会话
    final hasSession = _sessions.any((s) => s.otherDeviceId == deviceId);
    
    if (hasSession) return Container();
    
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: Colors.green.withOpacity(0.2),
        child: Icon(
          _getDeviceIcon(deviceType),
          color: Colors.green,
        ),
      ),
      title: Text(deviceName),
      subtitle: Text('Tap to start chat'),
      trailing: Icon(Icons.message_outlined),
      onTap: () async {
        // 发送一条初始消息来创建会话
        final message = await _chatService.sendMessage(
          toDeviceId: deviceId,
          content: 'Hi! 👋',
        );
        
        if (message != null) {
          // 刷新列表
          await _loadData();
          
          // 找到新创建的会话
          final newSession = _sessions.firstWhere(
            (s) => s.otherDeviceId == deviceId,
          );
          
          // 打开聊天界面
          if (mounted) {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (context) => P2PChatScreen(
                  session: newSession,
                ),
              ),
            );
          }
        }
      },
    );
  }

  IconData _getDeviceIcon(String deviceType) {
    switch (deviceType) {
      case 'mobile':
        return Icons.phone_android;
      case 'desktop':
        return Icons.computer;
      case 'server':
        return Icons.dns;
      default:
        return Icons.devices;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('P2P Chat'),
        actions: [
          StreamBuilder<bool>(
            stream: _chatService.connectionStream,
            initialData: _chatService.isConnected,
            builder: (context, snapshot) {
              final isConnected = snapshot.data ?? false;
              return Padding(
                padding: EdgeInsets.only(right: 16),
                child: Icon(
                  Icons.circle,
                  color: isConnected ? Colors.green : Colors.red,
                  size: 12,
                ),
              );
            },
          ),
        ],
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadData,
              child: ListView(
                children: [
                  // 会话列表
                  if (_sessions.isNotEmpty) ...[
                    Padding(
                      padding: EdgeInsets.all(16),
                      child: Text(
                        'Conversations',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    ..._sessions.map(_buildSessionItem),
                  ],
                  
                  // 在线设备
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
                    ..._onlineDevices.map(_buildOnlineDeviceItem),
                  ],
                  
                  // 空状态
                  if (_sessions.isEmpty && _onlineDevices.isEmpty)
                    Container(
                      padding: EdgeInsets.all(32),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.chat_bubble_outline,
                            size: 64,
                            color: Colors.grey,
                          ),
                          SizedBox(height: 16),
                          Text(
                            'No conversations yet',
                            style: TextStyle(
                              fontSize: 18,
                              color: Colors.grey,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Start a chat with online devices',
                            style: TextStyle(
                              color: Colors.grey,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: _loadData,
        child: Icon(Icons.refresh),
        tooltip: 'Refresh',
      ),
    );
  }
}
