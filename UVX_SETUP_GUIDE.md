# Mail MCP 超简单配置指南 (使用 uvx)

## 🚀 最简单的方式：使用 uvx

`uvx` 会自动下载、安装和运行 Mail MCP，无需任何预安装！

### 1. 确保安装了 uv
```bash
# 如果没有安装 uv，先安装：
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 创建 `.mcp.json` 配置文件

只需要这一个配置文件，`uvx` 会自动处理安装：

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

### 3. 启动 Claude Code

就是这么简单！`uvx` 会：
- 自动下载 mail-mcp 包
- 创建隔离的运行环境
- 启动 Mail MCP 服务器

## 📧 不同邮箱服务的配置

### QQ邮箱（默认）
```json
"MAIL_IMAP_HOST": "imap.qq.com",
"MAIL_SMTP_HOST": "smtp.qq.com"
```

### Gmail
```json
"MAIL_IMAP_HOST": "imap.gmail.com", 
"MAIL_SMTP_HOST": "smtp.gmail.com"
```

### Outlook/Hotmail
```json
"MAIL_IMAP_HOST": "outlook.office365.com",
"MAIL_SMTP_HOST": "smtp-mail.outlook.com"
```

### 163邮箱
```json
"MAIL_IMAP_HOST": "imap.163.com",
"MAIL_SMTP_HOST": "smtp.163.com"
```

## 🔐 获取应用密码

1. **QQ邮箱**: 设置 → 账户 → 开启IMAP/SMTP → 获取授权码
2. **Gmail**: Google账户 → 安全性 → 两步验证 → 应用密码
3. **Outlook**: 账户设置 → 安全性 → 应用密码
4. **163邮箱**: 设置 → POP3/IMAP/SMTP → 授权码

## ✨ uvx 的优势

- ✅ **零安装**: 不需要预先安装 mail-mcp
- ✅ **隔离环境**: 自动创建独立的Python环境
- ✅ **自动更新**: 每次运行都使用最新版本
- ✅ **无污染**: 不会影响系统Python环境
- ✅ **一键配置**: 只需要一个配置文件

## 🎯 完整示例配置

```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "uvx", 
      "args": ["mail-mcp"],
      "env": {
        "MAIL_IMAP_HOST": "imap.qq.com",
        "MAIL_IMAP_PORT": "993",
        "MAIL_IMAP_USERNAME": "your_actual_email@qq.com",
        "MAIL_IMAP_PASSWORD": "your_actual_app_password",
        "MAIL_IMAP_USE_SSL": "true",
        "MAIL_SMTP_HOST": "smtp.qq.com",
        "MAIL_SMTP_PORT": "587", 
        "MAIL_SMTP_USERNAME": "your_actual_email@qq.com",
        "MAIL_SMTP_PASSWORD": "your_actual_app_password",
        "MAIL_SMTP_USE_TLS": "true"
      }
    }
  }
}
```

**记得替换**:
- `your_actual_email@qq.com` → 你的真实邮箱地址
- `your_actual_app_password` → 你的应用专用密码/授权码

## 🚀 使用方法

1. 创建上述 `.mcp.json` 文件
2. 启动 Claude Code
3. 开始使用邮件功能：
   - "列出最新邮件"
   - "搜索重要邮件"
   - "发送邮件"
   - "下载附件"

就是这么简单！🎉