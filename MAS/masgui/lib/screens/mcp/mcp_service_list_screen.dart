import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/mcp/mcp_service.dart';
import 'mcp_tool_detail_screen.dart';

class MCPServiceListScreen extends StatefulWidget {
  const MCPServiceListScreen({Key? key}) : super(key: key);

  @override
  State<MCPServiceListScreen> createState() => _MCPServiceListScreenState();
}

class _MCPServiceListScreenState extends State<MCPServiceListScreen> {
  @override
  void initState() {
    super.initState();
    // 获取MCP服务列表
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<MCPService>().fetchMCPServices();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MCP服务'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              context.read<MCPService>().fetchMCPServices();
            },
          ),
          IconButton(
            icon: const Icon(Icons.cleaning_services),
            onPressed: () => _showCleanupDialog(context),
            tooltip: '清理旧工作空间',
          ),
        ],
      ),
      body: Consumer<MCPService>(
        builder: (context, mcpService, child) {
          if (mcpService.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (mcpService.error != null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, size: 64, color: Colors.red),
                  const SizedBox(height: 16),
                  Text(
                    '加载失败',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    mcpService.error!,
                    style: Theme.of(context).textTheme.bodyMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => mcpService.fetchMCPServices(),
                    child: const Text('重试'),
                  ),
                ],
              ),
            );
          }

          if (mcpService.services.isEmpty) {
            return const Center(
              child: Text('暂无可用的MCP服务'),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: mcpService.services.length,
            itemBuilder: (context, index) {
              final service = mcpService.services[index];
              return _buildServiceCard(context, service);
            },
          );
        },
      ),
    );
  }

  Widget _buildServiceCard(BuildContext context, MCPServiceInfo service) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 2,
      child: ExpansionTile(
        leading: Icon(
          _getServiceIcon(service.name),
          size: 32,
          color: service.enabled ? Theme.of(context).primaryColor : Colors.grey,
        ),
        title: Text(
          service.name,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text(service.description),
        trailing: Chip(
          label: Text('${service.tools.length} 个工具'),
          backgroundColor: Theme.of(context).primaryColor.withOpacity(0.1),
        ),
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '可用工具：',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                ...service.tools.map((tool) => _buildToolTile(context, tool)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildToolTile(BuildContext context, MCPToolInfo tool) {
    // 先获取MCPService的引用
    final mcpService = context.read<MCPService>();
    
    return ListTile(
      dense: true,
      leading: Icon(
        _getToolIcon(tool.name),
        size: 20,
        color: Theme.of(context).primaryColor,
      ),
      title: Text(tool.name),
      subtitle: Text(
        tool.description,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ChangeNotifierProvider<MCPService>.value(
              value: mcpService,  // 使用之前获取的引用
              child: MCPToolDetailScreen(tool: tool),
            ),
          ),
        );
      },
    );
  }

  IconData _getServiceIcon(String serviceName) {
    switch (serviceName.toLowerCase()) {
      case 'filesystem':
        return Icons.folder;
      case 'web':
        return Icons.language;
      case 'data':
        return Icons.data_object;
      case 'map':
      case 'amap':
        return Icons.map;
      case 'weather':
        return Icons.wb_sunny;
      default:
        return Icons.extension;
    }
  }

  IconData _getToolIcon(String toolName) {
    if (toolName.contains('read') || toolName.contains('get')) {
      return Icons.visibility;
    } else if (toolName.contains('write') || toolName.contains('create')) {
      return Icons.edit;
    } else if (toolName.contains('delete') || toolName.contains('remove')) {
      return Icons.delete;
    } else if (toolName.contains('list')) {
      return Icons.list;
    } else if (toolName.contains('search')) {
      return Icons.search;
    } else if (toolName.contains('route') || toolName.contains('planning')) {
      return Icons.directions;
    } else if (toolName.contains('place') || toolName.contains('location')) {
      return Icons.place;
    } else if (toolName.contains('map')) {
      return Icons.location_on;
    } else {
      return Icons.build;
    }
  }

  void _showCleanupDialog(BuildContext context) {
    // 先获取MCPService的引用
    final mcpService = context.read<MCPService>();
    // 保存外部context的引用
    final scaffoldContext = context;
    
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('清理工作空间'),
        content: const Text('这将清理24小时前创建的临时工作空间。确定要继续吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(dialogContext);
              await mcpService.cleanupOldCodespaces();
              if (mounted) {
                ScaffoldMessenger.of(scaffoldContext).showSnackBar(
                  const SnackBar(content: Text('工作空间清理完成')),
                );
              }
            },
            child: const Text('清理'),
          ),
        ],
      ),
    );
  }
}
