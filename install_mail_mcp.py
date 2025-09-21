#!/usr/bin/env python3
"""
Mail MCP 自动安装和配置脚本
"""

import json
import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def install_package():
    """安装mail-mcp包"""
    print("📦 正在安装 mail-mcp...")
    success, stdout, stderr = run_command("pip install mail-mcp")
    if success:
        print("✅ mail-mcp 安装成功!")
        return True
    else:
        print(f"❌ 安装失败: {stderr}")
        return False

def get_email_config():
    """获取用户邮箱配置"""
    print("\n📧 请输入您的邮箱配置信息:")
    
    # 邮箱服务提供商选择
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
        },
        "5": {
            "name": "自定义",
            "imap_host": "",
            "imap_port": "",
            "smtp_host": "",
            "smtp_port": ""
        }
    }
    
    print("\n请选择您的邮箱服务提供商:")
    for key, provider in providers.items():
        print(f"  {key}. {provider['name']}")
    
    choice = input("\n选择 (1-5): ").strip()
    
    if choice not in providers:
        print("❌ 无效选择，使用QQ邮箱配置")
        choice = "1"
    
    provider = providers[choice]
    config = {}
    
    if choice == "5":  # 自定义
        config["imap_host"] = input("IMAP主机地址: ").strip()
        config["imap_port"] = input("IMAP端口 (通常是993): ").strip() or "993"
        config["smtp_host"] = input("SMTP主机地址: ").strip()
        config["smtp_port"] = input("SMTP端口 (通常是587): ").strip() or "587"
    else:
        config["imap_host"] = provider["imap_host"]
        config["imap_port"] = provider["imap_port"]
        config["smtp_host"] = provider["smtp_host"]
        config["smtp_port"] = provider["smtp_port"]
    
    # 获取邮箱账号信息
    config["username"] = input(f"\n邮箱地址: ").strip()
    config["password"] = input("应用密码/授权码: ").strip()
    
    print(f"\n✅ 已配置 {provider['name']}")
    return config

def create_mcp_config(email_config):
    """创建MCP配置文件"""
    mcp_config = {
        "mcpServers": {
            "mail-mcp": {
                "command": "mail-mcp",
                "args": [],
                "env": {
                    "MAIL_IMAP_HOST": email_config["imap_host"],
                    "MAIL_IMAP_PORT": email_config["imap_port"],
                    "MAIL_IMAP_USERNAME": email_config["username"],
                    "MAIL_IMAP_PASSWORD": email_config["password"],
                    "MAIL_IMAP_USE_SSL": "true",
                    "MAIL_SMTP_HOST": email_config["smtp_host"],
                    "MAIL_SMTP_PORT": email_config["smtp_port"],
                    "MAIL_SMTP_USERNAME": email_config["username"],
                    "MAIL_SMTP_PASSWORD": email_config["password"],
                    "MAIL_SMTP_USE_TLS": "true"
                }
            }
        }
    }
    
    # 保存到当前目录
    config_file = Path.cwd() / ".mcp.json"
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(mcp_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ MCP配置文件已创建: {config_file}")
        return True
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False

def test_connection(email_config):
    """测试邮箱连接"""
    print("\n🔍 测试邮箱连接...")
    
    # 创建临时测试脚本
    test_script = """
import os
import imaplib
import smtplib
import ssl

def test_imap():
    try:
        context = ssl.create_default_context()
        with imaplib.IMAP4_SSL('{}', {}, ssl_context=context) as imap:
            imap.login('{}', '{}')
            imap.select('INBOX')
            return True
    except Exception as e:
        print(f"IMAP连接失败: {{e}}")
        return False

def test_smtp():
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP('{}', {}) as smtp:
            smtp.starttls(context=context)
            smtp.login('{}', '{}')
            return True
    except Exception as e:
        print(f"SMTP连接失败: {{e}}")
        return False

if __name__ == "__main__":
    imap_ok = test_imap()
    smtp_ok = test_smtp()
    
    if imap_ok and smtp_ok:
        print("✅ 邮箱连接测试成功!")
        exit(0)
    else:
        print("❌ 邮箱连接测试失败!")
        exit(1)
""".format(
        email_config["imap_host"],
        email_config["imap_port"], 
        email_config["username"],
        email_config["password"],
        email_config["smtp_host"],
        email_config["smtp_port"],
        email_config["username"],
        email_config["password"]
    )
    
    # 写入临时文件并执行
    test_file = Path.cwd() / "temp_test.py"
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_script)
        
        success, stdout, stderr = run_command(f"python {test_file}")
        test_file.unlink()  # 删除临时文件
        
        if success:
            print("✅ 邮箱连接测试成功!")
            return True
        else:
            print(f"❌ 邮箱连接测试失败!")
            if stderr:
                print(f"错误信息: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 测试脚本执行失败: {e}")
        if test_file.exists():
            test_file.unlink()
        return False

def show_usage_guide():
    """显示使用指南"""
    print("""
🎉 Mail MCP 安装配置完成!

📖 使用指南:
1. 启动Claude Code并确保在项目目录中
2. Mail MCP会自动加载，提供以下工具:
   
   📧 邮件操作:
   • list_messages - 列出邮件
   • get_message - 查看邮件详情
   • search_messages - 搜索邮件
   • send_email - 发送邮件
   • send_email_with_attachments - 发送带附件邮件
   • mark_as_read - 标记已读
   
   📎 附件操作:
   • list_attachments - 列出附件
   • download_attachments - 下载附件

3. 在Claude Code中可以直接使用，例如:
   "列出最新5封邮件"
   "搜索包含'重要'的邮件"
   "下载邮件1的所有附件"

🔧 配置文件位置: .mcp.json
📚 项目地址: https://github.com/LupinLin1/mail-mcp
""")

def main():
    """主函数"""
    print("🚀 Mail MCP 自动安装配置工具")
    print("=" * 50)
    
    # 1. 安装包
    if not install_package():
        print("❌ 安装失败，请检查网络连接或pip配置")
        sys.exit(1)
    
    # 2. 获取邮箱配置
    email_config = get_email_config()
    
    # 3. 测试连接
    if not test_connection(email_config):
        retry = input("\n连接测试失败，是否继续创建配置文件? (y/n): ").strip().lower()
        if retry != 'y':
            print("❌ 安装中止")
            sys.exit(1)
    
    # 4. 创建MCP配置
    if not create_mcp_config(email_config):
        sys.exit(1)
    
    # 5. 显示使用指南
    show_usage_guide()
    
    print("🎯 配置完成! 重启Claude Code即可使用Mail MCP功能")

if __name__ == "__main__":
    main()