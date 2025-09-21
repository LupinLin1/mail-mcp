"""
Configuration tests for Mail MCP server
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from mail_mcp.config import Config, IMAPConfig, SMTPConfig, TrustedSendersConfig, validate_email_address
from mail_mcp.errors import ConfigurationError


class TestIMAPConfig:
    """Test IMAP configuration"""
    
    def test_from_env_success(self):
        """Test successful IMAP config creation from environment"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_PORT': '993',
            'IMAP_USERNAME': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'IMAP_USE_SSL': 'true'
        }
        
        with patch.dict(os.environ, env_vars):
            config = IMAPConfig.from_env()
            
            assert config.host == 'imap.gmail.com'
            assert config.port == 993
            assert config.username == 'test@gmail.com'
            assert config.password == 'password123'
            assert config.use_ssl is True
    
    def test_from_env_defaults(self):
        """Test IMAP config with default values"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_USERNAME': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = IMAPConfig.from_env()
            
            assert config.port == 993  # default
            assert config.use_ssl is True  # default
    
    def test_validate_valid_config(self):
        """Test validation of valid IMAP config"""
        config = IMAPConfig(
            host='imap.gmail.com',
            port=993,
            username='test@gmail.com',
            password='password123',
            use_ssl=True
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validate_missing_host(self):
        """Test validation with missing host"""
        config = IMAPConfig(
            host='',
            port=993,
            username='test@gmail.com',
            password='password123',
            use_ssl=True
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert 'IMAP host is required' in errors
    
    def test_validate_invalid_port(self):
        """Test validation with invalid port"""
        config = IMAPConfig(
            host='imap.gmail.com',
            port=99999,
            username='test@gmail.com',
            password='password123',
            use_ssl=True
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert 'IMAP port 99999 is invalid' in errors


class TestSMTPConfig:
    """Test SMTP configuration"""
    
    def test_from_env_success(self):
        """Test successful SMTP config creation from environment"""
        env_vars = {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123',
            'SMTP_USE_SSL': 'true'
        }
        
        with patch.dict(os.environ, env_vars):
            config = SMTPConfig.from_env()
            
            assert config.host == 'smtp.gmail.com'
            assert config.port == 587
            assert config.username == 'test@gmail.com'
            assert config.password == 'password123'
            assert config.use_ssl is True
    
    def test_validate_valid_config(self):
        """Test validation of valid SMTP config"""
        config = SMTPConfig(
            host='smtp.gmail.com',
            port=587,
            username='test@gmail.com',
            password='password123',
            use_ssl=True
        )
        
        errors = config.validate()
        assert len(errors) == 0


class TestConfig:
    """Test main configuration class"""
    
    def test_config_initialization_success(self):
        """Test successful config initialization"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_PORT': '993',
            'IMAP_USERNAME': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123',
            'HOST': 'localhost',
            'PORT': '8000',
            'LOG_LEVEL': 'DEBUG'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            
            assert config.imap.host == 'imap.gmail.com'
            assert config.smtp.host == 'smtp.gmail.com'
            assert config.host == 'localhost'
            assert config.port == 8000
            assert config.log_level == 'DEBUG'
    
    def test_config_missing_required_fields(self):
        """Test config initialization with missing required fields"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            # Missing other required fields
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.is_valid is False
            assert 'imap' in config.errors
            assert 'smtp' in config.errors
            assert 'trusted_senders' in config.errors
    
    def test_config_validation_all(self):
        """Test comprehensive config validation"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_PORT': '993',
            'IMAP_USERNAME': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123',
            'HOST': 'invalid-host',
            'PORT': '99999'
        }
        env_vars['TRUSTED_SENDERS'] = 'test@company.com'
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            errors = config.validate_all()
            
            assert len(errors['server']) > 0
            assert 'Invalid server host: invalid-host' in errors['server']
            assert 'Invalid server port: 99999' in errors['server']
    
    def test_is_valid_method(self):
        """Test is_valid method"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_PORT': '993',
            'IMAP_USERNAME': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123'
        }
        
        env_vars['TRUSTED_SENDERS'] = 'test@company.com'
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            assert config.is_valid is True
    
    def test_get_config_summary(self):
        """Test configuration summary without sensitive data"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_PORT': '993',
            'IMAP_USERNAME': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123'
        }
        env_vars['TRUSTED_SENDERS'] = 'test@company.com'
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            summary = config.get_config_summary()
            
            assert 'password' not in str(summary)
            assert summary['imap']['host'] == 'imap.gmail.com'
            assert summary['smtp']['host'] == 'smtp.gmail.com'
            assert summary['imap']['username'] == 'test@gmail.com'
    
    def test_localhost_validation(self):
        """Test localhost validation"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_PORT': '993',
            'IMAP_USERNAME': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123',
            'HOST': 'localhost'
        }
        env_vars['TRUSTED_SENDERS'] = 'test@company.com'
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            errors = config.validate_all()
            
            assert 'server' not in errors or len(errors['server']) == 0


class TestValidateEmailAddress:
    """Test email address validation function"""
    
    def test_valid_email_addresses(self):
        """Test various valid email address formats"""
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org',
            'user123@test-domain.com',
            'a@b.co'
        ]
        
        for email in valid_emails:
            assert validate_email_address(email) is True, f"Failed for {email}"
    
    def test_invalid_email_addresses(self):
        """Test various invalid email address formats"""
        invalid_emails = [
            '',
            None,
            'invalid-email',
            '@domain.com',
            'user@',
            'user@@domain.com',
            'user@domain',
            'user name@domain.com',
            123,
            []
        ]
        
        for email in invalid_emails:
            assert validate_email_address(email) is False, f"Should be invalid: {email}"


class TestTrustedSendersConfig:
    """Test trusted senders configuration"""
    
    def test_from_env_single_sender(self):
        """Test creating config from environment with single sender"""
        env_vars = {
            'TRUSTED_SENDERS': 'boss@company.com'
        }
        
        with patch.dict(os.environ, env_vars):
            config = TrustedSendersConfig.from_env()
            
            assert len(config.senders) == 1
            assert config.senders[0] == 'boss@company.com'
    
    def test_from_env_multiple_senders(self):
        """Test creating config from environment with multiple senders"""
        env_vars = {
            'TRUSTED_SENDERS': 'boss@company.com,hr@company.com,no-reply@important.com'
        }
        
        with patch.dict(os.environ, env_vars):
            config = TrustedSendersConfig.from_env()
            
            assert len(config.senders) == 3
            assert 'boss@company.com' in config.senders
            assert 'hr@company.com' in config.senders
            assert 'no-reply@important.com' in config.senders
    
    def test_from_env_with_spaces(self):
        """Test creating config with spaces around emails"""
        env_vars = {
            'TRUSTED_SENDERS': ' boss@company.com , hr@company.com  ,  no-reply@important.com '
        }
        
        with patch.dict(os.environ, env_vars):
            config = TrustedSendersConfig.from_env()
            
            assert len(config.senders) == 3
            assert config.senders[0] == 'boss@company.com'
            assert config.senders[1] == 'hr@company.com'
            assert config.senders[2] == 'no-reply@important.com'
    
    def test_from_env_empty(self):
        """Test creating config from empty environment"""
        env_vars = {
            'TRUSTED_SENDERS': ''
        }
        
        with patch.dict(os.environ, env_vars):
            config = TrustedSendersConfig.from_env()
            
            assert len(config.senders) == 0
    
    def test_from_env_missing(self):
        """Test creating config when environment variable is missing"""
        with patch.dict(os.environ, {}, clear=True):
            config = TrustedSendersConfig.from_env()
            
            assert len(config.senders) == 0
    
    def test_validate_success(self):
        """Test successful validation with valid email addresses"""
        config = TrustedSendersConfig(senders=['boss@company.com', 'hr@company.com'])
        
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validate_empty_senders(self):
        """Test validation fails with empty senders list"""
        config = TrustedSendersConfig(senders=[])
        
        errors = config.validate()
        
        assert len(errors) == 1
        assert '至少需要配置一个可信发件人' in errors[0]
    
    def test_validate_invalid_email(self):
        """Test validation fails with invalid email addresses"""
        config = TrustedSendersConfig(senders=['invalid-email', 'boss@company.com', '@domain.com'])
        
        errors = config.validate()
        
        assert len(errors) == 2
        assert any('invalid-email' in error for error in errors)
        assert any('@domain.com' in error for error in errors)
    
    def test_is_trusted_sender_exact_match(self):
        """Test exact match for trusted sender check"""
        config = TrustedSendersConfig(senders=['boss@company.com', 'hr@company.com'])
        
        assert config.is_trusted_sender('boss@company.com') is True
        assert config.is_trusted_sender('hr@company.com') is True
        assert config.is_trusted_sender('other@company.com') is False
    
    def test_is_trusted_sender_case_insensitive(self):
        """Test case insensitive matching for trusted sender check"""
        config = TrustedSendersConfig(senders=['Boss@Company.com', 'HR@COMPANY.COM'])
        
        assert config.is_trusted_sender('boss@company.com') is True
        assert config.is_trusted_sender('BOSS@COMPANY.COM') is True
        assert config.is_trusted_sender('hr@company.com') is True
        assert config.is_trusted_sender('Hr@Company.Com') is True
    
    def test_is_trusted_sender_with_spaces(self):
        """Test trusted sender check handles spaces correctly"""
        config = TrustedSendersConfig(senders=['boss@company.com'])
        
        assert config.is_trusted_sender(' boss@company.com ') is True
        assert config.is_trusted_sender('boss@company.com') is True
    
    def test_is_trusted_sender_empty_input(self):
        """Test trusted sender check with empty/None input"""
        config = TrustedSendersConfig(senders=['boss@company.com'])
        
        assert config.is_trusted_sender('') is False
        assert config.is_trusted_sender(None) is False