"""
Configuration management for Mail MCP server
"""

import os
import re
from dataclasses import dataclass
from typing import List, Dict, Any
from dotenv import load_dotenv

from .errors import ConfigurationError

load_dotenv()


def validate_email_address(email: str) -> bool:
    """验证邮箱地址格式是否正确"""
    if not email or not isinstance(email, str):
        return False
    
    # 基本邮箱格式验证
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email.strip()))


@dataclass
class IMAPConfig:
    """IMAP server configuration"""
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True

    @classmethod
    def from_env(cls) -> 'IMAPConfig':
        """Create IMAP config from environment variables"""
        try:
            return cls(
                host=os.getenv('IMAP_HOST', ''),
                port=int(os.getenv('IMAP_PORT', '993')),
                username=os.getenv('IMAP_USERNAME', ''),
                password=os.getenv('IMAP_PASSWORD', ''),
                use_ssl=os.getenv('IMAP_USE_SSL', 'true').lower() == 'true'
            )
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid IMAP port value: {e}",
                details={"env_var": "IMAP_PORT", "error": str(e)},
                original_exception=e
            )

    def validate(self) -> List[str]:
        """Validate IMAP configuration and return list of errors"""
        errors = []

        if not self.host:
            errors.append("IMAP host is required")
        elif not self._is_valid_host(self.host):
            errors.append("IMAP host is invalid")

        if not self.username:
            errors.append("IMAP username is required")

        if not self.password:
            errors.append("IMAP password is required")

        if not self._is_valid_port(self.port):
            errors.append(f"IMAP port {self.port} is invalid")

        return errors

    def _is_valid_host(self, host: str) -> bool:
        """Validate host format"""
        host_pattern = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(host_pattern, host))

    def _is_valid_port(self, port: int) -> bool:
        """Validate port number"""
        return 1 <= port <= 65535


@dataclass
class SMTPConfig:
    """SMTP server configuration"""
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True

    @classmethod
    def from_env(cls) -> 'SMTPConfig':
        """Create SMTP config from environment variables"""
        try:
            return cls(
                host=os.getenv('SMTP_HOST', ''),
                port=int(os.getenv('SMTP_PORT', '587')),
                username=os.getenv('SMTP_USERNAME', ''),
                password=os.getenv('SMTP_PASSWORD', ''),
                use_ssl=os.getenv('SMTP_USE_SSL', 'true').lower() == 'true'
            )
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid SMTP port value: {e}",
                details={"env_var": "SMTP_PORT", "error": str(e)},
                original_exception=e
            )

    def validate(self) -> List[str]:
        """Validate SMTP configuration and return list of errors"""
        errors = []

        if not self.host:
            errors.append("SMTP host is required")
        elif not self._is_valid_host(self.host):
            errors.append("SMTP host is invalid")

        if not self.username:
            errors.append("SMTP username is required")

        if not self.password:
            errors.append("SMTP password is required")

        if not self._is_valid_port(self.port):
            errors.append(f"SMTP port {self.port} is invalid")

        return errors

    def _is_valid_host(self, host: str) -> bool:
        """Validate host format"""
        host_pattern = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(host_pattern, host))

    def _is_valid_port(self, port: int) -> bool:
        """Validate port number"""
        return 1 <= port <= 65535


@dataclass
class TrustedSendersConfig:
    """可信发件人配置"""
    senders: List[str]
    
    @classmethod
    def from_env(cls) -> 'TrustedSendersConfig':
        """从环境变量创建可信发件人配置"""
        trusted_str = os.getenv('TRUSTED_SENDERS', '')
        senders = [s.strip() for s in trusted_str.split(',') if s.strip()]
        return cls(senders=senders)
    
    def validate(self) -> List[str]:
        """验证可信发件人配置并返回错误列表"""
        errors = []
        
        if not self.senders:
            errors.append('至少需要配置一个可信发件人')
        
        for sender in self.senders:
            if not validate_email_address(sender):
                errors.append(f'无效的邮箱地址: {sender}')
        
        return errors
    
    def is_trusted_sender(self, sender_email: str) -> bool:
        """检查发件人是否在可信列表中"""
        if not sender_email:
            return False
        
        sender_email = sender_email.strip().lower()
        return any(trusted.strip().lower() == sender_email for trusted in self.senders)


@dataclass
class Config:
    """Main configuration class"""
    imap: IMAPConfig
    smtp: SMTPConfig
    trusted_senders: TrustedSendersConfig
    host: str = "localhost"
    port: int = 8000
    log_level: str = "INFO"
    is_valid: bool = True
    errors: Dict[str, List[str]] = None

    def __init__(self):
        self.imap = IMAPConfig.from_env()
        self.smtp = SMTPConfig.from_env()
        self.trusted_senders = TrustedSendersConfig.from_env()
        self.host = os.getenv('HOST', 'localhost')
        self.port = int(os.getenv('PORT', '8000'))
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.errors = {}
        self._validate_config()

    def _validate_config(self):
        """Validate configuration"""
        self.errors = {}
        
        # Validate IMAP config
        imap_errors = self.imap.validate()
        if imap_errors:
            self.errors['imap'] = imap_errors
        
        # Validate SMTP config
        smtp_errors = self.smtp.validate()
        if smtp_errors:
            self.errors['smtp'] = smtp_errors
        
        # Validate trusted senders config
        trusted_errors = self.trusted_senders.validate()
        if trusted_errors:
            self.errors['trusted_senders'] = trusted_errors
        
        self.is_valid = len(self.errors) == 0

    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all configuration and return errors"""
        errors = {
            'imap': self.imap.validate(),
            'smtp': self.smtp.validate(),
            'trusted_senders': self.trusted_senders.validate()
        }

        # Validate server config
        if not self._is_valid_host(self.host):
            errors['server'] = [f"Invalid server host: {self.host}"]

        if not self._is_valid_port(self.port):
            errors['server'] = errors.get('server', []) + [f"Invalid server port: {self.port}"]

        return errors

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary (without sensitive data)"""
        return {
            'imap': {
                'host': self.imap.host,
                'port': self.imap.port,
                'username': self.imap.username,
                'use_ssl': self.imap.use_ssl
            },
            'smtp': {
                'host': self.smtp.host,
                'port': self.smtp.port,
                'username': self.smtp.username,
                'use_ssl': self.smtp.use_ssl
            },
            'trusted_senders': {
                'count': len(self.trusted_senders.senders),
                'senders': self.trusted_senders.senders
            },
            'server': {
                'host': self.host,
                'port': self.port,
                'log_level': self.log_level
            }
        }

    def _is_valid_host(self, host: str) -> bool:
        """Validate host format"""
        if host in ['localhost', '127.0.0.1']:
            return True
        host_pattern = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(host_pattern, host))

    def _is_valid_port(self, port: int) -> bool:
        """Validate port number"""
        return 1 <= port <= 65535
