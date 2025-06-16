import 'dart:io';
import 'package:path/path.dart';

class LocalDocumentProcessor {
  static const int defaultChunkSize = 500;
  static const int chunkOverlap = 50;
  
  // 支持的文件类型
  static const supportedExtensions = [
    '.txt', '.md', '.json', '.csv', '.html', '.xml',
    '.pdf', '.docx', '.doc'
  ];

  // 处理文件
  Future<Map<String, dynamic>> processFile(String filePath) async {
    final file = File(filePath);
    final extension = basename(filePath).split('.').last.toLowerCase();
    
    String content = '';
    Map<String, dynamic> metadata = {
      'source': filePath,
      'filename': basename(filePath),
      'extension': extension,
      'size': await file.length(),
      'modified': (await file.lastModified()).toIso8601String(),
    };

    switch (extension) {
      case 'txt':
      case 'md':
      case 'json':
      case 'csv':
      case 'html':
      case 'xml':
        content = await file.readAsString();
        break;
      
      case 'pdf':
        // PDF处理需要特殊处理
        content = await _processPdf(filePath);
        break;
      
      case 'docx':
      case 'doc':
        // Word文档处理
        content = await _processWord(filePath);
        break;
      
      default:
        throw Exception('Unsupported file type: $extension');
    }

    return {
      'content': content,
      'metadata': metadata,
    };
  }

  // 分割文本
  List<Map<String, dynamic>> splitText(
    String text, {
    Map<String, dynamic>? metadata,
    int? chunkSize,
    int? overlap,
  }) {
    final size = chunkSize ?? defaultChunkSize;
    final overlapSize = overlap ?? chunkOverlap;
    
    if (text.isEmpty) {
      return [];
    }

    final chunks = <Map<String, dynamic>>[];
    final sentences = _splitIntoSentences(text);
    
    String currentChunk = '';
    int chunkIndex = 0;
    
    for (final sentence in sentences) {
      if (currentChunk.length + sentence.length > size && currentChunk.isNotEmpty) {
        // 保存当前chunk
        chunks.add({
          'text': currentChunk.trim(),
          'metadata': {
            ...?metadata,
            'chunk_index': chunkIndex,
            'start_index': text.indexOf(currentChunk),
          },
        });
        
        // 开始新的chunk，包含重叠部分
        final words = currentChunk.split(' ');
        final overlapWords = words.length > 10 
            ? words.sublist(words.length - 10).join(' ')
            : currentChunk;
        
        currentChunk = overlapWords + ' ' + sentence;
        chunkIndex++;
      } else {
        currentChunk += ' ' + sentence;
      }
    }
    
    // 添加最后一个chunk
    if (currentChunk.isNotEmpty) {
      chunks.add({
        'text': currentChunk.trim(),
        'metadata': {
          ...?metadata,
          'chunk_index': chunkIndex,
          'start_index': text.indexOf(currentChunk),
        },
      });
    }
    
    return chunks;
  }

  // 分割成句子
  List<String> _splitIntoSentences(String text) {
    // 简单的句子分割，实际应该使用更复杂的算法
    final sentences = <String>[];
    final pattern = RegExp(r'[.!?]+\s+');
    
    int start = 0;
    for (final match in pattern.allMatches(text)) {
      final sentence = text.substring(start, match.end).trim();
      if (sentence.isNotEmpty) {
        sentences.add(sentence);
      }
      start = match.end;
    }
    
    // 添加最后一部分
    if (start < text.length) {
      final lastSentence = text.substring(start).trim();
      if (lastSentence.isNotEmpty) {
        sentences.add(lastSentence);
      }
    }
    
    return sentences;
  }

  // 处理PDF（需要实现）
  Future<String> _processPdf(String filePath) async {
    // 这里需要集成PDF解析库
    // 暂时返回占位符
    return 'PDF content extraction not implemented yet';
  }

  // 处理Word文档（需要实现）
  Future<String> _processWord(String filePath) async {
    // 这里需要集成Word文档解析库
    // 暂时返回占位符
    return 'Word document extraction not implemented yet';
  }

  // 清理文本
  String cleanText(String text) {
    // 移除多余的空白字符
    text = text.replaceAll(RegExp(r'\s+'), ' ');
    
    // 使用更简单的方式处理特殊字符
    // 保留：字母、数字、中文、空格和基本标点
    final allowedChars = RegExp('[a-zA-Z0-9\u4e00-\u9fa5\\s.!?,;:\\-\'"]');
    final chars = text.split('');
    final cleanedChars = chars.where((char) => allowedChars.hasMatch(char)).toList();
    text = cleanedChars.join('');
    
    // 修整空白
    text = text.trim();
    
    return text;
  }

  // 提取关键词（简单实现）
  List<String> extractKeywords(String text, {int maxKeywords = 10}) {
    final words = text.toLowerCase().split(RegExp(r'\s+'));
    final wordCount = <String, int>{};
    
    // 停用词列表（应该更完整）
    final stopWords = {
      'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
      'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
      'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
      'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
    };
    
    // 统计词频
    for (final word in words) {
      if (word.length > 2 && !stopWords.contains(word)) {
        wordCount[word] = (wordCount[word] ?? 0) + 1;
      }
    }
    
    // 按频率排序
    final sortedWords = wordCount.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    
    // 返回前N个关键词
    return sortedWords
        .take(maxKeywords)
        .map((e) => e.key)
        .toList();
  }
}
