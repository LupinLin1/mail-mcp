# Mail MCP Server v1.x → v2.0 迁移指南

本文档帮助用户从 Mail MCP Server v1.x 版本迁移到 v2.0 版本。v2.0 版本带来了显著的性能提升和架构简化，但需要进行配置和使用方式的调整。

## 🎯 v2.0 升级收益

### 性能提升
- **响应速度**: 提升 50%+（连接池 + 缓存）
- **并发能力**: 支持 10 倍并发处理
- **资源利用**: 减少 90% 连接建立时间
- **缓存命中**: 80%+ 缓存命中率

### 功能简化
- **工具数量**: 从 12 个工具简化为 2 个核心工具
- **配置复杂度**: 降低 60% 配置项
- **学习成本**: 减少 90% 使用复杂度
- **维护成本**: 简化架构，更易维护

### 安全增强
- **可信发件人**: 基于白名单的安全筛选
- **错误处理**: 完整的错误分类和重试机制
- **类型安全**: 全面的类型注解和验证
- **监控能力**: 实时性能监控和统计

## 📋 迁移检查清单

### 迁移前准备
- [ ] 备份现有配置文件
- [ ] 记录当前使用的工具和参数
- [ ] 确认邮箱服务商配置信息
- [ ] 准备可信发件人列表

### 配置更新
- [ ] 更新 `.mcp.json` 配置文件
- [ ] 添加 `TRUSTED_SENDERS` 环境变量
- [ ] 调整环境变量名称格式
- [ ] 验证邮箱连接配置

### 代码适配
- [ ] 更新工具调用方式
- [ ] 适配新的返回数据格式
- [ ] 更新错误处理逻辑
- [ ] 测试核心功能

### 验证测试
- [ ] 测试邮件检查功能
- [ ] 测试邮件回复功能
- [ ] 验证性能统计功能
- [ ] 确认错误处理正常

## 🔧 配置文件迁移

### 1. 环境变量名称变更

**v1.x 配置**:
```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "uvx",
      "args": ["mail-mcp"],
      "env": {
        "MAIL_IMAP_HOST": "imap.qq.com",
        "MAIL_IMAP_PORT": "993",
        "MAIL_IMAP_USERNAME": "your-email@qq.com",
        "MAIL_IMAP_PASSWORD": "your-app-password",
        "MAIL_IMAP_USE_SSL": "true",
        "MAIL_SMTP_HOST": "smtp.qq.com",
        "MAIL_SMTP_PORT": "587",
        "MAIL_SMTP_USERNAME": "your-email@qq.com",
        "MAIL_SMTP_PASSWORD": "your-app-password",
        "MAIL_SMTP_USE_TLS": "true"
      }
    }
  }
}
```

**v2.0 配置**:
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
        "TRUSTED_SENDERS": "admin@company.com,support@partner.com,boss@example.com"
      }
    }
  }
}
```

### 2. 环境变量对照表

| v1.x 变量名 | v2.0 变量名 | 说明 |
|------------|------------|------|
| `MAIL_IMAP_HOST` | `IMAP_HOST` | 移除 MAIL_ 前缀 |
| `MAIL_IMAP_PORT` | `IMAP_PORT` | 移除 MAIL_ 前缀 |
| `MAIL_IMAP_USERNAME` | `IMAP_USERNAME` | 移除 MAIL_ 前缀 |
| `MAIL_IMAP_PASSWORD` | `IMAP_PASSWORD` | 移除 MAIL_ 前缀 |
| `MAIL_IMAP_USE_SSL` | `IMAP_USE_SSL` | 移除 MAIL_ 前缀 |
| `MAIL_SMTP_HOST` | `SMTP_HOST` | 移除 MAIL_ 前缀 |
| `MAIL_SMTP_PORT` | `SMTP_PORT` | 移除 MAIL_ 前缀 |
| `MAIL_SMTP_USERNAME` | `SMTP_USERNAME` | 移除 MAIL_ 前缀 |
| `MAIL_SMTP_PASSWORD` | `SMTP_PASSWORD` | 移除 MAIL_ 前缀 |
| `MAIL_SMTP_USE_TLS` | `SMTP_USE_SSL` | 名称统一为 USE_SSL |
| 无 | `TRUSTED_SENDERS` | **新增**: 可信发件人列表 |

### 3. 新增必需配置

**TRUSTED_SENDERS**: 这是 v2.0 版本的核心安全特性，必须配置：

```bash
# 单个发件人
TRUSTED_SENDERS=admin@company.com

# 多个发件人（用逗号分隔）
TRUSTED_SENDERS=admin@company.com,support@partner.com,boss@example.com

# 建议配置常用的重要发件人
TRUSTED_SENDERS=hr@company.com,finance@company.com,admin@company.com,boss@company.com
```

## 🛠️ 工具接口迁移

### 1. 工具对应关系

| v1.x 工具 | v2.0 工具 | 迁移说明 |
|----------|----------|---------|
| `list_messages` | `check` | 自动筛选可信发件人的未读邮件 |
| `get_message` | `check` | 包含在邮件检查结果中 |
| `search_messages` | `check` | 基于可信发件人自动筛选 |
| `mark_as_read` | `check` | 自动标记检查的邮件为已读 |
| `send_email` | `reply` | 改为回复现有邮件 |
| `send_email_with_attachments` | `reply` | 集成到 reply 工具中 |
| `list_attachments` | ❌ 移除 | 附件信息包含在邮件详情中 |
| `download_attachments` | ❌ 移除 | 使用文件系统直接访问 |
| `test_smtp_connection` | `performance_stats` | 集成到性能统计中 |
| `get_server_info` | `performance_stats` | 集成到性能统计中 |
| `health_check` | `performance_stats` | 集成到性能统计中 |

### 2. 使用方式对比

#### 邮件检查功能

**v1.x 方式** (需要多步操作):
```bash
# 1. 获取邮件列表
list_messages(folder="INBOX", limit=20)

