"""
Mail MCP Configuration Tool - 配置管理工具
"""

import sys
import yaml
import click
from pathlib import Path
from typing import Optional, Dict, Any


class MailMCPConfigTool:
    """Mail MCP 配置管理工具"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".mail-mcp"
        self.config_file = self.config_dir / "config.yaml"
        self.env_file = self.config_dir / ".env"
    
    def create_config(self, force: bool = False) -> bool:
        """创建配置文件"""
        if self.config_file.exists() and not force:
            click.echo(f"配置文件已存在: {self.config_file}")
            click.echo("使用 --force 强制重新创建")
            return False
        
        self.config_dir.mkdir(exist_ok=True)
        
        # 交互式配置
        click.echo("📧 Mail MCP 配置向导")
        click.echo("=" * 30)
        
        config = {
            "imap": self._configure_imap(),
            "smtp": self._configure_smtp(),
            "server": self._configure_server()
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            click.echo(f"✅ 配置文件已保存: {self.config_file}")
            return True
        except IOError as e:
            click.echo(f"❌ 配置文件保存失败: {e}")
            return False
    
    def _configure_imap(self) -> Dict[str, Any]:
        """配置IMAP设置"""
        click.echo("\n📥 IMAP 配置")
        
        providers = {
            "1": {"host": "imap.gmail.com", "port": 993, "ssl": True},
            "2": {"host": "imap.outlook.com", "port": 993, "ssl": True},
            "3": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True},
            "4": {"host": "imap.qq.com", "port": 993, "ssl": True},
            "5": {"host": "custom", "port": 993, "ssl": True}
        }
        
        click.echo("选择邮箱提供商:")
        for key, provider in providers.items():
            if key == "5":
                click.echo(f"{key}. 自定义")
            else:
                click.echo(f"{key}. {provider['host']}")
        
        choice = click.prompt("请选择", type=click.Choice(['1', '2', '3', '4', '5']))
        
        if choice == "5":
            host = click.prompt("IMAP服务器地址")
            port = click.prompt("IMAP端口", default=993, type=int)
            use_ssl = click.confirm("使用SSL?", default=True)
        else:
            provider = providers[choice]
            host = provider['host']
            port = provider['port']
            use_ssl = provider['ssl']
        
        username = click.prompt("邮箱用户名")
        password = click.prompt("邮箱密码/应用密码", hide_input=True)
        
        return {
            "host": host,
            "port": port,
            "use_ssl": use_ssl,
            "username": username,
            "password": password
        }
    
    def _configure_smtp(self) -> Dict[str, Any]:
        """配置SMTP设置"""
        click.echo("\n📤 SMTP 配置")
        
        providers = {
            "1": {"host": "smtp.gmail.com", "port": 587, "ssl": True},
            "2": {"host": "smtp-mail.outlook.com", "port": 587, "ssl": True},
            "3": {"host": "smtp.mail.yahoo.com", "port": 587, "ssl": True},
            "4": {"host": "smtp.qq.com", "port": 587, "ssl": True},
            "5": {"host": "custom", "port": 587, "ssl": True}
        }
        
        click.echo("选择邮箱提供商:")
        for key, provider in providers.items():
            if key == "5":
                click.echo(f"{key}. 自定义")
            else:
                click.echo(f"{key}. {provider['host']}")
        
        choice = click.prompt("请选择", type=click.Choice(['1', '2', '3', '4', '5']))
        
        if choice == "5":
            host = click.prompt("SMTP服务器地址")
            port = click.prompt("SMTP端口", default=587, type=int)
            use_ssl = click.confirm("使用SSL?", default=True)
        else:
            provider = providers[choice]
            host = provider['host']
            port = provider['port']
            use_ssl = provider['ssl']
        
        username = click.prompt("邮箱用户名")
        password = click.prompt("邮箱密码/应用密码", hide_input=True)
        
        return {
            "host": host,
            "port": port,
            "use_ssl": use_ssl,
            "username": username,
            "password": password
        }
    
    def _configure_server(self) -> Dict[str, Any]:
        """配置服务器设置"""
        click.echo("\n🖥️ 服务器配置")
        
        host = click.prompt("服务器主机", default="localhost")
        port = click.prompt("服务器端口", default=8000, type=int)
        log_level = click.prompt(
            "日志级别", 
            default="INFO",
            type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        )
        
        return {
            "host": host,
            "port": port,
            "log_level": log_level
        }
    
    def show_config(self) -> Optional[Dict[str, Any]]:
        """显示当前配置"""
        if not self.config_file.exists():
            click.echo("❌ 配置文件不存在")
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            click.echo("📋 当前配置:")
            click.echo("=" * 30)
            
            # 隐藏敏感信息
            safe_config = {
                "imap": {
                    **config.get("imap", {}),
                    "password": "***"
                },
                "smtp": {
                    **config.get("smtp", {}),
                    "password": "***"
                },
                "server": config.get("server", {})
            }
            
            click.echo(yaml.dump(safe_config, default_flow_style=False, allow_unicode=True))
            return config
            
        except Exception as e:
            click.echo(f"❌ 读取配置文件失败: {e}")
            return None
    
    def test_config(self) -> bool:
        """测试配置"""
        if not self.config_file.exists():
            click.echo("❌ 配置文件不存在")
            return False
        
        try:
            # 导入并测试配置
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from mail_mcp.config import Config
            
            config = Config(str(self.config_file))
            
            click.echo("🧪 测试配置...")
            
            # 测试IMAP连接
            click.echo("📥 测试 IMAP 连接...")
            imap_ok = config.imap.validate()
            click.echo(f"   IMAP: {'✅ 成功' if imap_ok else '❌ 失败'}")
            
            # 测试SMTP连接
            click.echo("📤 测试 SMTP 连接...")
            smtp_ok = config.smtp.validate()
            click.echo(f"   SMTP: {'✅ 成功' if smtp_ok else '❌ 失败'}")
            
            if imap_ok and smtp_ok:
                click.echo("✅ 配置测试成功")
                return True
            else:
                click.echo("❌ 配置测试失败")
                return False
                
        except Exception as e:
            click.echo(f"❌ 配置测试异常: {e}")
            return False
    
    def create_env_file(self) -> bool:
        """创建.env文件"""
        if not self.config_file.exists():
            click.echo("❌ 请先创建配置文件")
            return False
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            env_content = f"""# Mail MCP Environment Configuration
# 自动生成于 {yaml.safe_dump(config.get('imap', {}))}
# 自动生成于 {yaml.safe_dump(config.get('smtp', {}))}
# 自动生成于 {yaml.safe_dump(config.get('server', {}))}

