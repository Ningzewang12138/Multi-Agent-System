import 'package:flutter/material.dart';
import 'package:masgui/main.dart';
import '../config/app_mode.dart';
import '../services/internet/internet_chat_service.dart';
import '../config/app_config.dart';
import '../utils/model_sync_helper.dart';

class ModeSelectionScreen extends StatefulWidget {
  const ModeSelectionScreen({Key? key}) : super(key: key);

  @override
  State<ModeSelectionScreen> createState() => _ModeSelectionScreenState();
}

class _ModeSelectionScreenState extends State<ModeSelectionScreen> {
  // Internet模式的模型选择
  String? selectedInternetModel;
  final Map<String, TextEditingController> apiKeyControllers = {};

  @override
  void initState() {
    super.initState();
    
    // 加载保存的设置
    _loadSettings();
    
    // 初始化API密钥控制器
    for (var model in InternetChatService.getAvailableModels()) {
      final modelId = model['id']!;
      apiKeyControllers[modelId] = TextEditingController();
      
      // 加载API密钥（优先使用硬编码）
      final savedKey = prefs?.getString(InternetChatService.getApiKeyStorageKey(modelId)) ?? '';
      final actualKey = InternetChatService.getApiKey(modelId, savedKey);
      apiKeyControllers[modelId]!.text = actualKey;
    }
  }

  void _loadSettings() {
    // 加载应用模式
    final savedMode = prefs?.getString('app_mode') ?? 'local';
    AppModeManager.currentMode = savedMode == 'internet' ? AppMode.internet : AppMode.local;
    
    // 加载本地子模式
    final savedSubMode = prefs?.getString('local_sub_mode') ?? 'multiAgent';
    AppModeManager.localSubMode = savedSubMode == 'ollama' ? LocalSubMode.ollama : LocalSubMode.multiAgent;
    
    // 加载服务器模式（兼容旧版本）
    AppConfig.serverMode = savedSubMode == 'ollama' ? 'ollama' : 'multiagent';
    
    // 加载选中的互联网模型
    selectedInternetModel = prefs?.getString('selected_internet_model');
  }

  void _saveSettings() async {
    // 保存应用模式
    await prefs?.setString('app_mode', AppModeManager.currentMode == AppMode.internet ? 'internet' : 'local');
    
    // 保存本地子模式
    await prefs?.setString('local_sub_mode', 
      AppModeManager.localSubMode == LocalSubMode.ollama ? 'ollama' : 'multiAgent');
    
    // 更新AppConfig的服务器模式
    AppConfig.serverMode = AppModeManager.localSubMode == LocalSubMode.ollama ? 'ollama' : 'multiagent';
    await prefs?.setString('serverMode', AppConfig.serverMode);
    
    // 保存选中的互联网模型
    if (selectedInternetModel != null) {
      await prefs?.setString('selected_internet_model', selectedInternetModel!);
    }
    
    // 保存API密钥
    for (var entry in apiKeyControllers.entries) {
      final key = InternetChatService.getApiKeyStorageKey(entry.key);
      if (entry.value.text.isNotEmpty) {
        await prefs?.setString(key, entry.value.text);
      }
    }
  }