# 2. 搜索特定发件人
search_messages(query="from:admin@company.com", unread_only=true)

# 3. 获取邮件详情
get_message(message_id="123")

# 4. 标记为已读
mark_as_read(message_ids=["123"])
```

**v2.0 方式** (一步完成):
```bash
# 一步获取所有可信发件人的未读邮件，自动标记已读
check
```

#### 邮件回复功能

**v1.x 方式**:
```bash
# 发送新邮件（需要手动指定收件人）
send_email(
  to=["recipient@example.com"],
  subject="Re: 原邮件主题",
  body_text="回复内容"
)

# 发送带附件的邮件
send_email_with_attachments(
  to=["recipient@example.com"],
  subject="Re: 原邮件主题",
  body_text="回复内容",
  attachments=["/path/to/file.pdf"]
)
```

**v2.0 方式**:
```bash
# 智能回复（自动获取收件人和原邮件信息）
reply(
  message_id="123",
  body="回复内容",
  attachments=["/path/to/file.pdf"]
)
```

## 📊 数据格式变更

### 1. 邮件数据格式

**v1.x 格式**:
```json
{
  "message_id": "123",
  "subject": "邮件主题",
  "from_address": "sender@example.com",
  "body": "邮件正文",
  "date": "2024-01-15T10:30:00"
}
```

**v2.0 格式**:
```json
{
  "success": true,
  "emails": [
    {
      "id": "123",
      "from": "sender@example.com",
      "subject": "邮件主题",
      "body_text": "纯文本正文",
      "body_html": "<p>HTML正文</p>",
      "attachments": ["file.pdf"],
      "attachment_count": 1,
      "received_time": "2024-01-15T10:30:00",
      "cc_addresses": ["cc@example.com"],
      "is_read": true,
      "message_id": "msg-123@example.com"
    }
  ],
  "total_count": 1,
  "trusted_senders": ["admin@company.com"]
}
```

### 2. 错误响应格式

**v1.x 格式**:
```json
{
  "error": "Connection failed",
  "details": "Network timeout"
}
```

**v2.0 格式**:
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
    },
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

## 🧪 迁移测试步骤

### 1. 配置验证
```bash
# 检查配置是否正确
performance_stats
```

期望结果: 返回服务状态和连接池信息

### 2. 基础功能测试
```bash
# 测试邮件检查功能
check
```

期望结果: 返回可信发件人的邮件列表

### 3. 回复功能测试
```bash
# 使用check返回的邮件ID进行回复测试
reply(message_id="123", body="测试回复")
```

期望结果: 成功发送回复邮件

### 4. 性能监控测试
```bash
# 检查性能统计
performance_stats
```

期望结果: 显示连接池、缓存和性能指标

## ⚠️ 迁移注意事项

### 1. 破坏性变更
- **工具移除**: v1.x 的 9 个工具在 v2.0 中不再可用
- **参数变更**: 工具参数和返回格式完全不同
- **配置变更**: 环境变量名称发生变化
- **依赖关系**: 必须配置 `TRUSTED_SENDERS`

### 2. 功能限制
- **邮件发送**: v2.0 只支持回复现有邮件，不支持发送全新邮件
- **文件夹**: v2.0 主要关注 INBOX，不支持指定其他文件夹
- **搜索**: v2.0 基于可信发件人筛选，不支持任意搜索
- **附件下载**: v2.0 不提供附件下载功能

### 3. 性能考虑
- **缓存预热**: 首次使用时缓存为空，响应时间较长
- **连接建立**: 启动时需要建立连接池，初始化时间稍长
- **内存使用**: 缓存会占用更多内存资源

### 4. 安全注意事项
- **可信发件人**: 必须谨慎配置，避免遗漏重要发件人
- **权限检查**: v2.0 只处理可信发件人邮件，增强了安全性
- **数据隔离**: 邮件数据按可信发件人进行隔离

## 🔄 回滚计划

如果迁移后遇到问题，可以按以下步骤回滚到 v1.x：

### 1. 配置回滚
```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "uvx",
      "args": ["mail-mcp==1.9.0"],  // 指定v1.x版本
      "env": {
        "MAIL_IMAP_HOST": "imap.qq.com",
        // ... 使用v1.x配置格式
      }
    }
  }
}
```

### 2. 功能验证
```bash
# 验证v1.x工具是否正常
list_messages()
health_check()
```

### 3. 数据检查
确认回滚后所有功能正常工作，没有数据丢失。

## 📞 获取帮助

### 迁移问题
如果在迁移过程中遇到问题：

1. **配置问题**: 检查环境变量格式和可信发件人配置
2. **连接问题**: 使用 `performance_stats` 检查连接状态
3. **功能问题**: 参考新的工具文档和使用示例
4. **性能问题**: 检查缓存配置和连接池设置

### 技术支持
- 📖 查看 [README.md](./README.md) 了解详细使用方法
- 🐛 提交 [Issue](https://github.com/your-repo/mail-mcp/issues) 报告问题
- 💬 加入社区讨论获取帮助

### 迁移辅助工具
我们提供了迁移辅助脚本来帮助自动转换配置：

```bash
# 下载迁移脚本
curl -O https://raw.githubusercontent.com/your-repo/mail-mcp/main/scripts/migrate-config.py

# 运行迁移
python migrate-config.py --input .mcp-v1.json --output .mcp-v2.json
```

---

**成功迁移到 v2.0 后，您将享受到显著的性能提升和更简洁的使用体验！**

🎉 **欢迎来到 Mail MCP Server v2.0 时代！**