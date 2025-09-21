"""
测试IMAP服务
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import imaplib
import socket
import ssl
import email
from email import policy

from mail_mcp.config import Config
from mail_mcp.imap_service import IMAPService


class TestIMAPService:
    """测试IMAP服务"""
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=Config)
        config.imap = Mock()
        config.imap.host = "imap.test.com"
        config.imap.port = 993
        config.imap.username = "test@test.com"
        config.imap.password = "test_password"
        config.imap.use_ssl = True
        return config
    
    @pytest.fixture
    def imap_service(self, mock_config):
        """创建IMAP服务实例"""
        return IMAPService(mock_config)
    
    @pytest.mark.asyncio
    async def test_imap_service_initialization(self, imap_service, mock_config):
        """测试IMAP服务初始化"""
        assert imap_service.config == mock_config
        assert imap_service.connection is None
        assert imap_service.connected is False
        assert imap_service.max_retries == 3
        assert imap_service.connection_timeout == 30
        assert imap_service.connection_stats['total_connections'] == 0
    
    @pytest.mark.asyncio
    async def test_connect_ssl_success(self, imap_service):
        """测试SSL连接成功"""
        with patch('imaplib.IMAP4_SSL') as mock_ssl:
            # 模拟连接对象
            mock_connection = Mock()
            mock_connection.noop.return_value = None
            mock_ssl.return_value = mock_connection
            
            # 模拟认证成功
            with patch.object(imap_service, '_authenticate', return_value=True):
                result = await imap_service.connect()
                
                assert result is True
                assert imap_service.connected is True
                assert imap_service.connection == mock_connection
                assert imap_service.connection_stats['successful_connections'] == 1
                # 验证调用参数，但不比较SSLContext对象（每次创建都是新的）
                call_args = mock_ssl.call_args
                assert call_args[0][0] == "imap.test.com"
                assert call_args[0][1] == 993
                assert call_args[1]['timeout'] == 30
                assert 'ssl_context' in call_args[1]
                assert isinstance(call_args[1]['ssl_context'], ssl.SSLContext)
    
    @pytest.mark.asyncio
    async def test_connect_non_ssl_success(self, imap_service):
        """测试非SSL连接成功"""
        imap_service.config.imap.use_ssl = False
        
        with patch('imaplib.IMAP4') as mock_imap:
            mock_connection = Mock()
            mock_connection.noop.return_value = None
            mock_connection.starttls.return_value = None
            mock_imap.return_value = mock_connection
            
            with patch.object(imap_service, '_authenticate', return_value=True):
                result = await imap_service.connect()
                
                assert result is True
                # 验证调用参数
                call_args = mock_imap.call_args
                assert call_args[0][0] == "imap.test.com"
                assert call_args[0][1] == 993
                assert call_args[1]['timeout'] == 30
    
    @pytest.mark.asyncio
    async def test_connect_authentication_failure(self, imap_service):
        """测试认证失败"""
        with patch('imaplib.IMAP4_SSL') as mock_ssl:
            mock_connection = Mock()
            mock_connection.noop.return_value = None
            mock_ssl.return_value = mock_connection
            
            with patch.object(imap_service, '_authenticate', return_value=False):
                result = await imap_service.connect()
                
                assert result is False
                assert imap_service.connected is False
                assert imap_service.connection_stats['failed_connections'] == 1
    
    @pytest.mark.asyncio
    async def test_connect_retry_mechanism(self, imap_service):
        """测试重试机制"""
        with patch('imaplib.IMAP4_SSL') as mock_ssl:
            mock_connection = Mock()
            mock_ssl.return_value = mock_connection
            
            # 前两次认证失败，第三次成功
            with patch.object(imap_service, '_authenticate') as mock_auth:
                mock_auth.side_effect = [False, False, True]
                
                with patch('asyncio.sleep') as mock_sleep:
                    result = await imap_service.connect()
                    
                    assert result is True
                    assert mock_auth.call_count == 3
                    assert mock_sleep.call_count == 2  # 等待了2次
    
    @pytest.mark.asyncio
    async def test_connect_socket_timeout(self, imap_service):
        """测试连接超时"""
        with patch('imaplib.IMAP4_SSL') as mock_ssl:
            mock_ssl.side_effect = socket.timeout("Connection timeout")
            
            result = await imap_service.connect()
            
            assert result is False
            assert imap_service.connection_stats['failed_connections'] == 1
            assert "连接超时" in imap_service.connection_stats['last_error']
    
    @pytest.mark.asyncio
    async def test_connect_dns_error(self, imap_service):
        """测试DNS错误"""
        with patch('imaplib.IMAP4_SSL') as mock_ssl:
            mock_ssl.side_effect = socket.gaierror("Name resolution failed")
            
            result = await imap_service.connect()
            
            assert result is False
            assert "DNS解析失败" in imap_service.connection_stats['last_error']
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, imap_service):
        """测试认证成功"""
        mock_connection = Mock()
        imap_service.connection = mock_connection
        
        result = await imap_service._authenticate()
        
        assert result is True
        mock_connection.login.assert_called_once_with("test@test.com", "test_password")
    
    @pytest.mark.asyncio
    async def test_authenticate_failure_wrong_credentials(self, imap_service):
        """测试认证失败（错误凭据）"""
        mock_connection = Mock()
        mock_connection.login.side_effect = imaplib.IMAP4.error("Authentication failed")
        imap_service.connection = mock_connection
        
        result = await imap_service._authenticate()
        
        assert result is False
        assert "认证失败：用户名或密码错误" in imap_service.connection_stats['last_error']
    
    @pytest.mark.asyncio
    async def test_authenticate_imap_error(self, imap_service):
        """测试IMAP协议错误"""
        mock_connection = Mock()
        mock_connection.login.side_effect = imaplib.IMAP4.error("Server error")
        imap_service.connection = mock_connection
        
        result = await imap_service._authenticate()
        
        assert result is False
        assert "IMAP认证错误" in imap_service.connection_stats['last_error']
    
    @pytest.mark.asyncio
    async def test_disconnect(self, imap_service):
        """测试断开连接"""
        mock_connection = Mock()
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        await imap_service.disconnect()
        
        assert imap_service.connected is False
        assert imap_service.connection is None
        mock_connection.close.assert_called_once()
        mock_connection.logout.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_with_exception(self, imap_service):
        """测试断开连接时的异常处理"""
        mock_connection = Mock()
        mock_connection.close.side_effect = Exception("Disconnect error")
        mock_connection.logout.side_effect = Exception("Logout error")
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        # 应该不抛出异常
        await imap_service.disconnect()
        
        assert imap_service.connected is False
        assert imap_service.connection is None
    
    def test_is_connected_true(self, imap_service):
        """测试连接检查（已连接）"""
        mock_connection = Mock()
        mock_connection.noop.return_value = None
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        result = imap_service.is_connected()
        
        assert result is True
    
    def test_is_connected_false(self, imap_service):
        """测试连接检查（未连接）"""
        imap_service.connection = None
        imap_service.connected = False
        
        result = imap_service.is_connected()
        
        assert result is False
    
    def test_is_connection_dead(self, imap_service):
        """测试检查死连接"""
        mock_connection = Mock()
        mock_connection.noop.side_effect = Exception("Connection dead")
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        result = imap_service.is_connected()
        
        assert result is False
        assert imap_service.connected is False
    
    def test_get_connection_stats(self, imap_service):
        """测试获取连接统计"""
        imap_service.connection_stats = {
            'total_connections': 5,
            'successful_connections': 3,
            'failed_connections': 2,
            'last_error': 'Test error'
        }
        imap_service.connected = True
        
        stats = imap_service.get_connection_stats()
        
        assert stats['total_connections'] == 5
        assert stats['successful_connections'] == 3
        assert stats['failed_connections'] == 2
        assert stats['connected'] is True
        assert stats['success_rate'] == 60.0
        assert 'last_connection_attempt' in stats
    
    @pytest.mark.asyncio
    async def test_test_connection_already_connected(self, imap_service):
        """测试连接测试（已连接）"""
        mock_connection = Mock()
        mock_connection.noop.return_value = None
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        result = await imap_service.test_connection()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_not_connected(self, imap_service):
        """测试连接测试（未连接）"""
        with patch.object(imap_service, 'connect', return_value=True) as mock_connect:
            result = await imap_service.test_connection()
            
            assert result is True
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_connection_connected(self, imap_service):
        """测试确保连接（已连接）"""
        mock_connection = Mock()
        mock_connection.noop.return_value = None
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        result = await imap_service.ensure_connection()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_ensure_connection_not_connected(self, imap_service):
        """测试确保连接（未连接）"""
        with patch.object(imap_service, 'connect', return_value=True) as mock_connect:
            with patch.object(imap_service, '_cleanup_connection') as mock_cleanup:
                result = await imap_service.ensure_connection()
                
                assert result is True
                mock_cleanup.assert_called_once()
                mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_with_connection(self, imap_service):
        """测试重新认证（有连接）"""
        mock_connection = Mock()
        imap_service.connection = mock_connection
        
        with patch.object(imap_service, '_authenticate', return_value=True) as mock_auth:
            result = await imap_service.authenticate()
            
            assert result is True
            mock_auth.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_without_connection(self, imap_service):
        """测试重新认证（无连接）"""
        imap_service.connection = None
        
        with patch.object(imap_service, 'connect', return_value=True) as mock_connect:
            result = await imap_service.authenticate()
            
            assert result is True
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_lock(self, imap_service):
        """测试连接锁机制"""
        call_count = 0
        is_connected_value = False
        
        async def mock_connect_with_retry():
            nonlocal call_count, is_connected_value
            call_count += 1
            # 模拟连接时间
            await asyncio.sleep(0.1)
            is_connected_value = True
            imap_service.connected = True
            return True
        
        def mock_is_connected():
            return is_connected_value
        
        with patch.object(imap_service, '_connect_with_retry', side_effect=mock_connect_with_retry):
            with patch.object(imap_service, 'is_connected', side_effect=mock_is_connected):
                # 并发调用连接
                tasks = [imap_service.connect() for _ in range(3)]
                results = await asyncio.gather(*tasks)
                
                assert all(results)
                # 第一次连接后，后续的连接应该直接返回True而不调用_connect_with_retry
                assert call_count == 1, f"Expected 1 call, got {call_count}"

    @pytest.mark.asyncio
    async def test_get_message_attachments_with_attachments(self, imap_service):
        """测试获取包含附件的邮件附件列表"""
        # 创建一个包含附件的模拟邮件
        mock_email = """Subject: Test Email with Attachments
