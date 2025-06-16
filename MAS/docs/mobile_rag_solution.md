# 移动端本地RAG解决方案

## 1. 向量生成方案

### 轻量级方案（推荐用于移动设备）
- **简单哈希嵌入**：使用哈希函数生成固定维度向量，占用内存小
- **TF-IDF嵌入**：基于词频的传统方法，不需要神经网络
- **预计算嵌入**：在服务器端预先计算，客户端只存储结果

### 中等方案
- **量化模型**：使用INT8量化的小型嵌入模型（如：MiniLM）
- **ONNX Runtime**：使用优化的推理引擎运行轻量模型

### 高级方案
- **远程嵌入API**：调用服务器或云端API生成嵌入
- **混合模式**：WiFi环境使用远程，离线使用本地

## 2. 模型连接方案

### A. 本地设备作为服务器（推荐）
在同一局域网内的PC/服务器上运行Ollama：
```bash
# PC端运行
ollama serve --host 0.0.0.0
ollama run llama3:latest
```

手机连接到同一WiFi，访问PC的IP地址：
- 例如：http://192.168.1.100:11434

### B. 边缘计算设备
使用树莓派或其他边缘设备：
- 安装Ollama或llama.cpp
- 作为家庭/办公室的本地AI服务器

### C. 手机热点模式
手机开启热点，PC连接到手机热点：
- 手机可以访问PC上的Ollama服务
- 适合移动办公场景

### D. 云端轻量级API
使用免费或低成本的API服务：
- Hugging Face Inference API（免费额度）
- Cohere API（每月免费额度）
- 自建的云端轻量服务

### E. 本地轻量级模型（实验性）
- **llama.cpp移植**：有人尝试将llama.cpp移植到Android
- **ONNX Runtime Mobile**：运行量化的小模型
- **TensorFlow Lite**：运行优化的移动端模型

## 3. 实际部署建议

### 家庭/办公室场景
1. 在PC/NAS上运行Ollama服务器
2. 手机通过局域网连接
3. 可以配置动态DNS实现外网访问

### 移动场景
1. 使用手机热点 + 笔记本的组合
2. 或使用云端API作为后备

### 纯离线场景
1. 使用基于模板的响应系统
2. 预先下载常见问答对
3. 使用简单的关键词匹配

## 4. Flutter实现示例

```dart
// 配置文件
class MobileRAGConfig {
  // 本地网络Ollama地址（可配置）
  static List<String> localOllamaServers = [
    'http://192.168.1.100:11434',  // 家庭PC
    'http://192.168.1.200:11434',  // 办公室服务器
    'http://10.0.0.2:11434',       // 手机热点时的地址
  ];
  
  // 云端API（可选）
  static String? cloudApiUrl;
  static String? cloudApiKey;
  
  // 嵌入策略
  static EmbeddingMode embeddingMode = EmbeddingMode.auto;
  
  // RAG策略
  static RAGMode ragMode = RAGMode.hybrid;
}

// 使用示例
final ragService = MobileRAGService();
await ragService.initialize();

// 自动选择最佳可用的服务
final response = await ragService.mobileRAGChat(
  query: "What is machine learning?",
  knowledgeBaseId: "local_kb_123",
);
```

## 5. 性能优化建议

### 嵌入生成
- 批量处理文档，避免频繁计算
- 使用缓存存储已计算的嵌入
- 在WiFi环境下后台更新嵌入

### 搜索优化
- 使用倒排索引加速搜索
- 限制搜索范围（最近的N个文档）
- 实现分页加载

### 存储优化
- 压缩嵌入向量（量化到INT8）
- 定期清理旧数据
- 使用增量同步

## 6. 用户体验优化

### 渐进式响应
1. 立即显示本地模板响应
2. 后台尝试连接远程模型
3. 获得更好的响应后更新显示

### 网络状态提示
- 显示当前使用的模型（本地/远程）
- 提示用户可用的选项
- 允许手动切换模式

### 离线能力说明
- 明确告知用户离线功能的限制
- 提供改善体验的建议（如连接到家庭服务器）
