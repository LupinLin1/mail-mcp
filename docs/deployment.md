# Mail MCP Server v2.0 部署指南

本文档提供 Mail MCP Server v2.0 的完整部署指南，包括开发环境、生产环境和容器化部署方案。

## 📋 系统要求

### 最低要求
- **Python**: 3.8+ (推荐 3.12+)
- **内存**: 512MB RAM
- **磁盘**: 100MB 可用空间
- **网络**: 支持 HTTPS/IMAPS/SMTPS 出站连接

### 推荐配置
- **Python**: 3.12+
- **内存**: 2GB RAM (支持缓存和连接池)
- **磁盘**: 1GB 可用空间
- **CPU**: 2 核心 (支持并发处理)
- **网络**: 稳定的互联网连接

### 支持的平台
- ✅ Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- ✅ macOS (10.15+)
- ✅ Windows 10/11
- ✅ Docker (任何支持 Docker 的平台)

## 🚀 快速部署 (uvx方式)

### Claude Code 用户 (推荐)
这是最简单的部署方式，无需任何预安装：

1. **创建配置文件** `.mcp.json`:
```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "uvx",
      "args": ["mail-mcp"],
      "env": {
        "IMAP_HOST": "imap.qq.com",
        "IMAP_PORT": "993",
        "IMAP_USERNAME": "your-email@qq.com",
        "IMAP_PASSWORD": "your-app-password",
        "IMAP_USE_SSL": "true",
        "SMTP_HOST": "smtp.qq.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "your-email@qq.com",
        "SMTP_PASSWORD": "your-app-password",
        "SMTP_USE_SSL": "false",
        "TRUSTED_SENDERS": "admin@company.com,boss@company.com"
      }
    }
  }
}
```

2. **启动 Claude Code**:
```bash
claude
```

完成！系统会自动下载和运行最新版本。

## 🏗️ 本地开发环境部署

### 1. 环境准备
```bash
# 确保Python版本
python --version  # 应该是 3.8+

# 安装uvx (如果没有)
pip install uv
```

### 2. 项目安装
```bash
# 方式1: 直接从PyPI安装
pip install mail-mcp

# 方式2: 从源码安装
git clone https://github.com/your-repo/mail-mcp.git
cd mail-mcp
pip install -e .
```

### 3. 配置环境
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

填入以下必需配置：
```env
IMAP_HOST=your-imap-server.com
IMAP_USERNAME=your-email@domain.com
IMAP_PASSWORD=your-app-password
SMTP_HOST=your-smtp-server.com
SMTP_USERNAME=your-email@domain.com
SMTP_PASSWORD=your-app-password
TRUSTED_SENDERS=admin@company.com,boss@company.com
```

### 4. 运行测试
```bash
# 运行单元测试
pytest tests/test_config.py tests/test_error_handling.py tests/test_performance_integration.py -v

# 测试连接
python -c "
from mail_mcp.config import Config
config = Config()
print('配置有效:', config.is_valid)
print('错误信息:', config.errors)
"
```

### 5. 启动服务
```bash
# MCP stdio模式 (Claude Code使用)
mail-mcp

# HTTP服务器模式 (用于调试)
python -m mail_mcp.main
```

## 🐳 Docker 部署

### 1. 使用预构建镜像
```bash
# 拉取镜像
docker pull mail-mcp:latest

# 运行容器
docker run -d \
  --name mail-mcp \
  -e IMAP_HOST=imap.qq.com \
  -e IMAP_USERNAME=your-email@qq.com \
  -e IMAP_PASSWORD=your-app-password \
  -e SMTP_HOST=smtp.qq.com \
  -e SMTP_USERNAME=your-email@qq.com \
  -e SMTP_PASSWORD=your-app-password \
  -e TRUSTED_SENDERS="admin@company.com,boss@company.com" \
  -p 8000:8000 \
  mail-mcp:latest
```