From: test@example.com
To: recipient@example.com
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain

This is a test email with attachments.

--boundary123
Content-Type: application/pdf
Content-Disposition: attachment; filename="test.pdf"

PDF content here
--boundary123
Content-Type: image/jpeg
Content-Disposition: attachment; filename="image.jpg"

JPEG content here
--boundary123--
"""
        
        mock_connection = Mock()
        mock_connection.select.return_value = ('OK', [])
        mock_connection.fetch.return_value = ('OK', [(None, mock_email.encode())])
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            attachments = await imap_service.get_message_attachments("123")
            
            assert len(attachments) == 2
            
            # 检查第一个附件
            pdf_attachment = next(att for att in attachments if att['filename'] == 'test.pdf')
            assert pdf_attachment['content_type'] == 'application/pdf'
            assert pdf_attachment['size'] > 0
            assert 'part_id' in pdf_attachment
            
            # 检查第二个附件
            jpg_attachment = next(att for att in attachments if att['filename'] == 'image.jpg')
            assert jpg_attachment['content_type'] == 'image/jpeg'
            assert jpg_attachment['size'] > 0
            assert 'part_id' in jpg_attachment

    @pytest.mark.asyncio
    async def test_get_message_attachments_no_attachments(self, imap_service):
        """测试获取不含附件的邮件附件列表"""
        # 创建一个不含附件的模拟邮件
        mock_email = """Subject: Test Email without Attachments
