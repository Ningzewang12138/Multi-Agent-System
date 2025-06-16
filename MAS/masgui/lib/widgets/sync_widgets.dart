import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/sync/device_discovery_service.dart';
import '../services/sync/knowledge_base_sync_service.dart';

// 当前设备卡片
class CurrentDeviceCard extends StatelessWidget {
  final Device device;

  const CurrentDeviceCard({
    Key? key,
    required this.device,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      color: Theme.of(context).colorScheme.primaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.computer,
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                ),
                const SizedBox(width: 8),
                Text(
                  'This Device',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onPrimaryContainer,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Text(
                  device.deviceTypeIcon,
                  style: const TextStyle(fontSize: 24),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        device.name,
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Theme.of(context).colorScheme.onPrimaryContainer,
                        ),
                      ),
                      Text(
                        '${device.ipAddress}:${device.port}',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onPrimaryContainer.withOpacity(0.8),
                        ),
                      ),
                    ],
                  ),
                ),
                Text(
                  device.platformIcon,
                  style: const TextStyle(fontSize: 20),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// 设备列表项
class DeviceListTile extends StatelessWidget {
  final Device device;
  final bool isSelected;
  final VoidCallback? onTap;

  const DeviceListTile({
    Key? key,
    required this.device,
    this.isSelected = false,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: isSelected ? 4 : 1,
      color: isSelected 
          ? Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3)
          : null,
      child: ListTile(
        leading: Stack(
          children: [
            Text(
              device.deviceTypeIcon,
              style: const TextStyle(fontSize: 32),
            ),
            if (!device.isOnline)
              Positioned(
                right: 0,
                bottom: 0,
                child: Container(
                  padding: const EdgeInsets.all(2),
                  decoration: BoxDecoration(
                    color: Colors.red,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Icon(
                    Icons.cloud_off,
                    size: 12,
                    color: Colors.white,
                  ),
                ),
              ),
          ],
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                device.name,
                style: TextStyle(
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ),
            Text(
              device.platformIcon,
              style: const TextStyle(fontSize: 16),
            ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${device.ipAddress}:${device.port}'),
            Row(
              children: [
                _buildCapabilityChip('KB', device.supportsKnowledgeBase, context),
                const SizedBox(width: 4),
                _buildCapabilityChip('MCP', device.supportsMCP, context),
                const SizedBox(width: 4),
                _buildCapabilityChip('Chat', device.supportsChat, context),
                const Spacer(),
                Text(
                  device.isOnline ? 'Online' : 'Offline',
                  style: TextStyle(
                    fontSize: 12,
                    color: device.isOnline ? Colors.green : Colors.red,
                  ),
                ),
              ],
            ),
          ],
        ),
        onTap: device.isOnline ? onTap : null,
        selected: isSelected,
      ),
    );
  }

  Widget _buildCapabilityChip(String label, bool supported, BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: supported 
            ? Theme.of(context).colorScheme.primary.withOpacity(0.2)
            : Colors.grey.withOpacity(0.2),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          color: supported 
              ? Theme.of(context).colorScheme.primary
              : Colors.grey,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

// 同步历史记录项
class SyncHistoryTile extends StatelessWidget {
  final SyncRecord record;
  final bool isActive;

  const SyncHistoryTile({
    Key? key,
    required this.record,
    this.isActive = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('MMM d, y HH:mm');
    
    IconData statusIcon;
    Color statusColor;
    
    switch (record.status) {
      case SyncStatus.pending:
        statusIcon = Icons.schedule;
        statusColor = Colors.orange;
        break;
      case SyncStatus.inProgress:
        statusIcon = Icons.sync;
        statusColor = Colors.blue;
        break;
      case SyncStatus.completed:
        statusIcon = Icons.check_circle;
        statusColor = Colors.green;
        break;
      case SyncStatus.failed:
        statusIcon = Icons.error;
        statusColor = Colors.red;
        break;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: isActive
            ? SizedBox(
                width: 40,
                height: 40,
                child: CircularProgressIndicator(
                  strokeWidth: 3,
                  color: statusColor,
                ),
              )
            : Icon(statusIcon, color: statusColor, size: 40),
        title: Row(
          children: [
            Expanded(
              child: Text(
                '${record.sourceDeviceName ?? 'Unknown'} → ${record.targetDeviceName ?? 'Unknown'}',
                style: const TextStyle(fontWeight: FontWeight.w500),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: _getSyncTypeColor(record.syncType).withOpacity(0.2),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                record.syncType.toUpperCase(),
                style: TextStyle(
                  fontSize: 10,
                  color: _getSyncTypeColor(record.syncType),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(Icons.access_time, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text(
                  dateFormat.format(record.startedAt),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (record.duration != null) ...[
                  const SizedBox(width: 16),
                  Icon(Icons.timer, size: 14, color: Colors.grey[600]),
                  const SizedBox(width: 4),
                  Text(
                    _formatDuration(record.duration!),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ],
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                if (record.documentsSynced > 0) ...[
                  Icon(Icons.folder, size: 14, color: Colors.grey[600]),
                  const SizedBox(width: 4),
                  Text(
                    '${record.documentsSynced} docs',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(width: 16),
                ],
                if (record.conflictsCount > 0) ...[
                  const Icon(Icons.warning, size: 14, color: Colors.orange),
                  const SizedBox(width: 4),
                  Text(
                    '${record.conflictsCount} conflicts',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.orange[700],
                    ),
                  ),
                ],
              ],
            ),
            if (record.errorMessage != null) ...[
              const SizedBox(height: 4),
              Text(
                record.errorMessage!,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.red[700],
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ],
        ),
        isThreeLine: true,
      ),
    );
  }

  Color _getSyncTypeColor(String syncType) {
    switch (syncType) {
      case 'push':
        return Colors.blue;
      case 'pull':
        return Colors.purple;
      case 'bidirectional':
        return Colors.teal;
      default:
        return Colors.grey;
    }
  }

  String _formatDuration(Duration duration) {
    if (duration.inSeconds < 60) {
      return '${duration.inSeconds}s';
    } else if (duration.inMinutes < 60) {
      return '${duration.inMinutes}m ${duration.inSeconds % 60}s';
    } else {
      return '${duration.inHours}h ${duration.inMinutes % 60}m';
    }
  }
}

// 同步摘要卡片
class SyncSummaryCard extends StatelessWidget {
  final Map<String, dynamic> summary;

  const SyncSummaryCard({
    Key? key,
    required this.summary,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final successRate = summary['success_rate'] ?? 0;
    
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.analytics,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'Sync Summary',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStatItem(
                  context,
                  'Total',
                  summary['total_syncs'].toString(),
                  Icons.sync_alt,
                  Colors.blue,
                ),
                _buildStatItem(
                  context,
                  'Success',
                  summary['successful_syncs'].toString(),
                  Icons.check_circle,
                  Colors.green,
                ),
                _buildStatItem(
                  context,
                  'Failed',
                  summary['failed_syncs'].toString(),
                  Icons.error,
                  Colors.red,
                ),
                _buildStatItem(
                  context,
                  'Rate',
                  '${successRate.toStringAsFixed(0)}%',
                  Icons.trending_up,
                  successRate >= 80 ? Colors.green : Colors.orange,
                ),
              ],
            ),
            if (summary['total_documents'] > 0 || summary['total_conflicts'] > 0) ...[
              const Divider(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.folder, size: 16, color: Colors.grey),
                      const SizedBox(width: 8),
                      Text(
                        '${summary['total_documents']} documents synced',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      const Icon(Icons.warning, size: 16, color: Colors.orange),
                      const SizedBox(width: 8),
                      Text(
                        '${summary['total_conflicts']} conflicts',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}
