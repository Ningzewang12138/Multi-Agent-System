import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import '../../services/mcp/mcp_service.dart';
import 'mcp_Codespace_screen.dart';

class MCPToolExecutionScreen extends StatefulWidget {
  final MCPToolInfo tool;

  const MCPToolExecutionScreen({Key? key, required this.tool})
      : super(key: key);

  @override
  State<MCPToolExecutionScreen> createState() => _MCPToolExecutionScreenState();
}

class _MCPToolExecutionScreenState extends State<MCPToolExecutionScreen> {
  final Map<String, TextEditingController> _controllers = {};
  final Map<String, dynamic> _parameterValues = {};
  bool _isExecuting = false;
  ToolCallResult? _result;

  @override
  void initState() {
    super.initState();
    // 初始化参数控制器
    for (final param in widget.tool.parameters) {
      final name = param['name'] as String;
      _controllers[name] = TextEditingController();
      
      // 设置默认值
      if (param['default'] != null) {
        _controllers[name]!.text = param['default'].toString();
        _parameterValues[name] = param['default'];
      }
    }
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('执行 ${widget.tool.name}'),
        actions: [
          if (_result?.sessionId != null)
            IconButton(
              icon: const Icon(Icons.folder_open),
              onPressed: () => _openCodespace(context),
              tooltip: '查看工作空间',
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 参数输入区域
            if (widget.tool.parameters.isNotEmpty) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '参数设置',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 16),
                      ...widget.tool.parameters
                          .map((param) => _buildParameterInput(param)),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // 执行按钮
            SizedBox(
              width: double.infinity,
              height: 56,
              child: ElevatedButton.icon(
                onPressed: _isExecuting ? null : _executeTool,
                icon: _isExecuting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : const Icon(Icons.play_arrow),
                label: Text(_isExecuting ? '执行中...' : '执行工具'),
                style: ElevatedButton.styleFrom(
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),

            // 执行结果
            if (_result != null) ...[
              const SizedBox(height: 24),
              _buildResultCard(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildParameterInput(Map<String, dynamic> param) {
    final name = param['name'] as String;
    final type = param['type'] ?? 'string';
    final isRequired = param['required'] ?? false;
    final description = param['description'] ?? '';
    final enumValues = param['enum'] as List?;

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                name,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
              if (isRequired)
                const Text(
                  ' *',
                  style: TextStyle(color: Colors.red),
                ),
            ],
          ),
          if (description.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              description,
              style: TextStyle(
                color: Theme.of(context).brightness == Brightness.dark
                    ? Colors.grey.shade400
                    : Colors.grey.shade600,
                fontSize: 14,
              ),
            ),
          ],
          const SizedBox(height: 8),
          if (enumValues != null && enumValues.isNotEmpty)
            DropdownButtonFormField<String>(
              value: _controllers[name]!.text.isEmpty
                  ? null
                  : _controllers[name]!.text,
              decoration: InputDecoration(
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                filled: true,
                fillColor: Theme.of(context).brightness == Brightness.dark
                    ? Colors.grey.shade800
                    : Colors.grey.shade100,
              ),
              items: enumValues
                  .map((value) => DropdownMenuItem(
                        value: value.toString(),
                        child: Text(value.toString()),
                      ))
                  .toList(),
              onChanged: (value) {
                setState(() {
                  _controllers[name]!.text = value ?? '';
                  _parameterValues[name] = value;
                });
              },
            )
          else if (type == 'boolean')
            SwitchListTile(
              title: const Text('启用'),
              value: _parameterValues[name] ?? false,
              onChanged: (value) {
                setState(() {
                  _parameterValues[name] = value;
                  _controllers[name]!.text = value.toString();
                });
              },
              contentPadding: EdgeInsets.zero,
            )
          else if (type == 'integer' || type == 'number')
            TextFormField(
              controller: _controllers[name],
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                filled: true,
                fillColor: Theme.of(context).brightness == Brightness.dark
                    ? Colors.grey.shade800
                    : Colors.grey.shade100,
                hintText: '请输入${type == 'integer' ? '整数' : '数字'}',
              ),
              onChanged: (value) {
                if (value.isNotEmpty) {
                  if (type == 'integer') {
                    _parameterValues[name] = int.tryParse(value);
                  } else {
                    _parameterValues[name] = double.tryParse(value);
                  }
                } else {
                  _parameterValues.remove(name);
                }
              },
            )
          else if (type == 'object' || type == 'array')
            TextFormField(
              controller: _controllers[name],
              maxLines: 3,
              decoration: InputDecoration(
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                filled: true,
                fillColor: Theme.of(context).brightness == Brightness.dark
                    ? Colors.grey.shade800
                    : Colors.grey.shade100,
                hintText: '请输入JSON格式数据',
              ),
              onChanged: (value) {
                try {
                  if (value.isNotEmpty) {
                    _parameterValues[name] = json.decode(value);
                  } else {
                    _parameterValues.remove(name);
                  }
                } catch (e) {
                  // JSON解析错误，暂不处理
                }
              },
            )
          else
            TextFormField(
              controller: _controllers[name],
              decoration: InputDecoration(
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                filled: true,
                fillColor: Theme.of(context).brightness == Brightness.dark
                    ? Colors.grey.shade800
                    : Colors.grey.shade100,
                hintText: '请输入${name}',
              ),
              onChanged: (value) {
                if (value.isNotEmpty) {
                  _parameterValues[name] = value;
                } else {
                  _parameterValues.remove(name);
                }
              },
            ),
        ],
      ),
    );
  }

  Widget _buildResultCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _result!.success ? Icons.check_circle : Icons.error,
                  color: _result!.success ? Colors.green : Colors.red,
                ),
                const SizedBox(width: 8),
                Text(
                  '执行结果',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (_result!.error != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _result!.error!,
                        style: const TextStyle(color: Colors.red),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).brightness == Brightness.dark
                    ? Colors.grey.shade800
                    : Colors.grey.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(
                _formatResult(_result!.result),
                style: TextStyle(
                  fontFamily: 'monospace',
                  color: Theme.of(context).brightness == Brightness.dark
                      ? Colors.white
                      : Colors.black87,
                ),
              ),
            ),
            if (_result!.CodespaceInfo != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.folder, color: Colors.blue),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '工作空间已创建',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.blue,
                            ),
                          ),
                          Text(
                            '会话ID: ${_result!.sessionId}',
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.blue.shade700,
                            ),
                          ),
                          if (_result!.CodespaceInfo!['files'] != null)
                            Text(
                              '文件数: ${(_result!.CodespaceInfo!['files'] as List).length}',
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.blue.shade700,
                              ),
                            ),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: () => _openCodespace(context),
                      child: const Text('查看'),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _formatResult(dynamic result) {
    if (result == null) return 'null';
    if (result is String) return result;
    try {
      return const JsonEncoder.withIndent('  ').convert(result);
    } catch (e) {
      return result.toString();
    }
  }

  Future<void> _executeTool() async {
    // 验证必填参数
    for (final param in widget.tool.parameters) {
      final name = param['name'] as String;
      final isRequired = param['required'] ?? false;
      
      if (isRequired && !_parameterValues.containsKey(name)) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('请填写必填参数: $name')),
        );
        return;
      }
    }

    setState(() {
      _isExecuting = true;
      _result = null;
    });

    try {
      final mcpService = context.read<MCPService>();
      final result = await mcpService.executeTool(
        toolName: widget.tool.name,
        parameters: _parameterValues,
      );

      setState(() {
        _result = result;
      });

      if (result == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(mcpService.error ?? '执行失败'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('执行出错: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() {
        _isExecuting = false;
      });
    }
  }

  void _openCodespace(BuildContext context) {
    if (_result?.sessionId != null) {
      // 先获取MCPService的引用
      final mcpService = context.read<MCPService>();
      
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => ChangeNotifierProvider<MCPService>.value(
            value: mcpService,
            child: MCPCodespaceScreen(
              sessionId: _result!.sessionId,
            ),
          ),
        ),
      );
    }
  }
}
