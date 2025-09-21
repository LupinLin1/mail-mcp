# Mail MCP 快速配置指南

## 🚀 一键自动安装配置

只需要在项目中创建 `.mcp.json` 文件，Mail MCP 会自动安装！

### 方法1: 使用自动安装配置（推荐）

复制以下内容到你的项目 `.mcp.json` 文件：

```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "python",
      "args": ["-c", "import subprocess,sys,importlib.util;spec=importlib.util.find_spec('mail_mcp');subprocess.check_call([sys.executable,'-m','pip','install','mail-mcp']) if spec is None else None;from mail_mcp.main import sync_main;sync_main()"],
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

### 方法2: 使用启动脚本

1. 下载 `mail_mcp_auto.py` 启动脚本
2. 配置 `.mcp.json`:

```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "python",
      "args": ["mail_mcp_auto.py"],
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

## 📧 邮箱配置说明

### QQ邮箱
```
MAIL_IMAP_HOST: imap.qq.com
MAIL_SMTP_HOST: smtp.qq.com
```

### Gmail  
```
MAIL_IMAP_HOST: imap.gmail.com
MAIL_SMTP_HOST: smtp.gmail.com
```

### Outlook
```
MAIL_IMAP_HOST: outlook.office365.com
MAIL_SMTP_HOST: smtp-mail.outlook.com
```

### 163邮箱
```
MAIL_IMAP_HOST: imap.163.com
MAIL_SMTP_HOST: smtp.163.com
```

## 🔐 获取应用密码

- **QQ邮箱**: 设置 → 账户 → 开启IMAP/SMTP → 获取授权码
- **Gmail**: Google账户 → 安全性 → 应用密码
- **Outlook**: 账户设置 → 安全性 → 应用密码

## ✅ 使用方法

1. 配置好 `.mcp.json` 文件
2. 启动 Claude Code 
3. Mail MCP 会自动安装并启动
4. 直接使用邮件功能：
   - "列出最新5封邮件"
   - "搜索包含'重要'的邮件" 
   - "发送邮件给xxx"
   - "下载邮件的附件"

## 🎯 特性

- ✅ **自动安装**: 首次使用时自动安装依赖
- ✅ **智能附件**: 精准识别真实附件，过滤嵌入内容
- ✅ **多邮箱支持**: QQ、Gmail、Outlook、163等
- ✅ **安全连接**: SSL/TLS加密传输
- ✅ **异步高性能**: 基于FastMCP框架

重启 Claude Code 即可使用！🚀