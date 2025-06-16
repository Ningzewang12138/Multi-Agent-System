import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_config.dart';

class KnowledgeBaseSettingsScreen extends StatefulWidget {
  const KnowledgeBaseSettingsScreen({Key? key}) : super(key: key);

  @override
  State<KnowledgeBaseSettingsScreen> createState() => _KnowledgeBaseSettingsScreenState();
}

class _KnowledgeBaseSettingsScreenState extends State<KnowledgeBaseSettingsScreen> {
  late SharedPreferences _prefs;
  bool _isLoading = true;
  
  // 设置项
  bool _enableLocalKnowledgeBase = true;
  bool _enableServerKnowledgeBase = true;
  bool _autoSyncOnCreate = false;
  bool _preferLocalRAG = true;
  String _localOllamaUrl = 'http://localhost:11434';
  String _localEmbeddingModel = 'nomic-embed-text:latest';
  
  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    _prefs = await SharedPreferences.getInstance();
    
    setState(() {
      _enableLocalKnowledgeBase = _prefs.getBool('enableLocalKnowledgeBase') ?? true;
      _enableServerKnowledgeBase = _prefs.getBool('enableServerKnowledgeBase') ?? true;
      _autoSyncOnCreate = _prefs.getBool('autoSyncOnCreate') ?? false;
      _preferLocalRAG = _prefs.getBool('preferLocalRAG') ?? true;
      _localOllamaUrl = _prefs.getString('localOllamaUrl') ?? 'http://localhost:11434';
      _localEmbeddingModel = _prefs.getString('localEmbeddingModel') ?? 'nomic-embed-text:latest';
      _isLoading = false;
    });
  }

  Future<void> _saveSettings() async {
    await _prefs.setBool('enableLocalKnowledgeBase', _enableLocalKnowledgeBase);
    await _prefs.setBool('enableServerKnowledgeBase', _enableServerKnowledgeBase);
    await _prefs.setBool('autoSyncOnCreate', _autoSyncOnCreate);
    await _prefs.setBool('preferLocalRAG', _preferLocalRAG);
    await _prefs.setString('localOllamaUrl', _localOllamaUrl);
    await _prefs.setString('localEmbeddingModel', _localEmbeddingModel);
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Settings saved')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Knowledge Base Settings'),
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _saveSettings,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // 知识库模式
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Knowledge Base Mode',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  SwitchListTile(
                    title: const Text('Enable Local Knowledge Base'),
                    subtitle: const Text('Store and manage knowledge bases on this device'),
                    value: _enableLocalKnowledgeBase,
                    onChanged: (value) {
                      setState(() {
                        _enableLocalKnowledgeBase = value;
                      });
                    },
                  ),
                  SwitchListTile(
                    title: const Text('Enable Server Knowledge Base'),
                    subtitle: const Text('Use knowledge bases from the multi-agent server'),
                    value: _enableServerKnowledgeBase,
                    onChanged: AppConfig.serverMode == 'multiagent' 
                        ? (value) {
                            setState(() {
                              _enableServerKnowledgeBase = value;
                            });
                          }
                        : null,
                  ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // 同步设置
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Sync Settings',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  SwitchListTile(
                    title: const Text('Auto Sync on Create'),
                    subtitle: const Text('Automatically upload local knowledge bases to server after creation'),
                    value: _autoSyncOnCreate,
                    enabled: _enableLocalKnowledgeBase && _enableServerKnowledgeBase,
                    onChanged: (value) {
                      setState(() {
                        _autoSyncOnCreate = value;
                      });
                    },
                  ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // RAG设置
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'RAG Settings',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  SwitchListTile(
                    title: const Text('Prefer Local RAG'),
                    subtitle: const Text('Use local processing for RAG when possible (requires local Ollama)'),
                    value: _preferLocalRAG,
                    enabled: _enableLocalKnowledgeBase,
                    onChanged: (value) {
                      setState(() {
                        _preferLocalRAG = value;
                      });
                    },
                  ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // 本地Ollama设置
          if (_enableLocalKnowledgeBase) Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Local Ollama Settings',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    decoration: const InputDecoration(
                      labelText: 'Local Ollama URL',
                      border: OutlineInputBorder(),
                      helperText: 'URL of your local Ollama instance',
                    ),
                    controller: TextEditingController(text: _localOllamaUrl),
                    onChanged: (value) {
                      _localOllamaUrl = value;
                    },
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    decoration: const InputDecoration(
                      labelText: 'Embedding Model',
                      border: OutlineInputBorder(),
                      helperText: 'Model to use for generating embeddings',
                    ),
                    controller: TextEditingController(text: _localEmbeddingModel),
                    onChanged: (value) {
                      _localEmbeddingModel = value;
                    },
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: _testLocalOllama,
                    icon: const Icon(Icons.network_check),
                    label: const Text('Test Connection'),
                  ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // 统计信息
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Statistics',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  FutureBuilder<Map<String, dynamic>>(
                    future: _getStatistics(),
                    builder: (context, snapshot) {
                      if (snapshot.hasData) {
                        final stats = snapshot.data!;
                        return Column(
                          children: [
                            ListTile(
                              leading: const Icon(Icons.folder),
                              title: const Text('Local Knowledge Bases'),
                              trailing: Text('${stats['local_kb_count'] ?? 0}'),
                            ),
                            ListTile(
                              leading: const Icon(Icons.description),
                              title: const Text('Total Documents'),
                              trailing: Text('${stats['total_documents'] ?? 0}'),
                            ),
                            ListTile(
                              leading: const Icon(Icons.sync),
                              title: const Text('Synced Knowledge Bases'),
                              trailing: Text('${stats['synced_kb_count'] ?? 0}'),
                            ),
                          ],
                        );
                      }
                      return const Center(child: CircularProgressIndicator());
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _testLocalOllama() async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const AlertDialog(
        content: Row(
          children: [
            CircularProgressIndicator(),
            SizedBox(width: 16),
            Text('Testing connection...'),
          ],
        ),
      ),
    );

    try {
      final service = LocalRAGService();
      final available = await service.isOllamaAvailable();
      
      Navigator.pop(context);
      
      if (available) {
        final models = await service.getLocalModels();
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Connection Successful'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Local Ollama is running!'),
                const SizedBox(height: 8),
                Text('Available models: ${models.length}'),
                ...models.take(5).map((m) => Text('• $m')),
                if (models.length > 5) Text('... and ${models.length - 5} more'),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      } else {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Connection Failed'),
            content: const Text('Could not connect to local Ollama. Please make sure it is running.'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  Future<Map<String, dynamic>> _getStatistics() async {
    final service = UnifiedKnowledgeBaseService();
    return await service.getStatistics();
  }
}
