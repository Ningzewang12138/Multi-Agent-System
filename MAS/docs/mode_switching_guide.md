# Flutter客户端模式切换功能

## 概述

Flutter客户端现在支持两种主要模式：
- **Local Mode（本地模式）**：使用本地部署的AI模型
- **Internet Mode（互联网模式）**：连接外部AI服务

## Local Mode（本地模式）

本地模式包含两个子模式：

### 1. Direct Ollama
- 直接连接到Ollama服务器
- 支持所有Ollama模型
- 可以添加新模型
- 支持多模态（图像）功能

### 2. Multi-Agent Server
- 连接到MAS服务器
- 支持RAG（知识库增强）
- 支持MCP服务
- 设备同步功能

## Internet Mode（互联网模式）

支持以下外部AI服务：

### 支持的模型
1. **DeepSeek V3** - DeepSeek的最新模型
2. **DeepSeek R1** - DeepSeek的推理模型
3. **Claude 4 Sonnet** - Anthropic的Claude模型
4. **ChatGPT 4o** - OpenAI的GPT-4模型

### 特点
- 只需要API密钥
- 支持基本对话功能
- 自动保存API密钥（加密存储）
- 连接测试功能

## 使用方法

### 切换模式

1. 打开侧边栏菜单
2. 点击"Mode Selection"（模式选择）
3. 选择所需的模式：
   - Local Mode → 选择Ollama或Multi-Agent
   - Internet Mode → 选择具体的AI服务

### 配置Internet Mode

1. 选择Internet Mode
2. 选择想要使用的AI服务（如DeepSeek V3）
3. 输入对应的API密钥
4. 点击"Save and Apply"保存设置
5. 系统会自动测试连接

### 获取API密钥

- **DeepSeek**: https://platform.deepseek.com/
- **Claude**: https://console.anthropic.com/
- **ChatGPT**: https://platform.openai.com/

## 技术实现

### 新增文件
- `lib/config/app_mode.dart` - 模式管理
- `lib/services/internet/internet_chat_service.dart` - Internet模式服务
- `lib/screens/mode_selection_screen.dart` - 模式选择界面

### 修改的文件
- `lib/main.dart` - 集成模式切换功能
- `lib/worker/sender.dart` - 支持Internet模式发送消息
- `lib/worker/setter.dart` - 支持Internet模式的模型选择

## 注意事项

1. **API密钥安全**：API密钥保存在本地，请勿分享
2. **网络要求**：Internet模式需要稳定的网络连接
3. **功能限制**：Internet模式仅支持对话，不支持RAG、MCP等高级功能
4. **成本考虑**：使用外部API服务可能产生费用

## 后续计划

- [ ] 支持流式响应（Stream）
- [ ] 支持更多外部API服务
- [ ] 支持自定义API端点
- [ ] 支持对话历史导出/导入
