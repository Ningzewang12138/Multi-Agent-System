import 'dart:io';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';

class LocalDatabaseService {
  static Database? _database;
  static final LocalDatabaseService _instance = LocalDatabaseService._internal();
  
  factory LocalDatabaseService() => _instance;
  LocalDatabaseService._internal();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    // 初始化 sqflite_ffi for desktop
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }

    // 获取数据库路径
    final documentsDirectory = await getApplicationDocumentsDirectory();
    final path = join(documentsDirectory.path, 'masgui_local.db');

    // 打开数据库
    return await openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    // 创建本地知识库表
    await db.execute('''
      CREATE TABLE knowledge_bases (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_local INTEGER DEFAULT 1,
        is_synced INTEGER DEFAULT 0,
        server_id TEXT,
        sync_status TEXT DEFAULT 'not_synced',
        document_count INTEGER DEFAULT 0
      )
    ''');

    // 创建文档表
    await db.execute('''
      CREATE TABLE documents (
        id TEXT PRIMARY KEY,
        kb_id TEXT NOT NULL,
        title TEXT,
        content TEXT NOT NULL,
        file_path TEXT,
        file_type TEXT,
        file_size INTEGER,
        metadata TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        chunk_count INTEGER DEFAULT 0,
        FOREIGN KEY (kb_id) REFERENCES knowledge_bases (id) ON DELETE CASCADE
      )
    ''');

    // 创建文档块表（用于向量检索）
    await db.execute('''
      CREATE TABLE document_chunks (
        id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        kb_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding BLOB,
        metadata TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (doc_id) REFERENCES documents (id) ON DELETE CASCADE,
        FOREIGN KEY (kb_id) REFERENCES knowledge_bases (id) ON DELETE CASCADE
      )
    ''');

    // 创建同步记录表
    await db.execute('''
      CREATE TABLE sync_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kb_id TEXT NOT NULL,
        sync_type TEXT NOT NULL,
        sync_direction TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        documents_synced INTEGER DEFAULT 0,
        error_message TEXT,
        FOREIGN KEY (kb_id) REFERENCES knowledge_bases (id) ON DELETE CASCADE
      )
    ''');

    // 创建索引
    await db.execute('CREATE INDEX idx_documents_kb_id ON documents (kb_id)');
    await db.execute('CREATE INDEX idx_chunks_kb_id ON document_chunks (kb_id)');
    await db.execute('CREATE INDEX idx_chunks_doc_id ON document_chunks (doc_id)');
    await db.execute('CREATE INDEX idx_sync_kb_id ON sync_records (kb_id)');
  }

  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    // 处理数据库升级
    if (oldVersion < 2) {
      // 未来的升级逻辑
    }
  }

  // 知识库操作
  Future<String> createKnowledgeBase({
    required String name,
    String? description,
  }) async {
    final db = await database;
    final id = DateTime.now().millisecondsSinceEpoch.toString();
    final now = DateTime.now().toIso8601String();

    await db.insert('knowledge_bases', {
      'id': id,
      'name': name,
      'description': description,
      'created_at': now,
      'updated_at': now,
      'is_local': 1,
      'is_synced': 0,
      'sync_status': 'not_synced',
      'document_count': 0,
    });

    return id;
  }

  Future<List<Map<String, dynamic>>> getLocalKnowledgeBases() async {
    final db = await database;
    return await db.query(
      'knowledge_bases',
      where: 'is_local = ?',
      whereArgs: [1],
      orderBy: 'updated_at DESC',
    );
  }

  Future<Map<String, dynamic>?> getKnowledgeBase(String id) async {
    final db = await database;
    final results = await db.query(
      'knowledge_bases',
      where: 'id = ?',
      whereArgs: [id],
      limit: 1,
    );
    return results.isNotEmpty ? results.first : null;
  }

  Future<void> updateKnowledgeBase(String id, Map<String, dynamic> updates) async {
    final db = await database;
    updates['updated_at'] = DateTime.now().toIso8601String();
    await db.update(
      'knowledge_bases',
      updates,
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> deleteKnowledgeBase(String id) async {
    final db = await database;
    await db.delete(
      'knowledge_bases',
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  // 文档操作
  Future<String> addDocument({
    required String kbId,
    required String content,
    String? title,
    String? filePath,
    String? fileType,
    int? fileSize,
    Map<String, dynamic>? metadata,
  }) async {
    final db = await database;
    final docId = DateTime.now().millisecondsSinceEpoch.toString();
    final now = DateTime.now().toIso8601String();

    await db.insert('documents', {
      'id': docId,
      'kb_id': kbId,
      'title': title,
      'content': content,
      'file_path': filePath,
      'file_type': fileType,
      'file_size': fileSize,
      'metadata': metadata != null ? jsonEncode(metadata) : null,
      'created_at': now,
      'updated_at': now,
      'chunk_count': 0,
    });

    // 更新知识库文档数
    await db.rawUpdate('''
      UPDATE knowledge_bases 
      SET document_count = document_count + 1,
          updated_at = ?
      WHERE id = ?
    ''', [now, kbId]);

    return docId;
  }

  Future<List<Map<String, dynamic>>> getDocuments(String kbId) async {
    final db = await database;
    return await db.query(
      'documents',
      where: 'kb_id = ?',
      whereArgs: [kbId],
      orderBy: 'created_at DESC',
    );
  }

  Future<void> deleteDocument(String docId) async {
    final db = await database;
    
    // 获取文档信息
    final doc = await db.query(
      'documents',
      where: 'id = ?',
      whereArgs: [docId],
      limit: 1,
    );
    
    if (doc.isNotEmpty) {
      final kbId = doc.first['kb_id'];
      
      // 删除文档
      await db.delete(
        'documents',
        where: 'id = ?',
        whereArgs: [docId],
      );
      
      // 更新知识库文档数
      await db.rawUpdate('''
        UPDATE knowledge_bases 
        SET document_count = document_count - 1,
            updated_at = ?
        WHERE id = ?
      ''', [DateTime.now().toIso8601String(), kbId]);
    }
  }

  // 文档块操作（用于向量检索）
  Future<void> addDocumentChunks(String docId, String kbId, List<Map<String, dynamic>> chunks) async {
    final db = await database;
    final batch = db.batch();
    final now = DateTime.now().toIso8601String();

    for (int i = 0; i < chunks.length; i++) {
      final chunk = chunks[i];
      final chunkId = '${docId}_chunk_$i';
      
      batch.insert('document_chunks', {
        'id': chunkId,
        'doc_id': docId,
        'kb_id': kbId,
        'chunk_index': i,
        'content': chunk['content'],
        'embedding': chunk['embedding'], // 这里需要是Uint8List
        'metadata': chunk['metadata'] != null ? jsonEncode(chunk['metadata']) : null,
        'created_at': now,
      });
    }

    await batch.commit();
    
    // 更新文档的chunk数量
    await db.update(
      'documents',
      {'chunk_count': chunks.length},
      where: 'id = ?',
      whereArgs: [docId],
    );
  }

  Future<List<Map<String, dynamic>>> searchChunks(String kbId, String query, {int limit = 10}) async {
    final db = await database;
    
    // 简单的文本搜索，实际应该使用向量相似度搜索
    return await db.query(
      'document_chunks',
      where: 'kb_id = ? AND content LIKE ?',
      whereArgs: [kbId, '%$query%'],
      limit: limit,
    );
  }

  // 同步操作
  Future<void> markKnowledgeBaseAsSynced(String kbId, String serverId) async {
    final db = await database;
    await db.update(
      'knowledge_bases',
      {
        'is_synced': 1,
        'server_id': serverId,
        'sync_status': 'synced',
        'updated_at': DateTime.now().toIso8601String(),
      },
      where: 'id = ?',
      whereArgs: [kbId],
    );
  }

  Future<void> recordSyncHistory({
    required String kbId,
    required String syncType,
    required String syncDirection,
    required String status,
    int documentsSync = 0,
    String? errorMessage,
  }) async {
    final db = await database;
    final now = DateTime.now().toIso8601String();

    await db.insert('sync_records', {
      'kb_id': kbId,
      'sync_type': syncType,
      'sync_direction': syncDirection,
      'status': status,
      'started_at': now,
      'completed_at': status == 'completed' ? now : null,
      'documents_synced': documentsSync,
      'error_message': errorMessage,
    });
  }

  Future<List<Map<String, dynamic>>> getSyncHistory(String kbId) async {
    final db = await database;
    return await db.query(
      'sync_records',
      where: 'kb_id = ?',
      whereArgs: [kbId],
      orderBy: 'started_at DESC',
      limit: 10,
    );
  }

  // 获取统计信息
  Future<Map<String, dynamic>> getStatistics() async {
    final db = await database;
    
    final kbCount = Sqflite.firstIntValue(
      await db.rawQuery('SELECT COUNT(*) FROM knowledge_bases WHERE is_local = 1')
    ) ?? 0;
    
    final docCount = Sqflite.firstIntValue(
      await db.rawQuery('SELECT COUNT(*) FROM documents')
    ) ?? 0;
    
    final syncedCount = Sqflite.firstIntValue(
      await db.rawQuery('SELECT COUNT(*) FROM knowledge_bases WHERE is_synced = 1')
    ) ?? 0;
    
    return {
      'local_kb_count': kbCount,
      'total_documents': docCount,
      'synced_kb_count': syncedCount,
    };
  }

  // 关闭数据库
  Future<void> close() async {
    final db = await database;
    await db.close();
    _database = null;
  }
}

// JSON编码/解码辅助函数
String jsonEncode(Map<String, dynamic> data) {
  return data.toString(); // 简单实现，实际应该使用 dart:convert
}

Map<String, dynamic> jsonDecode(String data) {
  // 简单实现，实际应该使用 dart:convert
  return {};
}
