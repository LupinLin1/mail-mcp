"""
Configuration tests for Mail MCP server
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from mail_mcp.config import Config, IMAPConfig, SMTPConfig
from mail_mcp.errors import ConfigurationError


class TestIMAPConfig:
    """Test IMAP configuration"""
    
    def test_from_env_success(self):
        """Test successful IMAP config creation from environment"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_PORT': '993',
            'IMAP_USER': 'test@gmail.com',
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
            'IMAP_USER': 'test@gmail.com',
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
            'SMTP_USER': 'test@gmail.com',
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
            'IMAP_USER': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USER': 'test@gmail.com',
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
            with pytest.raises(ConfigurationError, match="IMAP configuration errors"):
                Config()
    
    def test_config_validation_all(self):
        """Test comprehensive config validation"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_PORT': '993',
            'IMAP_USER': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USER': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123',
            'HOST': 'invalid-host',
            'PORT': '99999'
        }
        
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
            'IMAP_USER': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USER': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            assert config.is_valid() is True
    
    def test_get_config_summary(self):
        """Test configuration summary without sensitive data"""
        env_vars = {
            'IMAP_HOST': 'imap.gmail.com',
            'IMAP_PORT': '993',
            'IMAP_USER': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USER': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123'
        }
        
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
            'IMAP_USER': 'test@gmail.com',
            'IMAP_PASSWORD': 'password123',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USER': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123',
            'HOST': 'localhost'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            errors = config.validate_all()
            
            assert 'server' not in errors or len(errors['server']) == 0