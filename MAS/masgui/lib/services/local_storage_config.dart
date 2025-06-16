import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;

class LocalStorageConfig {
  static late String _basePath;
  
  // 初始化本地存储路径
  static Future<void> initialize() async {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      // 桌面平台：使用应用文档目录
      final documentsDir = await getApplicationDocumentsDirectory();
      _basePath = path.join(documentsDir.path, 'MASClient');
    } else {
      // 移动平台：使用应用支持目录
      final supportDir = await getApplicationSupportDirectory();
      _basePath = path.join(supportDir.path, 'MASClient');
    }
    
    // 创建必要的目录
    await Directory(_basePath).create(recursive: true);
    await Directory(knowledgeBasePath).create(recursive: true);
    await Directory(documentsPath).create(recursive: true);
    
    print('Local storage initialized at: $_basePath');
  }
  
  // 知识库存储路径
  static String get knowledgeBasePath => path.join(_basePath, 'knowledge_bases');
  
  // 文档存储路径
  static String get documentsPath => path.join(_basePath, 'documents');
  
  // 临时文件路径
  static String get tempPath => path.join(_basePath, 'temp');
  
  // 配置文件路径
  static String get configPath => path.join(_basePath, 'config');
}
