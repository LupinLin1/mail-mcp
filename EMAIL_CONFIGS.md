# 邮箱服务配置示例

## QQ邮箱配置
```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "mail-mcp",
      "args": [],
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

## Gmail配置
```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "mail-mcp", 
      "args": [],
      "env": {
        "MAIL_IMAP_HOST": "imap.gmail.com",
        "MAIL_IMAP_PORT": "993",
        "MAIL_IMAP_USERNAME": "your-email@gmail.com",
        "MAIL_IMAP_PASSWORD": "your-app-password",
        "MAIL_IMAP_USE_SSL": "true",
        "MAIL_SMTP_HOST": "smtp.gmail.com",
        "MAIL_SMTP_PORT": "587",
        "MAIL_SMTP_USERNAME": "your-email@gmail.com",
        "MAIL_SMTP_PASSWORD": "your-app-password",
        "MAIL_SMTP_USE_TLS": "true"
      }
    }
  }
}
```

## Outlook/Hotmail配置
```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "mail-mcp",
      "args": [],
      "env": {
        "MAIL_IMAP_HOST": "outlook.office365.com",
        "MAIL_IMAP_PORT": "993", 
        "MAIL_IMAP_USERNAME": "your-email@outlook.com",
        "MAIL_IMAP_PASSWORD": "your-app-password",
        "MAIL_IMAP_USE_SSL": "true",
        "MAIL_SMTP_HOST": "smtp-mail.outlook.com",
        "MAIL_SMTP_PORT": "587",
        "MAIL_SMTP_USERNAME": "your-email@outlook.com",
        "MAIL_SMTP_PASSWORD": "your-app-password",
        "MAIL_SMTP_USE_TLS": "true"
      }
    }
  }
}
```

## 163邮箱配置
```json
{
  "mcpServers": {
    "mail-mcp": {
      "command": "mail-mcp",
      "args": [],
      "env": {
        "MAIL_IMAP_HOST": "imap.163.com",
        "MAIL_IMAP_PORT": "993",
        "MAIL_IMAP_USERNAME": "your-email@163.com", 
        "MAIL_IMAP_PASSWORD": "your-app-password",
        "MAIL_IMAP_USE_SSL": "true",
        "MAIL_SMTP_HOST": "smtp.163.com",
        "MAIL_SMTP_PORT": "587",
        "MAIL_SMTP_USERNAME": "your-email@163.com",
        "MAIL_SMTP_PASSWORD": "your-app-password",
        "MAIL_SMTP_USE_TLS": "true"
      }
    }
  }
}
```

## 配置说明

### 🔐 获取应用密码

#### QQ邮箱
1. 登录QQ邮箱 → 设置 → 账户
2. 开启"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
3. 获取授权码作为密码

#### Gmail  
1. Google账户 → 安全性 → 两步验证（必须开启）
2. 应用密码 → 生成应用密码
3. 使用生成的16位密码

#### Outlook
1. 账户设置 → 安全性 → 高级安全选项
2. 应用密码 → 创建新的应用密码
3. 使用生成的密码

### 📧 端口说明
- **IMAP**: 通常使用993端口(SSL)或143端口(无SSL)
- **SMTP**: 通常使用587端口(TLS)或25端口(无加密)

### 🔒 安全设置
- 建议使用SSL/TLS加密连接
- 使用应用专用密码，不要使用账户主密码
- 定期更换应用密码