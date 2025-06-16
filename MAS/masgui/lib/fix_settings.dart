import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // 设置前缀
  SharedPreferences.setPrefix("Baymin.");
  SharedPreferences prefs = await SharedPreferences.getInstance();
  
  print('=== Current Settings ===');
  print('serverMode: ${prefs.getString('serverMode')}');
  print('multiAgentServer: ${prefs.getString('multiAgentServer')}');
  print('host: ${prefs.getString('host')}');
  print('model: ${prefs.getString('model')}');
  
  // 强制设置为 multiagent 模式
  await prefs.setString('serverMode', 'multiagent');
  await prefs.setString('multiAgentServer', 'http://localhost:8000');
  
  // 如果有旧的 host 设置，移除它
  if (prefs.containsKey('host')) {
    await prefs.remove('host');
    print('Removed old host setting');
  }
  
  print('\n=== Updated Settings ===');
  print('serverMode: ${prefs.getString('serverMode')}');
  print('multiAgentServer: ${prefs.getString('multiAgentServer')}');
  
  print('\nSettings fixed! Please restart the app.');
  
  runApp(MaterialApp(
    home: Scaffold(
      appBar: AppBar(title: Text('Fix Settings')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Settings have been fixed!'),
            SizedBox(height: 20),
            Text('Server Mode: multiagent'),
            Text('Server URL: http://localhost:8000'),
            SizedBox(height: 40),
            Text('Please close this and restart the main app.'),
          ],
        ),
      ),
    ),
  ));
}
