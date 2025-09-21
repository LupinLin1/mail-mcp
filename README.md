# Mail MCP Server

一个基于 FastMCP 框架的邮件服务器，支持 IMAP 和 SMTP 协议，提供邮件收发、搜索、附件处理等功能的 MCP (Model Context Protocol) 服务。

## 功能特性

### 📧 邮件操作
- **邮件列表获取**: 支持分页浏览邮件列表
- **邮件详情查看**: 完整解析邮件内容，支持 HTML 和纯文本
- **邮件搜索**: 按发件人、收件人、主题、正文搜索邮件
- **邮件标记**: 支持标记已读/未读状态
- **邮件删除**: 安全删除邮件功能

### 📤 邮件发送
- **基础邮件发送**: 支持纯文本和 HTML 邮件
- **附件支持**: 支持多个文件附件，自动 MIME 类型检测
- **抄送/密送**: 支持 CC 和 BCC 功能
- **文件大小限制**: 默认 25MB 附件大小限制

### 🔒 安全连接
- **SSL/TLS 支持**: 支持 IMAPS 和 SMTPS 协议
- **连接重试**: 指数退避重试机制
- **认证安全**: 支持用户名密码认证
- **错误处理**: 完整的错误分类和异常处理

### 🛠️ 开发特性
- **异步设计**: 基于 asyncio 的高性能异步架构
- **类型安全**: 完整的类型注解和 mypy 检查
- **测试覆盖**: 全面的单元测试覆盖
- **日志记录**: 详细的操作日志和错误追踪

## 安装和配置

### 环境要求
- Python 3.8+
- FastMCP 框架

### 安装依赖
```bash
pip install fastmcp python-dotenv
```

### 环境变量配置
创建 `.env` 文件：

```env
# IMAP 服务器配置
IMAP_HOST=imap.qiye.aliyun.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USERNAME=your_email@example.com
IMAP_PASSWORD=your_password

# SMTP 服务器配置
SMTP_HOST=smtp.qiye.aliyun.com
SMTP_PORT=465
SMTP_USE_SSL=true
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_password

# 服务器配置
SERVER_HOST=localhost
SERVER_PORT=8080
LOG_LEVEL=INFO
```

### 配置示例
以下是常见邮箱服务商的配置：

#### 阿里云企业邮箱
```env
IMAP_HOST=imap.qiye.aliyun.com
IMAP_PORT=993
SMTP_HOST=smtp.qiye.aliyun.com
SMTP_PORT=465
```

#### 腾讯企业邮箱
```env
IMAP_HOST=imap.exmail.qq.com
IMAP_PORT=993
SMTP_HOST=smtp.exmail.qq.com
SMTP_PORT=465
```

#### 网易企业邮箱
```env
IMAP_HOST=imap.ym.163.com
IMAP_PORT=993
SMTP_HOST=smtp.ym.163.com
SMTP_PORT=465
```

#### Gmail
```env
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_SSL=false  # Gmail 使用 STARTTLS
```

## 使用方法

### 启动服务器
```bash
# 方法1: 直接运行主程序
python main.py

# 方法2: 使用模块方式
python -m mail_mcp.main

# 方法3: 如果安装了包
mail-mcp
```

### MCP 工具列表

#### 邮件接收工具

**list_messages** - 获取邮件列表
```python
await list_messages(
    folder="INBOX",     # 邮件文件夹，默认 INBOX
    limit=20,           # 返回邮件数量，默认 20
    offset=0            # 偏移量，用于分页
)
```

**get_message** - 获取邮件详情
```python
await get_message(
    message_id="123",    # 邮件 ID
    folder="INBOX"       # 邮件文件夹
)
```

**search_messages** - 搜索邮件（简化接口）
```python
await search_messages(
    query="搜索关键词",          # 搜索关键词（在主题、发件人、收件人、正文中搜索）
    folder="INBOX",             # 邮件文件夹，默认 INBOX
    unread_only=False,         # 是否只搜索未读邮件，默认 false
    limit=20                   # 返回结果数量限制，默认 20
)
```

**mark_as_read** - 标记邮件已读（支持批量操作）
```python
await mark_as_read(
    message_ids=["123", "456", "789"]    # 邮件 ID 列表（支持单个或批量）
)
```

#### 邮件发送工具

**send_email** - 发送邮件
```python
await send_email(
    to=["recipient@example.com"],    # 收件人列表
    subject="邮件主题",                # 邮件主题
    body_text="邮件正文",              # 纯文本正文
    body_html="<p>HTML 正文</p>",     # HTML 正文（可选）
    cc=["cc@example.com"],            # 抄送列表（可选）
    bcc=["bcc@example.com"]           # 密送列表（可选）
)
```

**send_email_with_attachments** - 发送带附件的邮件
```python
await send_email_with_attachments(
    to=["recipient@example.com"],        # 收件人列表
    subject="带附件的邮件",                # 邮件主题
    body_text="请查看附件",                # 纯文本正文
    attachments=["/path/to/file1.pdf", "/path/to/file2.jpg"],  # 附件路径列表
    body_html="<p>HTML 正文</p>",       # HTML 正文（可选）
    cc=["cc@example.com"],              # 抄送列表（可选）
    bcc=["bcc@example.com"]             # 密送列表（可选）
)
```

#### 服务器管理工具