  @override
  void dispose() {
    for (var controller in apiKeyControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mode Selection'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 主模式选择
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Select Mode',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    
                    // Local Mode
                    RadioListTile<AppMode>(
                      title: const Text('Local Mode'),
                      subtitle: const Text('Use local AI models via Ollama or Multi-Agent Server'),
                      value: AppMode.local,
                      groupValue: AppModeManager.currentMode,
                      onChanged: (value) {
                        setState(() {
                          AppModeManager.currentMode = value!;
                        });
                      },
                    ),
                    
                    // Internet Mode
                    RadioListTile<AppMode>(
                      title: const Text('Internet Mode'),
                      subtitle: const Text('Connect to external AI services (DeepSeek, Claude, ChatGPT)'),
                      value: AppMode.internet,
                      groupValue: AppModeManager.currentMode,
                      onChanged: (value) {
                        setState(() {
                          AppModeManager.currentMode = value!;
                        });
                      },
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Local Mode 子选项
            if (AppModeManager.currentMode == AppMode.local)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Local Mode Options',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 16),
                      
                      RadioListTile<LocalSubMode>(
                        title: const Text('Direct Ollama'),
                        subtitle: const Text('Connect directly to Ollama server'),
                        value: LocalSubMode.ollama,
                        groupValue: AppModeManager.localSubMode,
                        onChanged: (value) {
                          setState(() {
                            AppModeManager.localSubMode = value!;
                          });
                        },
                      ),
                      
                      RadioListTile<LocalSubMode>(
                        title: const Text('Multi-Agent Server'),
                        subtitle: const Text('Use Multi-Agent Server with RAG and MCP support'),
                        value: LocalSubMode.multiAgent,
                        groupValue: AppModeManager.localSubMode,
                        onChanged: (value) {
                          setState(() {
                            AppModeManager.localSubMode = value!;
                          });
                        },
                      ),
                    ],
                  ),
                ),
              ),
            
            // Internet Mode 选项
            if (AppModeManager.currentMode == AppMode.internet)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Internet Model Selection',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 16),
                      
                      // 模型选择
                      ...InternetChatService.getAvailableModels().map((model) {
                        final modelId = model['id']!;
                        final modelName = model['name']!;
                        final requiresKey = model['requiresApiKey'] == 'true';
                        
                        return Column(
                          children: [
                            RadioListTile<String>(
                              title: Text(modelName),
                              subtitle: requiresKey ? const Text('Requires API key') : null,
                              value: modelId,
                              groupValue: selectedInternetModel,
                              onChanged: (value) {
                                setState(() {
                                  selectedInternetModel = value;
                                });
                              },
                            ),
                            
                            // API密钥输入（如果已硬编码则显示已配置）
                            if (selectedInternetModel == modelId && requiresKey)
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                child: apiKeyControllers[modelId]!.text.isNotEmpty
                                    ? ListTile(
                                        leading: const Icon(Icons.check_circle, color: Colors.green),
                                        title: Text('API Key for $modelName'),
                                        subtitle: const Text('Already configured'),
                                        trailing: TextButton(
                                          onPressed: () {
                                            // 允许用户覆盖硬编码的密钥
                                            apiKeyControllers[modelId]!.clear();
                                            setState(() {});
                                          },
                                          child: const Text('Change'),
                                        ),
                                      )
                                    : TextField(
                                        controller: apiKeyControllers[modelId],
                                        decoration: InputDecoration(
                                          labelText: 'API Key for $modelName',
                                          hintText: 'Enter your API key',
                                          border: const OutlineInputBorder(),
                                          suffixIcon: IconButton(
                                            icon: const Icon(Icons.visibility_off),
                                            onPressed: () {
                                              // 切换密码可见性的逻辑可以在这里添加
                                            },
                                          ),
                                        ),
                                        obscureText: true,
                                      ),
                              ),
                            
                            const Divider(),
                          ],
                        );
                      }).toList(),
                      
                      // API密钥说明
                      if (selectedInternetModel != null)
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.surfaceVariant,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'How to get API keys:',
                                style: Theme.of(context).textTheme.titleSmall,
                              ),
                              const SizedBox(height: 8),
                              const Text('• DeepSeek: https://platform.deepseek.com/'),
                              const Text('• Claude: https://console.anthropic.com/'),
                              const Text('• ChatGPT: https://platform.openai.com/'),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            
            const SizedBox(height: 24),
            
            // 保存按钮
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () async {
                  // 验证Internet模式的设置
                  if (AppModeManager.currentMode == AppMode.internet) {
                    if (selectedInternetModel == null) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Please select a model for Internet mode')),
                      );
                      return;
                    }
                    
                    // 获取实际的API密钥（可能是硬编码的）
                    final storedKey = apiKeyControllers[selectedInternetModel]?.text ?? '';
                    final apiKey = InternetChatService.getApiKey(selectedInternetModel!, storedKey);
                    
                    if (apiKey.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Please enter API key for the selected model')),
                      );
                      return;
                    }
                    
                    // 测试连接
                    showDialog(
                      context: context,
                      barrierDismissible: false,
                      builder: (context) => const Center(child: CircularProgressIndicator()),
                    );
                    
                    try {
                      final service = InternetChatService();
                      final connected = await service.testConnection(
                        modelId: selectedInternetModel!,
                        apiKey: apiKey,
                      );
                      
                      Navigator.pop(context); // 关闭加载对话框
                      
                      if (!connected) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Failed to connect to API. Please check your API key.')),
                        );
                        return;
                      }
                    } catch (e) {
                      Navigator.pop(context); // 关闭加载对话框
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Connection error: $e')),
                      );
                      return;
                    }
                  }
                  
                  // 保存设置
                  _saveSettings();
                  
                  // 同步模型选择
                  ModelSyncHelper.syncModelSelection();
                  
                  // 触发主应用状态更新
                  if (setMainAppState != null) {
                    setMainAppState!(() {});
                  }
                  
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Settings saved successfully')),
                  );
                  
                  Navigator.pop(context);
                },
                child: const Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('Save and Apply'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
