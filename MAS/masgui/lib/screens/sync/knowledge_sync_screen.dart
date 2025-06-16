import 'package:flutter/material.dart';
import '../../services/multi_agent_service.dart';
import '../../services/sync/device_discovery_service.dart';
import '../../services/device_id_service.dart';

class KnowledgeSyncScreen extends StatefulWidget {
  const KnowledgeSyncScreen({super.key});

  @override
  State<KnowledgeSyncScreen> createState() => _KnowledgeSyncScreenState();
}

class _KnowledgeSyncScreenState extends State<KnowledgeSyncScreen> {
  final MultiAgentService _service = MultiAgentService();
  final DeviceDiscoveryService _deviceService = DeviceDiscoveryService();
  
  List<Map<String, dynamic>> _localKnowledgeBases = [];
  bool _isLoading = true;
  
  @override
  void initState() {
    super.initState();
    _loadData();
  }
  
  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    
    try {
      // 获取当前设备ID
      final deviceId = await DeviceIdService().getDeviceId();
      
      // 获取所有知识库（包含草稿和公开的）
      final allKbs = await _service.getKnowledgeBases(deviceId: deviceId);
      
      // 只显示当前设备的草稿知识库
      final draftKbs = allKbs.where((kb) {
        final metadata = kb['metadata'] ?? {};
        final isDraft = metadata['is_draft'] == true || 
                       metadata['is_draft'] == 1 || 
                       kb['is_draft'] == true || 
                       kb['is_draft'] == 1;
        final isMyDevice = kb['device_id'] == deviceId || 
                          metadata['device_id'] == deviceId || 
                          metadata['creator_device_id'] == deviceId;
        return isDraft && isMyDevice;
      }).toList();
      
      setState(() {
        _localKnowledgeBases = draftKbs;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading data: $e')),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }
  
  Future<void> _publishKnowledgeBase(String kbId, String kbName) async {
    // 显示确认对话框
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Publish Knowledge Base'),
        content: Text(
          'Are you sure you want to publish "$kbName"?\n\n'
          'Once published:\n'
          '• It will be visible to all devices\n'
          '• All devices can edit the content\n'
          '• You cannot unpublish it',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Publish'),
          ),
        ],
      ),
    );
    
    if (confirm != true) return;
    
    // 显示进度指示器
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: Card(
          child: Padding(
            padding: EdgeInsets.all(16.0),
            child: CircularProgressIndicator(),
          ),
        ),
      ),
    );
    
    try {
      final result = await _service.publishKnowledgeBase(kbId);
      
      // 关闭进度指示器
      if (mounted) Navigator.pop(context);
      
      // 检查是否成功（服务器返回的是 message 字段）
      if (result['message'] != null && result['message'].toString().contains('successfully')) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Published successfully!'),
              backgroundColor: Colors.green,
            ),
          );
        }
        
        // 刷新数据
        await _loadData();
      } else {
        throw Exception(result['message'] ?? 'Unknown error');
      }
    } catch (e) {
      // 关闭进度指示器
      if (mounted) Navigator.pop(context);
      
      if (mounted) {
        String errorMessage = e.toString();
        
        // 清理错误消息
        if (errorMessage.contains('Exception: ')) {
          errorMessage = errorMessage.replaceAll('Exception: ', '');
        }
        
        // 如果是名称冲突
        if (errorMessage.contains('already exists')) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('A knowledge base with this name already exists. Please rename it first.'),
              backgroundColor: Colors.orange,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Failed to publish: $errorMessage'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final currentDevice = _deviceService.currentDevice;
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Publish Knowledge Bases'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadData,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // 当前设备信息
                  if (currentDevice != null)
                    Card(
                      child: ListTile(
                        leading: Text(
                          currentDevice.deviceTypeIcon,
                          style: const TextStyle(fontSize: 24),
                        ),
                        title: Text('Current Device: ${currentDevice.name}'),
                        subtitle: Text(
                          '${currentDevice.platform} • ${currentDevice.ipAddress}:${currentDevice.port}',
                        ),
                      ),
                    ),
                  
                  const SizedBox(height: 16),
                  
                  // 本地草稿知识库
                  Text(
                    'Draft Knowledge Bases Ready to Publish',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  
                  if (_localKnowledgeBases.isEmpty)
                    const Card(
                      child: ListTile(
                        title: Text('No draft knowledge bases'),
                        subtitle: Text('Create a draft knowledge base first before publishing'),
                      ),
                    )
                  else
                    ..._localKnowledgeBases.map((kb) {
                      return Card(
                        child: ListTile(
                          title: Text(kb['name']),
                          subtitle: Text(
                            '${kb['document_count'] ?? 0} documents',
                          ),
                          trailing: FilledButton.icon(
                            icon: const Icon(Icons.cloud_upload),
                            label: const Text('Publish'),
                            onPressed: () => _publishKnowledgeBase(
                              kb['id'],
                              kb['name'],
                            ),
                          ),
                        ),
                      );
                    }),

                ],
              ),
            ),
    );
  }

}