From: test@example.com
To: recipient@example.com
MIME-Version: 1.0
Content-Type: text/plain

This is a test email without attachments.
"""
        
        mock_connection = Mock()
        mock_connection.select.return_value = ('OK', [])
        mock_connection.fetch.return_value = ('OK', [(None, mock_email.encode())])
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            attachments = await imap_service.get_message_attachments("123")
            
            assert len(attachments) == 0

    @pytest.mark.asyncio
    async def test_get_message_attachments_folder_selection_failed(self, imap_service):
        """测试获取附件时文件夹选择失败"""
        with patch.object(imap_service, 'select_folder', return_value=False):
            attachments = await imap_service.get_message_attachments("123")
            
            assert attachments == []

    @pytest.mark.asyncio
    async def test_get_message_attachments_fetch_failed(self, imap_service):
        """测试获取附件时fetch失败"""
        mock_connection = Mock()
        mock_connection.fetch.return_value = ('NO', [])
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            attachments = await imap_service.get_message_attachments("123")
            
            assert attachments == []

    @pytest.mark.asyncio
    async def test_download_attachment_payload_success(self, imap_service):
        """测试成功下载附件内容"""
        # 创建包含附件的模拟邮件
        mock_email = """Subject: Test Email with Attachments
From: test@example.com
To: recipient@example.com
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain

