import 'package:flutter/material.dart';
import 'dart:async';
import '../services/sync/device_discovery_service.dart';
import '../services/sync/knowledge_base_sync_service.dart';
import '../widgets/sync_widgets.dart';

class KnowledgeBaseSyncScreen extends StatefulWidget {
  final Map<String, dynamic> knowledgeBase;

  const KnowledgeBaseSyncScreen({
    Key? key,
    required this.knowledgeBase,
  }) : super(key: key);

  @override
  State<KnowledgeBaseSyncScreen> createState() => _KnowledgeBaseSyncScreenState();
}

class _KnowledgeBaseSyncScreenState extends State<KnowledgeBaseSyncScreen> 
    with SingleTickerProviderStateMixin {
  final DeviceDiscoveryService _deviceService = DeviceDiscoveryService();
  final KnowledgeBaseSyncService _syncService = KnowledgeBaseSyncService();
  
  late TabController _tabController;
  List<Device> _devices = [];
  List<SyncRecord> _syncHistory = [];
  bool _isLoading = true;
  String? _selectedDeviceId;
  SyncType _selectedSyncType = SyncType.bidirectional;
  
  // 当前同步状态
  String? _activeSyncId;
  Timer? _syncStatusTimer;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _initializeServices();
  }

  @override
  void dispose() {
    _syncStatusTimer?.cancel();
    _deviceService.stopAutoRefresh();
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _initializeServices() async {
    setState(() => _isLoading = true);
    
    try {
      // 初始化设备发现服务
      await _deviceService.initialize();
      
      // 监听设备列表变化
      _deviceService.devicesStream.listen((devices) {
        if (mounted) {
          setState(() {
            _devices = _deviceService.getSyncableDevices();
          });
        }
      });
      
      // 加载同步历史
      await _loadSyncHistory();
      
    } catch (e) {
      print('Failed to initialize: $e');
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _loadSyncHistory() async {
    try {
      final history = await _syncService.getSyncHistory(
        kbId: widget.knowledgeBase['id'],
      );
      
      if (mounted) {
        setState(() {
          _syncHistory = history;
        });
      }
    } catch (e) {
      print('Failed to load sync history: $e');
    }
  }

  Future<void> _initiateSync() async {
    if (_selectedDeviceId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a device')),
      );
      return;
    }

    try {
      // 显示确认对话框
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Confirm Sync'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Knowledge Base: ${widget.knowledgeBase['name']}'),
              const SizedBox(height: 8),
              Text('Target Device: ${_devices.firstWhere((d) => d.id == _selectedDeviceId).name}'),
              const SizedBox(height: 8),
              Text('Sync Type: ${_getSyncTypeText(_selectedSyncType)}'),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Start Sync'),
            ),
          ],
        ),
      );

      if (confirmed != true) return;

      // 发起同步
      final syncId = await _syncService.initiateSync(
        kbId: widget.knowledgeBase['id'],
        targetDeviceId: _selectedDeviceId!,
        syncType: _selectedSyncType,
      );

      setState(() {
        _activeSyncId = syncId;
      });

      // 开始监控同步状态
      _startSyncStatusMonitoring(syncId);

      // 切换到历史标签页
      _tabController.animateTo(2);

    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to initiate sync: $e')),
      );
    }
  }

  void _startSyncStatusMonitoring(String syncId) {
    _syncStatusTimer?.cancel();
    
    _syncStatusTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      try {
        final status = await _syncService.getSyncStatus(syncId);
        
        if (status.status == SyncStatus.completed || 
            status.status == SyncStatus.failed) {
          _syncStatusTimer?.cancel();
          _activeSyncId = null;
          
          // 刷新历史
          await _loadSyncHistory();
          
          // 显示结果
          if (mounted) {
            final message = status.status == SyncStatus.completed
                ? 'Sync completed: ${status.documentsSynced} documents synced'
                : 'Sync failed: ${status.errorMessage}';
            
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(message)),
            );
          }
        }
      } catch (e) {
        print('Failed to check sync status: $e');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sync & Share'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Devices', icon: Icon(Icons.devices)),
            Tab(text: 'Settings', icon: Icon(Icons.settings)),
            Tab(text: 'History', icon: Icon(Icons.history)),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                _buildDevicesTab(),
                _buildSettingsTab(),
                _buildHistoryTab(),
              ],
            ),
    );
  }

  Widget _buildDevicesTab() {
    return Column(
      children: [
        // 当前设备信息
        if (_deviceService.currentDevice != null)
          CurrentDeviceCard(device: _deviceService.currentDevice!),
        
        // 同步控制面板
        Card(
          margin: const EdgeInsets.all(16),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Sync Knowledge Base',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 16),
                
                // 设备选择
                DropdownButtonFormField<String>(
                  value: _selectedDeviceId,
                  decoration: const InputDecoration(
                    labelText: 'Target Device',
                    border: OutlineInputBorder(),
                  ),
                  items: _devices.map((device) {
                    return DropdownMenuItem(
                      value: device.id,
                      child: Row(
                        children: [
                          Text(device.deviceTypeIcon),
                          const SizedBox(width: 8),
                          Text(device.name),
                          const SizedBox(width: 8),
                          Text(
                            '(${device.ipAddress})',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                  onChanged: (value) {
                    setState(() {
                      _selectedDeviceId = value;
                    });
                  },
                ),
                
                const SizedBox(height: 16),
                
                // 同步类型选择
                Row(
                  children: [
                    const Text('Sync Type:'),
                    const SizedBox(width: 16),
                    ChoiceChip(
                      label: const Text('Push'),
                      selected: _selectedSyncType == SyncType.push,
                      onSelected: (selected) {
                        if (selected) {
                          setState(() {
                            _selectedSyncType = SyncType.push;
                          });
                        }
                      },
                    ),
                    const SizedBox(width: 8),
                    ChoiceChip(
                      label: const Text('Pull'),
                      selected: _selectedSyncType == SyncType.pull,
                      onSelected: (selected) {
                        if (selected) {
                          setState(() {
                            _selectedSyncType = SyncType.pull;
                          });
                        }
                      },
                    ),
                    const SizedBox(width: 8),
                    ChoiceChip(
                      label: const Text('Bidirectional'),
                      selected: _selectedSyncType == SyncType.bidirectional,
                      onSelected: (selected) {
                        if (selected) {
                          setState(() {
                            _selectedSyncType = SyncType.bidirectional;
                          });
                        }
                      },
                    ),
                  ],
                ),
                
                const SizedBox(height: 16),
                
                // 同步按钮
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: _activeSyncId != null ? null : _initiateSync,
                    icon: _activeSyncId != null
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Icon(Icons.sync),
                    label: Text(_activeSyncId != null ? 'Syncing...' : 'Start Sync'),
                  ),
                ),
              ],
            ),
          ),
        ),
        
        // 可用设备列表
        Expanded(
          child: _devices.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.devices_other,
                        size: 64,
                        color: Colors.grey,
                      ),
                      const SizedBox(height: 16),
                      const Text('No devices found'),
                      const SizedBox(height: 16),
                      OutlinedButton.icon(
                        onPressed: () => _deviceService.scanDevices(),
                        icon: const Icon(Icons.refresh),
                        label: const Text('Scan Again'),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: () => _deviceService.refreshDevices(),
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: _devices.length,
                    itemBuilder: (context, index) {
                      final device = _devices[index];
                      return DeviceListTile(
                        device: device,
                        isSelected: device.id == _selectedDeviceId,
                        onTap: () {
                          setState(() {
                            _selectedDeviceId = device.id;
                          });
                        },
                      );
                    },
                  ),
                ),
        ),
      ],
    );
  }

  Widget _buildSettingsTab() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _syncService.getSyncSettings(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }

        final settings = snapshot.data!;
        
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.merge_type),
                    title: const Text('Conflict Resolution'),
                    subtitle: Text(_getConflictResolutionText(settings['conflict_resolution'])),
                    trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                    onTap: () => _showConflictResolutionDialog(settings['conflict_resolution']),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.speed),
                    title: const Text('Sync Chunk Size'),
                    subtitle: Text('${settings['chunk_size']} documents per batch'),
                    trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                    onTap: () => _showChunkSizeDialog(settings['chunk_size']),
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 16),
            
            Card(
              child: Column(
                children: [
                  SwitchListTile(
                    secondary: const Icon(Icons.sync_alt),
                    title: const Text('Auto Sync'),
                    subtitle: const Text('Automatically sync when devices are discovered'),
                    value: settings['auto_sync_enabled'] ?? false,
                    onChanged: (value) {
                      // TODO: Implement auto sync
                    },
                  ),
                  if (settings['auto_sync_enabled'] ?? false)
                    ListTile(
                      leading: const Icon(Icons.timer),
                      title: const Text('Sync Interval'),
                      subtitle: Text('Every ${settings['sync_interval'] ~/ 60} minutes'),
                      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                      onTap: () {
                        // TODO: Implement interval setting
                      },
                    ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildHistoryTab() {
    if (_syncHistory.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.history,
              size: 64,
              color: Colors.grey,
            ),
            const SizedBox(height: 16),
            const Text('No sync history'),
          ],
        ),
      );
    }

    final summary = KnowledgeBaseSyncService.calculateSyncSummary(_syncHistory);

    return Column(
      children: [
        // 统计摘要
        SyncSummaryCard(summary: summary),
        
        // 历史记录列表
        Expanded(
          child: RefreshIndicator(
            onRefresh: _loadSyncHistory,
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _syncHistory.length,
              itemBuilder: (context, index) {
                final record = _syncHistory[index];
                return SyncHistoryTile(
                  record: record,
                  isActive: record.syncId == _activeSyncId,
                );
              },
            ),
          ),
        ),
      ],
    );
  }

  void _showConflictResolutionDialog(String currentValue) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Conflict Resolution'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            RadioListTile<String>(
              title: const Text('Keep Local'),
              subtitle: const Text('Always keep local version'),
              value: 'keep_local',
              groupValue: currentValue,
              onChanged: (value) => Navigator.pop(context, value),
            ),
            RadioListTile<String>(
              title: const Text('Keep Remote'),
              subtitle: const Text('Always keep remote version'),
              value: 'keep_remote',
              groupValue: currentValue,
              onChanged: (value) => Navigator.pop(context, value),
            ),
            RadioListTile<String>(
              title: const Text('Keep Latest'),
              subtitle: const Text('Keep the most recent version'),
              value: 'keep_latest',
              groupValue: currentValue,
              onChanged: (value) => Navigator.pop(context, value),
            ),
            RadioListTile<String>(
              title: const Text('Ask'),
              subtitle: const Text('Ask for each conflict'),
              value: 'ask',
              groupValue: currentValue,
              onChanged: (value) => Navigator.pop(context, value),
            ),
          ],
        ),
      ),
    ).then((value) async {
      if (value != null && value != currentValue) {
        try {
          await _syncService.updateSyncSettings(conflictResolution: value);
          setState(() {});
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Settings updated')),
          );
        } catch (e) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to update settings: $e')),
          );
        }
      }
    });
  }

  void _showChunkSizeDialog(int currentValue) {
    final controller = TextEditingController(text: currentValue.toString());
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sync Chunk Size'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'Documents per batch',
            helperText: 'Between 1 and 1000',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final value = int.tryParse(controller.text);
              if (value != null && value >= 1 && value <= 1000) {
                Navigator.pop(context, value);
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Please enter a valid number between 1 and 1000')),
                );
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    ).then((value) async {
      if (value != null && value != currentValue) {
        try {
          await _syncService.updateSyncSettings(chunkSize: value);
          setState(() {});
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Settings updated')),
          );
        } catch (e) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to update settings: $e')),
          );
        }
      }
    });
  }

  String _getSyncTypeText(SyncType type) {
    switch (type) {
      case SyncType.push:
        return 'Push';
      case SyncType.pull:
        return 'Pull';
      case SyncType.bidirectional:
        return 'Bidirectional';
    }
  }

  String _getConflictResolutionText(String value) {
    switch (value) {
      case 'keep_local':
        return 'Keep local version';
      case 'keep_remote':
        return 'Keep remote version';
      case 'keep_latest':
        return 'Keep latest version';
      case 'ask':
        return 'Ask for each conflict';
      default:
        return value;
    }
  }
}
