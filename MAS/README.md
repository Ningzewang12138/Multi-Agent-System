# Baymin - 智能多Agent系统

Baymin 是一个基于服务器-客户端架构的智能AI服务系统，支持多设备同步、知识库管理和RAG（检索增强生成）功能。

## 🌟 主要特性

- **多Agent架构**：支持多个AI模型协同工作
- **知识库管理**：完整的文档上传、管理和检索功能
- **RAG支持**：基于知识库的智能问答
- **MCP工具集成**：支持文件操作、数据处理等多种工具调用
- **跨平台客户端**：使用Flutter开发，支持Windows、macOS、Linux、iOS和Android
- **设备隔离**：每个设备的草稿知识库相互隔离，保护隐私
- **智能同步**：支持知识库在多设备间同步共享
- **P2P聊天**：设备间直接通信功能

## 🚀 快速开始

### 使用快速启动脚本（推荐）

```bash
# 显示交互式菜单
python quickstart.py

# 直接启动服务器
python quickstart.py server

# 运行快速测试
python quickstart.py test
```

### 手动启动

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **启动服务器**
```bash
# Windows
start_server.bat

# Linux/Mac
./start_server.sh
```

服务器默认运行在 `http://localhost:8000`

### 客户端

1. **安装Flutter环境**
- 访问 [Flutter官网](https://flutter.dev) 下载并安装Flutter SDK

2. **编译客户端**
```bash
cd masgui

# 获取依赖
flutter pub get

# 编译对应平台
flutter build windows  # Windows
flutter build apk      # Android
flutter build ios      # iOS
```

## 📁 项目结构

```
MAS/
├── server/              # 服务器端代码
│   ├── api/            # API路由
│   ├── services/       # 业务逻辑
│   ├── models/         # 数据模型
│   └── mcp/            # MCP工具集成
├── masgui/             # Flutter客户端
│   ├── lib/            # Dart源代码
│   ├── android/        # Android平台配置
│   ├── ios/           # iOS平台配置
│   └── windows/       # Windows平台配置
├── tests/              # 测试脚本
│   └── integrated_test_suite.py  # 综合测试套件
├── scripts/            # 工具脚本
│   ├── fix_project.py  # 项目修复工具
│   └── project_cleanup.py # 清理维护工具
├── docs/               # 文档
│   └── mcp_tools_guide.md  # MCP工具使用指南
└── requirements.txt    # Python依赖

```

## 🧪 测试

运行综合测试套件：
```bash
python tests/integrated_test_suite.py --all
```

快速测试：
```bash
python tests/integrated_test_suite.py --quick
```

特定功能测试：
```bash
python tests/integrated_test_suite.py --rag      # RAG功能
python tests/integrated_test_suite.py --knowledge # 知识库功能
python tests/integrated_test_suite.py --api      # API端点
python test_mcp_functionality.py                 # MCP工具功能
```

性能测试：
```bash
python tests/integrated_test_suite.py --performance
```

## 🛠️ 维护工具

### 项目清理工具
```bash
# 查看将要清理的内容（模拟运行）
python scripts/project_cleanup.py --all --dry-run

# 执行清理和整理
python scripts/project_cleanup.py --all

# 只清理冗余文件
python scripts/project_cleanup.py --redundant

# 只整理项目结构
python scripts/project_cleanup.py --organize
```

### 项目修复工具
```bash
# 修复编码问题和创建缺失文件
python scripts/fix_project.py
```

## 📖 API文档

主要API端点：

### 知识库管理
- `GET /api/knowledge/` - 列出知识库
- `POST /api/knowledge/` - 创建知识库
- `DELETE /api/knowledge/{kb_id}` - 删除知识库

### 文档管理
- `POST /api/knowledge/{kb_id}/documents/upload` - 上传文档
- `GET /api/knowledge/{kb_id}/documents` - 列出文档

### RAG查询
- `POST /api/chat/rag/completions` - 执行RAG增强聊天

### MCP工具
- `GET /api/mcp/services` - 获取MCP服务列表
- `GET /api/mcp/tools` - 获取可用工具列表
- `POST /api/mcp/execute` - 执行MCP工具

### P2P功能
- `GET /api/p2p/peers` - 获取在线设备列表
- `POST /api/p2p/chat/send` - 发送P2P消息

详细API文档请参考 [docs/api/](docs/api/)

## 🔧 配置

### 服务器配置
编辑 `server/config/settings.py`：
- 数据库路径
- 嵌入模型选择
- 服务器地址和端口

### 客户端配置
在客户端设置界面中配置：
- 服务器地址
- 选择AI模型
- 启用/禁用RAG

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

Copyright 2024 Baymin Team

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

**注意**：这是一个正在积极开发中的项目，某些功能可能还不稳定。如遇到问题，请提交Issue。