This is a test email with attachments.

--boundary123
Content-Type: application/pdf
Content-Disposition: attachment; filename="test.pdf"
Content-Transfer-Encoding: base64

UERGIGNvbnRlbnQgaGVyZQ==
--boundary123--
"""
        
        mock_connection = Mock()
        mock_connection.select.return_value = ('OK', [])
        mock_connection.fetch.return_value = ('OK', [(None, mock_email.encode())])
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            payload = await imap_service.download_attachment_payload("123", "test.pdf")
            
            assert payload is not None
            assert isinstance(payload, bytes)
            # 解码base64后的内容应该是 "PDF content here"
            assert b"PDF content here" == payload

    @pytest.mark.asyncio
    async def test_download_attachment_payload_file_not_found(self, imap_service):
        """测试下载不存在的附件"""
        # 创建包含不同附件的模拟邮件
        mock_email = """Subject: Test Email with Attachments
From: test@example.com
To: recipient@example.com
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain

This is a test email with attachments.

--boundary123
Content-Type: application/pdf
Content-Disposition: attachment; filename="different.pdf"

PDF content here
--boundary123--
"""
        
        mock_connection = Mock()
        mock_connection.select.return_value = ('OK', [])
        mock_connection.fetch.return_value = ('OK', [(None, mock_email.encode())])
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            payload = await imap_service.download_attachment_payload("123", "test.pdf")
            
            assert payload is None

    @pytest.mark.asyncio
    async def test_download_attachment_payload_folder_selection_failed(self, imap_service):
        """测试下载附件时文件夹选择失败"""
        with patch.object(imap_service, 'select_folder', return_value=False):
            payload = await imap_service.download_attachment_payload("123", "test.pdf")
            
            assert payload is None

    @pytest.mark.asyncio
    async def test_download_attachment_payload_exception_handling(self, imap_service):
        """测试下载附件时的异常处理"""
        mock_connection = Mock()
        mock_connection.fetch.side_effect = Exception("Network error")
        imap_service.connection = mock_connection
        imap_service.connected = True
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            payload = await imap_service.download_attachment_payload("123", "test.pdf")
            
            assert payload is None