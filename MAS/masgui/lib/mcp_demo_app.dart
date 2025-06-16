import 'package:flutter/material.dart';
import 'screens/tool_enhanced_chat_screen.dart';

/// MCP工具调用演示应用
class MCPDemoApp extends StatelessWidget {
  const MCPDemoApp({Key? key}) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MAS MCP Tool Demo',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: const MCPDemoHomePage(),
    );
  }
}

/// 演示应用主页
class MCPDemoHomePage extends StatefulWidget {
  const MCPDemoHomePage({Key? key}) : super(key: key);
  
  @override
  State<MCPDemoHomePage> createState() => _MCPDemoHomePageState();
}

class _MCPDemoHomePageState extends State<MCPDemoHomePage> {
  final TextEditingController _serverUrlController = TextEditingController(
    text: 'http://localhost:8000',
  );
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MAS MCP Tool Demo'),
        centerTitle: true,
      ),
      body: Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 400),
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Logo或图标
              Icon(
                Icons.build_circle,
                size: 80,
                color: Theme.of(context).primaryColor,
              ),
              const SizedBox(height: 24),
              
              // 标题
              Text(
                'MCP Tool-Enhanced Chat',
                style: Theme.of(context).textTheme.headlineMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              
              // 描述
              Text(
                'Use natural language to create, read, and manage files',
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              
              // 服务器地址输入
              TextField(
                controller: _serverUrlController,
                decoration: const InputDecoration(
                  labelText: 'Server URL',
                  hintText: 'http://localhost:8000',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.cloud),
                ),
              ),
              const SizedBox(height: 24),
              
              // 开始按钮
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => ToolEnhancedChatScreen(
                          serverUrl: _serverUrlController.text,
                        ),
                      ),
                    );
                  },
                  child: const Text('Start Chat'),
                ),
              ),
              const SizedBox(height: 16),
              
              // 功能列表
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Supported Commands:',
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      const SizedBox(height: 8),
                      _buildFeature('📝 Create files with content'),
                      _buildFeature('📂 List files in workspace'),
                      _buildFeature('📖 Read file contents'),
                      _buildFeature('🗑️ Delete files'),
                      _buildFeature('🔄 Session-based workspace'),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildFeature(String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          const Icon(Icons.check_circle, size: 16, color: Colors.green),
          const SizedBox(width: 8),
          Text(text, style: const TextStyle(fontSize: 14)),
        ],
      ),
    );
  }
  
  @override
  void dispose() {
    _serverUrlController.dispose();
    super.dispose();
  }
}

void main() {
  runApp(const MCPDemoApp());
}
