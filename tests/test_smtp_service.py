"""
SMTP service tests for Mail MCP server
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import smtplib
import socket
from email.mime.text import MIMEText

from mail_mcp.config import Config
from mail_mcp.smtp_service import SMTPService
from mail_mcp.models import EmailMessage, EmailAttachment


class TestSMTPService:
    """Test SMTP service functionality"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = Mock(spec=Config)
        config.smtp = Mock()
        config.imap = Mock()
        return config
    
    @pytest.fixture
    def smtp_service(self, mock_config):
        """Create SMTP service instance"""
        return SMTPService(mock_config)
    
    def test_smtp_service_initialization(self, smtp_service, mock_config):
        """Test SMTP service initialization"""
        assert smtp_service.config == mock_config
        assert smtp_service.connection is None
        assert smtp_service.connected is False
        assert smtp_service.connection_timeout == 30
        assert smtp_service.connection_stats['total_connections'] == 0
    
    @pytest.mark.asyncio
    async def test_connect_ssl_success(self, smtp_service, mock_config):
        """Test successful SSL connection"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'test@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock SMTP_SSL
        with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
            mock_connection = Mock()
            mock_smtp_ssl.return_value = mock_connection
            mock_connection.noop.return_value = None
            
            result = await smtp_service.connect()
            
            assert result is True
            assert smtp_service.connected is True
            assert smtp_service.connection_stats['successful_connections'] == 1
            mock_smtp_ssl.assert_called_once()
            mock_connection.login.assert_called_once_with('test@gmail.com', 'password')
            mock_connection.noop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_starttls_success(self, smtp_service, mock_config):
        """Test successful STARTTLS connection"""
        # Mock config
        mock_config.smtp.use_ssl = False
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 587
        mock_config.smtp.username = 'test@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock SMTP
        with patch('smtplib.SMTP') as mock_smtp:
            mock_connection = Mock()
            mock_smtp.return_value = mock_connection
            mock_connection.noop.return_value = None
            
            result = await smtp_service.connect()
            
            assert result is True
            assert smtp_service.connected is True
            mock_smtp.assert_called_once()
            mock_connection.ehlo.assert_called()
            mock_connection.starttls.assert_called_once()
            mock_connection.login.assert_called_once_with('test@gmail.com', 'password')
            mock_connection.noop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_authentication_failure(self, smtp_service, mock_config):
        """Test authentication failure"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'test@gmail.com'
        mock_config.smtp.password = 'wrong_password'
        
        # Mock SMTP_SSL with auth failure
        with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
            mock_connection = Mock()
            mock_smtp_ssl.return_value = mock_connection
            mock_connection.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Authentication failed')
            
            result = await smtp_service.connect()
            
            assert result is False
            assert smtp_service.connected is False
            assert smtp_service.connection_stats['failed_connections'] == 1
            assert 'Authentication failed' in smtp_service.connection_stats['last_error']
    
    @pytest.mark.asyncio
    async def test_connect_timeout(self, smtp_service, mock_config):
        """Test connection timeout"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'test@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock SMTP_SSL with timeout
        with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
            mock_smtp_ssl.side_effect = socket.timeout("Connection timed out")
            
            result = await smtp_service.connect()
            
            assert result is False
            assert smtp_service.connected is False
            assert smtp_service.connection_stats['failed_connections'] == 1
            assert 'Connection timeout' in smtp_service.connection_stats['last_error']
    
    @pytest.mark.asyncio
    async def test_connect_dns_failure(self, smtp_service, mock_config):
        """Test DNS resolution failure"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'nonexistent.domain.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'test@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock SMTP_SSL with DNS error
        with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
            mock_smtp_ssl.side_effect = socket.gaierror("Name resolution failed")
            
            result = await smtp_service.connect()
            
            assert result is False
            assert smtp_service.connected is False
            assert 'DNS resolution failed' in smtp_service.connection_stats['last_error']
    
    @pytest.mark.asyncio
    async def test_disconnect(self, smtp_service, mock_config):
        """Test disconnect functionality"""
        # Set up mock connection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        
        await smtp_service.disconnect()
        
        assert smtp_service.connected is False
        assert smtp_service.connection is None
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, smtp_service, mock_config):
        """Test successful email sending"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'sender@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock connection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        
        result = await smtp_service.send_email(
            to='recipient@example.com',
            subject='Test Subject',
            body='Test Body'
        )
        
        assert result is True
        smtp_service.connection.sendmail.assert_called_once()
        
        # Check call arguments
        call_args = smtp_service.connection.sendmail.call_args
        assert call_args[0][0] == 'sender@gmail.com'  # from
        assert 'recipient@example.com' in call_args[0][1]  # to
    
    @pytest.mark.asyncio
    async def test_send_email_invalid_address(self, smtp_service):
        """Test sending email with invalid address"""
        result = await smtp_service.send_email(
            to='invalid-email',
            subject='Test Subject',
            body='Test Body'
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_email_reconnect(self, smtp_service, mock_config):
        """Test email sending with reconnection"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'sender@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock connect and connection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        
        with patch.object(smtp_service, 'connect', return_value=True) as mock_connect:
            smtp_service.connected = False  # Force reconnection
            
            result = await smtp_service.send_email(
                to='recipient@example.com',
                subject='Test Subject',
                body='Test Body'
            )
            
            assert result is True
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments(self, smtp_service, mock_config):
        """Test sending email with attachments"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'sender@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock connection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        
        # Create attachment
        attachment = EmailAttachment(
            filename='test.txt',
            content_type='text/plain',
            size=12,
            content=b'Hello World'
        )
        
        result = await smtp_service.send_email(
            to='recipient@example.com',
            subject='Test Subject',
            body='Test Body',
            attachments=[attachment]
        )
        
        assert result is True
        smtp_service.connection.sendmail.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_connection(self, smtp_service, mock_config):
        """Test connection testing"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'test@gmail.com'
        mock_config.smtp.password = 'password'
        
        with patch.object(smtp_service, 'connect', return_value=True) as mock_connect:
            result = await smtp_service.test_connection()
            
            assert result is True
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate(self, smtp_service, mock_config):
        """Test authentication"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'test@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock connection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        
        result = await smtp_service.authenticate()
        
        assert result is True
        smtp_service.connection.login.assert_called_with('test@gmail.com', 'password')
    
    def test_get_connection_stats(self, smtp_service):
        """Test connection statistics"""
        # Set some stats
        smtp_service.connection_stats['total_connections'] = 5
        smtp_service.connection_stats['successful_connections'] = 3
        smtp_service.connected = True
        
        stats = smtp_service.get_connection_stats()
        
        assert stats['total_connections'] == 5
        assert stats['successful_connections'] == 3
        assert stats['connected'] is True
        assert stats['success_rate'] == 60.0
    
    def test_is_connection_healthy(self, smtp_service):
        """Test connection health check"""
        # Mock healthy connection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        smtp_service.connection.noop.return_value = None
        
        result = smtp_service.is_connection_healthy()
        
        assert result is True
        smtp_service.connection.noop.assert_called_once()
    
    def test_is_connection_healthy_failure(self, smtp_service):
        """Test connection health check failure"""
        # Mock unhealthy connection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        smtp_service.connection.noop.side_effect = Exception("Connection lost")
        
        result = smtp_service.is_connection_healthy()
        
        assert result is False
        assert smtp_service.connected is False
    
    @pytest.mark.asyncio
    async def test_ensure_connection_healthy(self, smtp_service):
        """Test ensure connection with healthy connection"""
        # Mock healthy connection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        smtp_service.connection.noop.return_value = None
        
        result = await smtp_service.ensure_connection()
        
        assert result is True
        smtp_service.connection.noop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_connection_reconnect(self, smtp_service, mock_config):
        """Test ensure connection with reconnection"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'test@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock unhealthy connection that needs reconnection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        smtp_service.connection.noop.side_effect = Exception("Connection lost")
        
        with patch.object(smtp_service, 'connect', return_value=True) as mock_connect:
            result = await smtp_service.ensure_connection()
            
            assert result is True
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_message(self, smtp_service, mock_config):
        """Test sending EmailMessage object"""
        # Mock config
        mock_config.smtp.use_ssl = True
        mock_config.smtp.host = 'smtp.gmail.com'
        mock_config.smtp.port = 465
        mock_config.smtp.username = 'sender@gmail.com'
        mock_config.smtp.password = 'password'
        
        # Mock connection
        smtp_service.connection = Mock()
        smtp_service.connected = True
        
        # Create message
        message = EmailMessage(
            id="1",
            subject="Test Subject",
            from_address="sender@gmail.com",
            to_addresses=["recipient@example.com"],
            cc_addresses=["cc@example.com"],
            date="2024-01-01",
            body_text="Test Body",
            body_html=None,
            attachments=[],
            is_read=False
        )
        
        result = await smtp_service.send_email_message(message)
        
        assert result is True
        smtp_service.connection.sendmail.assert_called_once()
        
        # Check that CC addresses are included
        call_args = smtp_service.connection.sendmail.call_args
        recipients = call_args[0][1]
        assert "recipient@example.com" in recipients
        assert "cc@example.com" in recipients