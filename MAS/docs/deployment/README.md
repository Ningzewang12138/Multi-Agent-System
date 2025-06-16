# 部署指南

## 服务器部署

### 1. 系统要求

- Python 3.8 或更高版本
- 4GB RAM（推荐8GB）
- 10GB 可用磁盘空间
- Ubuntu 20.04+ / Windows 10+ / macOS 10.15+

### 2. 安装步骤

#### 2.1 克隆项目
```bash
git clone https://github.com/your-repo/mas.git
cd mas
```

#### 2.2 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

#### 2.3 安装依赖
```bash
pip install -r requirements.txt
```

#### 2.4 安装Ollama
```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# 从 https://ollama.ai 下载安装程序
```

#### 2.5 下载模型
```bash
ollama pull llama3:latest
ollama pull qwen3:4b
```

### 3. 配置

创建配置文件 `config/settings.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "reload": false
  },
  "database": {
    "type": "chromadb",
    "path": "./chroma_db"
  },
  "embedding": {
    "default_service": "sentence-transformers",
    "model": "all-MiniLM-L6-v2"
  },
  "ollama": {
    "base_url": "http://localhost:11434",
    "default_model": "llama3:latest"
  }
}
```

### 4. 启动服务

#### 使用快速启动脚本
```bash
python quickstart.py server
```

#### 使用systemd（Linux）
创建服务文件 `/etc/systemd/system/mas.service`:

```ini
[Unit]
Description=MAS AI Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/mas
Environment="PATH=/path/to/mas/venv/bin"
ExecStart=/path/to/mas/venv/bin/python /path/to/mas/server/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable mas
sudo systemctl start mas
```

### 5. Nginx反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## 客户端部署

### Flutter Web部署

```bash
cd masgui
flutter build web --release

# 将build/web目录部署到Web服务器
```

### Android APK

```bash
cd masgui
flutter build apk --release

# APK文件位于 build/app/outputs/flutter-apk/
```

### Windows安装包

```bash
cd masgui
flutter build windows --release

# 使用Inno Setup创建安装包
```

## Docker部署（计划中）

Dockerfile示例：

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "server/main.py"]
```

## 性能优化

1. **使用生产级ASGI服务器**
   ```bash
   gunicorn server.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

2. **启用响应缓存**
   - 配置Redis缓存
   - 缓存知识库搜索结果

3. **数据库优化**
   - 定期清理旧数据
   - 优化向量索引

## 监控和日志

1. **日志配置**
   - 日志文件位置：`logs/`
   - 日志级别：生产环境使用INFO

2. **监控工具**
   - Prometheus + Grafana
   - 健康检查端点：`/health`

## 备份策略

1. **数据备份**
   ```bash
   # 备份ChromaDB
   tar -czf backup_$(date +%Y%m%d).tar.gz chroma_db/
   ```

2. **自动备份脚本**
   ```bash
   0 2 * * * /path/to/backup_script.sh
   ```

## 安全建议

1. **启用HTTPS**
2. **添加API认证**
3. **限制CORS来源**
4. **定期更新依赖**
5. **使用防火墙规则**
