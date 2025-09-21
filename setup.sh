#!/bin/bash

# Mail MCP 一键安装配置脚本

echo "🚀 Mail MCP 一键安装配置工具"
echo "=================================="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python"
    exit 1
fi

# 安装mail-mcp
echo "📦 正在安装 mail-mcp..."
if pip install mail-mcp; then
    echo "✅ mail-mcp 安装成功!"
else
    echo "❌ 安装失败，请检查网络连接"
    exit 1
fi

# 运行配置脚本
echo ""
echo "🔧 开始配置..."
python3 - << 'EOF'
import json
import os

# 邮箱服务配置模板
providers = {
    "1": {
        "name": "QQ邮箱",
        "imap_host": "imap.qq.com",
        "imap_port": "993",
        "smtp_host": "smtp.qq.com",
        "smtp_port": "587"
    },
    "2": {
        "name": "Gmail",
        "imap_host": "imap.gmail.com",
        "imap_port": "993", 
        "smtp_host": "smtp.gmail.com",
        "smtp_port": "587"
    },
    "3": {
        "name": "Outlook/Hotmail",
        "imap_host": "outlook.office365.com",
        "imap_port": "993",
        "smtp_host": "smtp-mail.outlook.com",
        "smtp_port": "587"
    },
    "4": {
        "name": "163邮箱", 
        "imap_host": "imap.163.com",
        "imap_port": "993",
        "smtp_host": "smtp.163.com",
        "smtp_port": "587"
    }
}

print("\n📧 请选择您的邮箱服务提供商:")
for key, provider in providers.items():
    print(f"  {key}. {provider['name']}")

choice = input("\n选择 (1-4): ").strip()

if choice not in providers:
    print("❌ 无效选择，使用QQ邮箱配置")
    choice = "1"

provider = providers[choice]
print(f"\n✅ 已选择 {provider['name']}")

# 获取用户输入
username = input("\n邮箱地址: ").strip()
password = input("应用密码/授权码: ").strip()

# 创建MCP配置
mcp_config = {
    "mcpServers": {
        "mail-mcp": {
            "command": "mail-mcp",
            "args": [],
            "env": {
                "MAIL_IMAP_HOST": provider["imap_host"],
                "MAIL_IMAP_PORT": provider["imap_port"],
                "MAIL_IMAP_USERNAME": username,
                "MAIL_IMAP_PASSWORD": password,
                "MAIL_IMAP_USE_SSL": "true",
                "MAIL_SMTP_HOST": provider["smtp_host"],
                "MAIL_SMTP_PORT": provider["smtp_port"],
                "MAIL_SMTP_USERNAME": username,
                "MAIL_SMTP_PASSWORD": password,
                "MAIL_SMTP_USE_TLS": "true"
            }
        }
    }
}

# 保存配置文件
try:
    with open(".mcp.json", "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2, ensure_ascii=False)
    print(f"✅ MCP配置文件已创建: .mcp.json")
except Exception as e:
    print(f"❌ 创建配置文件失败: {e}")
    exit(1)

print("""
🎉 Mail MCP 安装配置完成!

📖 使用方法:
1. 在项目目录中启动Claude Code
2. Mail MCP会自动加载，提供邮件操作功能
3. 可以直接说"列出最新邮件"、"发送邮件"等

🔧 配置文件: .mcp.json
📚 项目地址: https://github.com/LupinLin1/mail-mcp

重启Claude Code即可使用! 🚀
""")
EOF

echo "🎯 安装配置完成!"