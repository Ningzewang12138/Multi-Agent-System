# 开发指南

## 项目结构

```
MAS/
├── server/              # 服务器端代码
│   ├── api/            # API路由
│   ├── services/       # 业务逻辑服务
│   ├── models/         # 数据模型
│   └── main.py         # 服务器入口
├── masgui/             # Flutter客户端
│   ├── lib/            # Dart源代码
│   └── pubspec.yaml    # Flutter依赖
├── tests/              # 测试脚本
│   └── integrated_test_suite.py  # 综合测试套件
├── scripts/            # 工具脚本
│   ├── fix_project.py  # 项目修复工具
│   └── project_cleanup.py  # 清理工具
├── docs/               # 文档
│   ├── api/           # API文档
│   ├── guides/        # 使用指南
│   └── deployment/    # 部署文档
└── config/            # 配置文件
```

## 开发流程

### 1. 环境设置

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行服务器

```bash
# 使用快速启动脚本
python quickstart.py server

# 或手动启动
cd server
python main.py
```

### 3. 运行测试

```bash
# 运行所有测试
python tests/integrated_test_suite.py --all

# 快速测试
python tests/integrated_test_suite.py --quick

# 特定功能测试
python tests/integrated_test_suite.py --rag
```

### 4. Flutter开发

```bash
cd masgui
flutter pub get
flutter run
```

## 代码规范

- Python代码遵循PEP 8
- 使用类型注解
- 编写文档字符串
- 保持代码简洁清晰

## Git工作流程

1. 从main分支创建功能分支
2. 进行开发和测试
3. 提交前运行测试
4. 创建Pull Request

## 调试技巧

### 服务器调试
- 查看日志文件：`logs/server.log`
- 使用断点调试
- 检查API响应

### Flutter调试
- 使用Flutter DevTools
- 查看控制台输出
- 使用断点调试

## 常见问题

### Q: 服务器启动失败
A: 检查端口是否被占用，确保Ollama服务正在运行

### Q: 知识库搜索不工作
A: 检查嵌入服务是否正常，查看服务器日志

### Q: Flutter编译失败
A: 运行`flutter clean`后重新编译