**test_smtp_connection** - 测试 SMTP 连接
```python
await test_smtp_connection()
```

**get_server_info** - 获取服务器信息
```python
await get_server_info()
```

**health_check** - 健康检查
```python
await health_check()
```

## 错误处理

### 错误分类
系统定义了以下错误类型：

- **ConfigurationError**: 配置错误
- **NetworkError**: 网络连接错误
- **AuthenticationError**: 认证失败错误
- **ValidationError**: 参数验证错误
- **FileSystemError**: 文件系统错误
- **EmailParsingError**: 邮件解析错误
- **ProtocolError**: 协议错误

### 错误响应格式
```json
{
  "success": false,
  "error": {
    "code": "NETWORK_CONNECT_FAILED",
    "category": "network", 
    "message": "连接超时",
    "details": {
      "host": "imap.example.com",
      "port": 993,
      "timeout": 30
    }
  }
}
```

### 常见错误和解决方案

#### 认证失败
```
[AUTH_FAILED] 认证失败：用户名或密码错误
```
**解决方案**: 检查用户名和密码是否正确，确认开启了 IMAP/SMTP 服务。

#### 网络连接失败
```
[NETWORK_CONNECT_FAILED] 连接超时
```
**解决方案**: 检查网络连接，确认防火墙设置，验证服务器地址和端口。

#### 文件不存在
```
[VALIDATION_FILE_NOT_FOUND] 文件不存在: /path/to/file.pdf
```
**解决方案**: 检查文件路径是否正确，确认文件存在且有读取权限。

#### 文件过大
```
[VALIDATION_FILE_TOO_LARGE] 文件大小超过限制 (26214400 > 25165824 bytes)
```
**解决方案**: 压缩文件或分割成多个小文件发送。

## 开发指南

### 项目结构
```
mail-mcp/
├── mail_mcp/               # 主模块
│   ├── __init__.py
│   ├── main.py            # MCP 服务器入口
│   ├── config.py          # 配置管理
│   ├── imap_service.py    # IMAP 服务实现
│   ├── smtp_service.py    # SMTP 服务实现
│   ├── models.py          # 数据模型
│   ├── utils.py           # 工具函数
│   └── errors.py          # 错误处理
├── tests/                  # 测试文件
├── .env                    # 环境变量
├── pyproject.toml         # 项目配置
└── README.md              # 项目文档
```

### 添加新功能
1. 在相应服务文件中实现功能
2. 添加错误处理和日志记录
3. 编写单元测试
4. 在 main.py 中注册 MCP 工具
5. 更新文档

### 测试
运行所有测试：
```bash
pytest
```

运行特定测试：
```bash
pytest tests/test_imap_service.py
```

生成测试覆盖率报告：
```bash
pytest --cov=mail_mcp --cov-report=html
```

### 代码质量检查
```bash
# 类型检查
mypy mail_mcp/

# 代码格式化
ruff check mail_mcp/
ruff format mail_mcp/

# 导入排序
ruff check --select I mail_mcp/
```

## 性能优化

### 连接池管理
- IMAP 和 SMTP 连接自动复用
- 连接超时自动重连
- 指数退避重试机制

### 内存优化
- 大文件流式处理
- 邮件内容分块解析
- 及时释放资源

### 并发处理
- 异步 I/O 操作
- 连接锁防止并发冲突
- 合理的超时设置

## 监控和日志

### 日志级别
- **DEBUG**: 详细的调试信息
- **INFO**: 一般操作信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息

### 日志配置
在 `.env` 中设置日志级别：
```env
LOG_LEVEL=INFO
```

或指定日志文件：
```env
LOG_FILE=/var/log/mail-mcp.log
```

### 关键指标
- 连接成功率和失败率
- 邮件处理时间
- 错误类型分布
- 系统资源使用情况

## 安全考虑

### 数据安全
- 密码安全存储（使用环境变量）
- 传输层加密（SSL/TLS）
- 敏感信息日志脱敏

### 访问控制
- 认证验证
- 参数输入验证
- 文件路径安全检查

### 错误信息
- 避免泄露敏感信息
- 提供用户友好的错误消息
- 详细的开发者调试信息

## 常见问题解答

### Q: 如何配置邮箱服务？
A: 参考"配置示例"部分，根据你的邮箱服务商设置正确的服务器地址、端口和 SSL 配置。

### Q: 支持哪些邮箱服务商？
A: 支持所有标准 IMAP/SMTP 协议的邮箱，包括阿里云企业邮箱、腾讯企业邮箱、网易企业邮箱、Gmail、Outlook 等。

### Q: 附件大小限制是多少？
A: 默认限制为 25MB，可以在代码中修改 `MAX_ATTACHMENT_SIZE` 常量调整。

### Q: 如何处理中文乱码？
A: 系统自动处理邮件编码，支持 UTF-8、GBK 等多种编码格式。

### Q: 如何提高连接稳定性？
A: 系统内置重试机制和连接池管理，如需进一步优化可调整重试次数和延迟时间。

## 许可证

本项目采用 MIT 许可证。详情请参阅 LICENSE 文件。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 支持

如果你在使用过程中遇到问题，请：

1. 查看本文档的常见问题解答
2. 检查日志文件获取详细错误信息
3. 提交 Issue 描述问题

---

**Mail MCP Server** - 让邮件操作更简单！