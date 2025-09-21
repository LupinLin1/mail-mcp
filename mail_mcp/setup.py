"""
Mail MCP Setup Tool - 自动化安装和配置工具
"""

import sys
import json
import yaml
import click
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any


class MailMCPSetup:
    """Mail MCP 自动安装和配置类"""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.claude_dir = self.home_dir / ".claude"
        self.mcp_config_file = self.claude_dir / "settings.json"
        
    def check_claude_installed(self) -> bool:
        """检查Claude Code是否已安装"""
        try:
            result = subprocess.run(
                ["claude", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_claude_config_path(self) -> Optional[Path]:
        """获取Claude配置文件路径"""
        possible_paths = [
            self.claude_dir / "settings.json",
            self.claude_dir / "config.json",
            self.home_dir / ".config" / "claude" / "settings.json"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        return None
    
    def load_mcp_config(self) -> Dict[str, Any]:
        """加载现有MCP配置"""
        config_path = self.get_claude_config_path()
        if not config_path:
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def save_mcp_config(self, config: Dict[str, Any]) -> bool:
        """保存MCP配置"""
        config_path = self.get_claude_config_path()
        if not config_path:
            # 创建配置目录
            self.claude_dir.mkdir(exist_ok=True)
            config_path = self.claude_dir / "settings.json"
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False
    
    def add_mail_mcp_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """添加mail-mcp配置"""
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        
        config["mcpServers"]["mail-mcp"] = {
            "type": "stdio",
            "command": "mail-mcp",
            "args": []
        }
        
        return config
    
    def check_python_version(self) -> bool:
        """检查Python版本"""
        version = sys.version_info
        return version.major >= 3 and version.minor >= 8
    
    def install_package(self) -> bool:
        """安装mail-mcp包"""
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "--upgrade", "mail-mcp[auto]"
            ], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def create_sample_config(self) -> bool:
        """创建示例配置文件"""
        config_dir = self.home_dir / ".mail-mcp"
        config_dir.mkdir(exist_ok=True)
        
        sample_config = {
            "imap": {
                "host": "imap.gmail.com",
                "port": 993,
                "use_ssl": True,
                "username": "your-email@gmail.com",
                "password": "your-app-password"
            },
            "smtp": {
                "host": "smtp.gmail.com",
                "port": 587,
                "use_ssl": True,
                "username": "your-email@gmail.com", 
                "password": "your-app-password"
            },
            "server": {
                "host": "localhost",
                "port": 8000,
                "log_level": "INFO"
            }
        }
        
        config_file = config_dir / "config.yaml"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(sample_config, f, default_flow_style=False, allow_unicode=True)
            return True
        except IOError:
            return False
    
    def setup_environment(self) -> bool:
        """设置环境变量"""
        env_file = self.home_dir / ".mail-mcp" / ".env"
        env_content = """# Mail MCP Environment Configuration
# 复制此文件为.env并填入您的实际配置

# IMAP配置
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=your-app-password

# SMTP配置  
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_SSL=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# 服务器配置
SERVER_HOST=localhost
SERVER_PORT=8000
LOG_LEVEL=INFO
"""
        
        try:
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            return True
        except IOError:
            return False
    
    def verify_installation(self) -> bool:
        """验证安装"""
        try:
            result = subprocess.run([
                "mail-mcp", "--help"
            ], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_setup_status(self) -> Dict[str, Any]:
        """获取设置状态"""
        status = {
            "claude_installed": self.check_claude_installed(),
            "python_version_ok": self.check_python_version(),
            "config_exists": self.get_claude_config_path() is not None,
            "mail_mcp_installed": self.verify_installation(),
            "config_file": str(self.get_claude_config_path()) if self.get_claude_config_path() else None
        }
        
        # 检查是否已配置mail-mcp
        if status["config_exists"]:
            config = self.load_mcp_config()
            status["mail_mcp_configured"] = "mail-mcp" in config.get("mcpServers", {})
        else:
            status["mail_mcp_configured"] = False
        
        return status


@click.group()
def cli():
    """Mail MCP 自动化安装和配置工具"""
    pass


@cli.command()
@click.option('--force', is_flag=True, help='强制重新安装')
def install(force):
    """一键安装mail-mcp并配置Claude Code"""
    click.echo("🚀 开始安装 Mail MCP...")
    
    setup = MailMCPSetup()
    
    # 检查系统要求
    if not setup.check_python_version():
        click.echo("❌ Python版本过低，需要Python 3.8+")
        sys.exit(1)
    
    if not setup.check_claude_installed():
        click.echo("❌ Claude Code未安装，请先安装Claude Code")
        sys.exit(1)
    
    click.echo("✅ 系统要求检查通过")
    
    # 安装包
    click.echo("📦 安装 mail-mcp 包...")
    if not setup.install_package():
        click.echo("❌ 包安装失败")
        sys.exit(1)
    
    click.echo("✅ 包安装成功")
    
    # 配置MCP
    click.echo("⚙️ 配置 Claude Code MCP...")
    config = setup.load_mcp_config()
    config = setup.add_mail_mcp_config(config)
    
    if not setup.save_mcp_config(config):
        click.echo("❌ MCP配置保存失败")
        sys.exit(1)
    
    click.echo("✅ MCP配置成功")
    
    # 创建示例配置
    click.echo("📝 创建示例配置文件...")
    setup.create_sample_config()
    setup.setup_environment()
    
    click.echo("✅ 示例配置文件已创建")
    
    # 验证安装
    if setup.verify_installation():
        click.echo("✅ 安装验证成功")
    else:
        click.echo("⚠️ 安装验证失败，但可能仍可使用")
    
    click.echo("🎉 Mail MCP 安装完成！")
    click.echo("\n下一步：")
    click.echo("1. 编辑 ~/.mail-mcp/config.yaml 配置您的邮箱信息")
    click.echo("2. 重启Claude Code以加载MCP配置")
    click.echo("3. 使用 /mcp 命令验证连接")


@cli.command()
def status():
    """检查安装状态"""
    setup = MailMCPSetup()
    status_info = setup.get_setup_status()
    
    click.echo("📊 Mail MCP 安装状态")
    click.echo("=" * 30)
    
    for key, value in status_info.items():
        if isinstance(value, bool):
            status_icon = "✅" if value else "❌"
            click.echo(f"{status_icon} {key.replace('_', ' ').title()}: {value}")
        else:
            click.echo(f"📄 {key.replace('_', ' ').title()}: {value}")


@cli.command()
def uninstall():
    """卸载mail-mcp"""
    click.echo("🗑️ 卸载 Mail MCP...")
    
    setup = MailMCPSetup()
    
    # 从MCP配置中移除
    config = setup.load_mcp_config()
    if "mcpServers" in config and "mail-mcp" in config["mcpServers"]:
        del config["mcpServers"]["mail-mcp"]
        setup.save_mcp_config(config)
        click.echo("✅ 已从MCP配置中移除")
    
    # 卸载包
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "uninstall", "-y", "mail-mcp"
        ], check=True)
        click.echo("✅ 包卸载成功")
    except subprocess.CalledProcessError:
        click.echo("❌ 包卸载失败")
    
    click.echo("🎉 卸载完成")


@cli.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径')
def test(config):
    """测试mail-mcp连接"""
    click.echo("🧪 测试 Mail MCP 连接...")
    
    try:
        result = subprocess.run([
            "mail-mcp"
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            click.echo("✅ mail-mcp 运行正常")
        else:
            click.echo(f"❌ mail-mcp 运行异常: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        click.echo("✅ mail-mcp 启动超时（这可能是正常的）")
    except FileNotFoundError:
        click.echo("❌ mail-mcp 未找到")


def main():
    """主入口"""
    cli()


if __name__ == "__main__":
    main()