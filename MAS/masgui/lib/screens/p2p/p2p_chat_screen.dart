import 'dart:async';
import 'package:flutter/material.dart';
import 'package:masgui/services/p2p/p2p_chat_service.dart';
import 'package:masgui/services/device_id_service.dart';
import 'package:intl/intl.dart';

/// P2P聊天界面
class P2PChatScreen extends StatefulWidget {
  final P2PChatSession session;
  
  const P2PChatScreen({
    Key? key,
    required this.session,
  }) : super(key: key);

  @override
  State<P2PChatScreen> createState() => _P2PChatScreenState();
}

class _P2PChatScreenState extends State<P2PChatScreen> {
  final P2PChatService _chatService = P2PChatService();
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  List<P2PChatMessage> _messages = [];
  bool _isLoading = true;
  bool _isSending = false;
  Timer? _typingTimer;
  bool _isTyping = false;
  Map<String, bool> _typingStatus = {};
  
  StreamSubscription? _messageSubscription;
  StreamSubscription? _typingSubscription;
  String? _currentDeviceId;

  @override
  void initState() {
    super.initState();
    _initialize();
  }
  
  Future<void> _initialize() async {
    _currentDeviceId = await DeviceIdService().getDeviceId();
    await _loadMessages();
    _setupListeners();
  }

  void _setupListeners() {
    // 监听新消息
    _messageSubscription = _chatService.messageStream.listen((message) {
      if (message.fromDeviceId == widget.session.otherDeviceId ||
          message.toDeviceId == widget.session.otherDeviceId) {
        setState(() {
          _messages.insert(0, message);
        });
        _scrollToBottom();
        
        // 标记已读
        if (!message.isSent(_currentDeviceId)) {
          _markMessagesRead([message.id]);
        }
      }
    });
    
    // 监听输入状态
    _typingSubscription = _chatService.typingStream.listen((data) {
      if (data['session_id'] == widget.session.sessionId) {
        setState(() {
          _typingStatus[data['device_id']] = data['is_typing'];
        });
      }
    });
  }