# IMAP配置
IMAP_HOST={config.get('imap', {}).get('host', '')}
IMAP_PORT={config.get('imap', {}).get('port', '')}
IMAP_USE_SSL={str(config.get('imap', {}).get('use_ssl', '')).lower()}
IMAP_USERNAME={config.get('imap', {}).get('username', '')}
IMAP_PASSWORD={config.get('imap', {}).get('password', '')}

# SMTP配置  
SMTP_HOST={config.get('smtp', {}).get('host', '')}
SMTP_PORT={config.get('smtp', {}).get('port', '')}
SMTP_USE_SSL={str(config.get('smtp', {}).get('use_ssl', '')).lower()}
SMTP_USERNAME={config.get('smtp', {}).get('username', '')}
SMTP_PASSWORD={config.get('smtp', {}).get('password', '')}

# 服务器配置
SERVER_HOST={config.get('server', {}).get('host', '')}
SERVER_PORT={config.get('server', {}).get('port', '')}
LOG_LEVEL={config.get('server', {}).get('log_level', '')}
"""
            
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            click.echo(f"✅ .env文件已创建: {self.env_file}")
            return True
            
        except Exception as e:
            click.echo(f"❌ 创建.env文件失败: {e}")
            return False


@click.group()
def cli():
    """Mail MCP 配置管理工具"""
    pass


@cli.command()
@click.option('--force', is_flag=True, help='强制重新创建配置')
def create(force):
    """创建配置文件"""
    tool = MailMCPConfigTool()
    tool.create_config(force)


@cli.command()
def show():
    """显示当前配置"""
    tool = MailMCPConfigTool()
    tool.show_config()


@cli.command()
def test():
    """测试配置"""
    tool = MailMCPConfigTool()
    tool.test_config()


@cli.command()
def env():
    """生成.env文件"""
    tool = MailMCPConfigTool()
    tool.create_env_file()


@cli.command()
def path():
    """显示配置文件路径"""
    tool = MailMCPConfigTool()
    click.echo(f"配置文件: {tool.config_file}")
    click.echo(f"环境文件: {tool.env_file}")
    click.echo(f"配置目录: {tool.config_dir}")


def main():
    """主入口"""
    cli()


if __name__ == "__main__":
    main()