### 2. 自定义构建
创建 `Dockerfile`:
```dockerfile
FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml ./
COPY mail_mcp/ ./mail_mcp/

# 安装Python依赖
RUN pip install --no-cache-dir -e .

# 创建非root用户
RUN useradd -m -s /bin/bash mailmcp
USER mailmcp

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "mail_mcp.main"]
```

构建和运行：
```bash
# 构建镜像
docker build -t mail-mcp:local .

# 运行容器
docker run -d \
  --name mail-mcp-local \
  --env-file .env \
  -p 8000:8000 \
  mail-mcp:local
```

### 3. Docker Compose 部署
创建 `docker-compose.yml`:
```yaml
version: '3.8'

services:
  mail-mcp:
    image: mail-mcp:latest
    container_name: mail-mcp
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # 可选: 添加监控服务
  prometheus:
    image: prom/prometheus:latest
    container_name: mail-mcp-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
```

启动服务：
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f mail-mcp

# 停止服务
docker-compose down
```

## 🖥️ 生产环境部署

### 1. systemd 服务配置

创建服务文件 `/etc/systemd/system/mail-mcp.service`:
```ini
[Unit]
Description=Mail MCP Server v2.0
After=network.target
Wants=network.target

[Service]
Type=simple
User=mailmcp
Group=mailmcp
WorkingDirectory=/opt/mail-mcp
Environment=PYTHONPATH=/opt/mail-mcp
EnvironmentFile=/opt/mail-mcp/.env
ExecStart=/opt/mail-mcp/venv/bin/python -m mail_mcp.main
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 安全配置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/mail-mcp/logs

[Install]
WantedBy=multi-user.target
```

### 2. 用户和目录设置
```bash
# 创建专用用户
sudo useradd -m -s /bin/bash -r mailmcp

# 创建目录结构
sudo mkdir -p /opt/mail-mcp/{logs,data}
sudo chown -R mailmcp:mailmcp /opt/mail-mcp

# 切换到专用用户
sudo -u mailmcp -i

# 安装虚拟环境
cd /opt/mail-mcp
python -m venv venv
source venv/bin/activate
pip install mail-mcp
```

### 3. 生产配置
创建生产配置文件 `/opt/mail-mcp/.env`:
```env
# 基础配置
IMAP_HOST=imap.company.com
IMAP_USERNAME=service@company.com
IMAP_PASSWORD=secure-app-password
SMTP_HOST=smtp.company.com
SMTP_USERNAME=service@company.com
SMTP_PASSWORD=secure-app-password
TRUSTED_SENDERS=admin@company.com,hr@company.com,finance@company.com

# 生产优化配置
LOG_LEVEL=INFO
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# 性能优化
IMAP_TIMEOUT=60
SMTP_TIMEOUT=60
MAX_ATTACHMENT_SIZE=52428800  # 50MB
MAX_RETRIES=5

# 安全配置
IMAP_USE_SSL=true
SMTP_USE_SSL=true
```

### 4. 启动和管理服务
```bash
# 启动服务
sudo systemctl start mail-mcp

# 开机自启
sudo systemctl enable mail-mcp

# 查看状态
sudo systemctl status mail-mcp

# 查看日志
sudo journalctl -u mail-mcp -f

# 重启服务
sudo systemctl restart mail-mcp
```

## 🔧 性能调优

### 1. 连接池优化
在代码中调整连接池参数：
```python
# 在main.py的setup_services方法中
self.connection_pool = ConnectionPool(
    config=self.config,
    max_imap_connections=5,     # 增加IMAP连接数
    max_smtp_connections=3,     # 增加SMTP连接数
    connection_timeout=600,     # 10分钟超时
    health_check_interval=30    # 30秒健康检查
)
```

### 2. 缓存优化
```python
# 在main.py的setup_services方法中
self.email_cache = EmailCache(
    max_emails=2000,          # 增加邮件缓存
    max_message_content=1000, # 增加内容缓存
    email_ttl=3600,          # 1小时TTL
    content_ttl=7200         # 2小时TTL
)
```

### 3. 系统级优化
```bash
# 增加文件描述符限制
echo "mailmcp soft nofile 65536" >> /etc/security/limits.conf
echo "mailmcp hard nofile 65536" >> /etc/security/limits.conf