  Future<void> _loadMessages() async {
    try {
      final messages = await _chatService.getMessages(
        sessionId: widget.session.sessionId,
      );
      
      if (mounted) {
        setState(() {
          _messages = messages.reversed.toList();
          _isLoading = false;
        });
        
        // 标记所有未读消息为已读
        final unreadIds = messages
            .where((m) => !m.isSent(_currentDeviceId) && m.status != 'read')
            .map((m) => m.id)
            .toList();
        
        if (unreadIds.isNotEmpty) {
          _markMessagesRead(unreadIds);
        }
        
        _scrollToBottom();
      }
    } catch (e) {
      print('Error loading messages: $e');
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _markMessagesRead(List<String> messageIds) async {
    try {
      await _chatService.markMessagesRead(
        sessionId: widget.session.sessionId,
        messageIds: messageIds,
      );
    } catch (e) {
      print('Error marking messages read: $e');
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          0,
          duration: Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _handleTextChanged(String text) {
    // 发送输入状态
    if (text.isNotEmpty && !_isTyping) {
      _isTyping = true;
      _chatService.sendTypingStatus(
        sessionId: widget.session.sessionId,
        isTyping: true,
      );
    }
    
    // 重置定时器
    _typingTimer?.cancel();
    _typingTimer = Timer(Duration(seconds: 2), () {
      if (_isTyping) {
        _isTyping = false;
        _chatService.sendTypingStatus(
          sessionId: widget.session.sessionId,
          isTyping: false,
        );
      }
    });
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _isSending) return;
    
    setState(() {
      _isSending = true;
    });
    
    _messageController.clear();
    
    // 停止输入状态
    if (_isTyping) {
      _isTyping = false;
      _chatService.sendTypingStatus(
        sessionId: widget.session.sessionId,
        isTyping: false,
      );
    }
    
    try {
      final message = await _chatService.sendMessage(
        toDeviceId: widget.session.otherDeviceId,
        content: text,
      );
      
      if (message != null && mounted) {
        setState(() {
          _messages.insert(0, message);
        });
        _scrollToBottom();
      }
    } catch (e) {
      print('Error sending message: $e');
      
      // 恢复消息
      if (mounted) {
        _messageController.text = text;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to send message')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  Widget _buildMessage(P2PChatMessage message) {
    final isSent = message.isSent(_currentDeviceId);
    final timeFormat = DateFormat.Hm();
    
    return Align(
      alignment: isSent ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        child: Column(
          crossAxisAlignment: 
              isSent ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Container(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: isSent 
                    ? Theme.of(context).primaryColor 
                    : Colors.grey[300],
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(16),
                  topRight: Radius.circular(16),
                  bottomLeft: Radius.circular(isSent ? 16 : 4),
                  bottomRight: Radius.circular(isSent ? 4 : 16),
                ),
              ),
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.7,
              ),
              child: Text(
                message.content,
                style: TextStyle(
                  color: isSent ? Colors.white : Colors.black87,
                  fontSize: 16,
                ),
              ),
            ),
            SizedBox(height: 4),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  timeFormat.format(message.timestamp),
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                  ),
                ),
                if (isSent) ...[
                  SizedBox(width: 4),
                  Icon(
                    message.status == 'read' 
                        ? Icons.done_all 
                        : Icons.done,
                    size: 14,
                    color: message.status == 'read' 
                        ? Colors.blue 
                        : Colors.grey,
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTypingIndicator() {
    final isOtherTyping = _typingStatus[widget.session.otherDeviceId] ?? false;
    
    if (!isOtherTyping) return Container();
    
    return Container(
      padding: EdgeInsets.all(16),
      child: Row(
        children: [
          Container(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.grey[300],
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              children: [
                SizedBox(
                  width: 40,
                  height: 20,
                  child: Stack(
                    children: List.generate(3, (index) {
                      return AnimatedPositioned(
                        duration: Duration(milliseconds: 300),
                        curve: Curves.easeInOut,
                        left: index * 12.0,
                        bottom: 0,
                        child: AnimatedContainer(
                          duration: Duration(milliseconds: 300),
                          curve: Curves.easeInOut,
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: Colors.grey[600],
                            shape: BoxShape.circle,
                          ),
                        ),
                      );
                    }),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _messageSubscription?.cancel();
    _typingSubscription?.cancel();
    _typingTimer?.cancel();
    
    // 停止输入状态
    if (_isTyping) {
      _chatService.sendTypingStatus(
        sessionId: widget.session.sessionId,
        isTyping: false,
      );
    }
    
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: widget.session.isOnline 
                  ? Colors.green 
                  : Colors.grey,
              child: Icon(
                Icons.person,
                color: Colors.white,
                size: 20,
              ),
            ),
            SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.session.displayName,
                  style: TextStyle(fontSize: 16),
                ),
                if (widget.session.isOnline)
                  Text(
                    'Online',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.green,
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: _isLoading
                ? Center(child: CircularProgressIndicator())
                : ListView.builder(
                    controller: _scrollController,
                    reverse: true,
                    itemCount: _messages.length + 1,
                    itemBuilder: (context, index) {
                      if (index == 0) {
                        return _buildTypingIndicator();
                      }
                      return _buildMessage(_messages[index - 1]);
                    },
                  ),
          ),
          Container(
            decoration: BoxDecoration(
              color: Theme.of(context).cardColor,
              boxShadow: [
                BoxShadow(
                  offset: Offset(0, -2),
                  blurRadius: 4,
                  color: Colors.black12,
                ),
              ],
            ),
            padding: EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    onChanged: _handleTextChanged,
                    onSubmitted: (_) => _sendMessage(),
                    decoration: InputDecoration(
                      hintText: 'Type a message...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                      filled: true,
                      fillColor: Colors.grey[200],
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                    ),
                    maxLines: null,
                    textCapitalization: TextCapitalization.sentences,
                  ),
                ),
                SizedBox(width: 8),
                CircleAvatar(
                  radius: 24,
                  backgroundColor: Theme.of(context).primaryColor,
                  child: IconButton(
                    icon: Icon(
                      _isSending ? Icons.hourglass_empty : Icons.send,
                      color: Colors.white,
                    ),
                    onPressed: _isSending ? null : _sendMessage,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
