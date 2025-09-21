#!/usr/bin/env python3
"""
Mail MCP 自动安装启动器
当MCP服务器启动时自动安装mail-mcp包（如果尚未安装）
"""

import subprocess
import sys
import importlib.util

def ensure_package_installed():
    """确保mail-mcp包已安装"""
    # 检查包是否已安装
    spec = importlib.util.find_spec("mail_mcp")
    if spec is None:
        print("📦 正在自动安装 mail-mcp...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "mail-mcp"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ mail-mcp 安装成功!")
        except subprocess.CalledProcessError as e:
            print(f"❌ 安装失败: {e}")
            sys.exit(1)
    
    # 导入并启动服务
    try:
        from mail_mcp.main import sync_main
        sync_main()
    except ImportError as e:
        print(f"❌ 导入mail_mcp失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ensure_package_installed()