# 优化TCP连接
echo "net.core.somaxconn = 1024" >> /etc/sysctl.conf
echo "net.ipv4.tcp_tw_reuse = 1" >> /etc/sysctl.conf
sysctl -p
```

### 4. 内存优化
```bash
# 设置合理的内存限制 (systemd服务)
[Service]
MemoryLimit=2G
MemoryAccounting=true
```

## 📊 监控和日志

### 1. 内置监控
使用performance_stats工具获取性能指标：
```python
# 定期检查性能统计
stats = await performance_stats()
```

### 2. 日志配置
```python
# 在.env中配置日志
LOG_LEVEL=INFO
LOG_FILE=/opt/mail-mcp/logs/mail-mcp.log
```

### 3. Prometheus 监控
创建 `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'mail-mcp'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### 4. 日志轮转
创建 `/etc/logrotate.d/mail-mcp`:
```
/opt/mail-mcp/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    su mailmcp mailmcp
}
```

## 🔒 安全配置

### 1. 防火墙配置
```bash
# 只允许必要的出站连接
sudo ufw allow out 993/tcp   # IMAPS
sudo ufw allow out 587/tcp   # SMTP
sudo ufw allow out 465/tcp   # SMTPS
sudo ufw enable
```

### 2. SELinux 配置 (如果使用)
```bash
# 设置SELinux上下文
sudo setsebool -P httpd_can_network_connect 1
sudo semanage port -a -t http_port_t -p tcp 8000
```

### 3. SSL证书 (如果需要HTTPS)
```bash
# 使用Let's Encrypt
sudo certbot certonly --standalone -d mail-mcp.company.com

# 在服务配置中使用证书
SSL_CERT_PATH=/etc/letsencrypt/live/mail-mcp.company.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/mail-mcp.company.com/privkey.pem
```

## 🚨 故障排除

### 1. 常见问题

#### 连接失败
```bash
# 检查网络连接
telnet imap.qq.com 993
telnet smtp.qq.com 587

# 检查DNS解析
nslookup imap.qq.com
```

#### 认证失败
```bash
# 验证配置
python -c "
from mail_mcp.config import Config
config = Config()
print('IMAP配置:', config.imap.__dict__)
print('SMTP配置:', config.smtp.__dict__)
"
```

#### 性能问题
```bash
# 检查资源使用
htop
iostat -x 1
netstat -an | grep :8000
```

### 2. 调试模式
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python -m mail_mcp.main
```

### 3. 健康检查
```bash
# 检查服务状态
curl -f http://localhost:8000/health

# 检查性能统计
curl -X POST http://localhost:8000/performance_stats
```

## 📈 升级指南

### 1. 从v1.x升级
参考 [MIGRATION.md](../MIGRATION.md) 文档。

### 2. v2.x 版本升级
```bash
# 停止服务
sudo systemctl stop mail-mcp

# 备份配置
cp /opt/mail-mcp/.env /opt/mail-mcp/.env.backup

# 升级软件
sudo -u mailmcp -i
cd /opt/mail-mcp
source venv/bin/activate
pip install --upgrade mail-mcp

# 启动服务
sudo systemctl start mail-mcp

# 验证升级
sudo systemctl status mail-mcp
```

## 📞 技术支持

### 获取帮助
- 📖 查看 [README.md](../README.md) 了解基本使用
- 🔧 查看 [MIGRATION.md](../MIGRATION.md) 了解升级过程
- 🐛 提交 [Issue](https://github.com/your-repo/mail-mcp/issues) 报告问题
- 💬 加入社区讨论获取技术支持

### 企业支持
如需企业级支持，请联系我们获取：
- 专业部署服务
- 性能优化咨询
- 24/7 技术支持
- 定制化开发

---

**部署成功后，您将拥有一个高性能、安全可靠的邮件处理服务！**

🎉 **欢迎使用 Mail MCP Server v2.0！**