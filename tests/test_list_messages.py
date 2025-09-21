"""
测试邮件列表获取功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from mail_mcp.config import Config
from mail_mcp.imap_service import IMAPService
from mail_mcp.models import EmailMessage


class TestListMessages:
    """测试邮件列表获取功能"""
    
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
    
    @pytest.fixture
    def sample_messages(self):
        """创建示例邮件数据"""
        return [
            EmailMessage(
                id="1",
                subject="测试邮件1",
                from_address="sender1@test.com",
                to_addresses=["test@test.com"],
                date="2025-09-20T10:00:00",
                body_text="这是测试邮件1的内容",
                body_html=None,
                attachments=[],
                is_read=False,
                message_id="msg1@test.com",
                folder="INBOX"
            ),
            EmailMessage(
                id="2",
                subject="测试邮件2",
                from_address="sender2@test.com",
                to_addresses=["test@test.com"],
                date="2025-09-20T11:00:00",
                body_text="这是测试邮件2的内容",
                body_html=None,
                attachments=[],
                is_read=True,
                message_id="msg2@test.com",
                folder="INBOX"
            ),
            EmailMessage(
                id="3",
                subject="测试邮件3",
                from_address="sender3@test.com",
                to_addresses=["test@test.com"],
                date="2025-09-20T12:00:00",
                body_text="这是测试邮件3的内容",
                body_html=None,
                attachments=[],
                is_read=False,
                message_id="msg3@test.com",
                folder="INBOX"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_list_messages_success(self, imap_service, sample_messages):
        """测试成功获取邮件列表"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch('imaplib.IMAP4_SSL') as mock_ssl:
                mock_connection = Mock()
                mock_connection.search.return_value = ('OK', [b'1 2 3'])
                mock_ssl.return_value = mock_connection
                imap_service.connection = mock_connection
                imap_service.connected = True
                
                with patch.object(imap_service, '_get_message_by_id') as mock_get:
                    # 设置模拟返回值
                    mock_get.side_effect = sample_messages
                    
                    result = await imap_service.list_messages("INBOX", 3, 0)
                    
                    assert len(result) == 3
                    assert result[0].id == "1"
                    assert result[0].subject == "测试邮件1"
                    assert result[1].id == "2"
                    assert result[1].subject == "测试邮件2"
                    assert result[2].id == "3"
                    assert result[2].subject == "测试邮件3"
    
    @pytest.mark.asyncio
    async def test_list_messages_with_limit(self, imap_service, sample_messages):
        """测试限制邮件数量"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch('imaplib.IMAP4_SSL') as mock_ssl:
                mock_connection = Mock()
                mock_connection.search.return_value = ('OK', [b'1 2 3'])
                mock_ssl.return_value = mock_connection
                imap_service.connection = mock_connection
                imap_service.connected = True
                
                with patch.object(imap_service, '_get_message_by_id') as mock_get:
                    mock_get.side_effect = sample_messages
                    
                    result = await imap_service.list_messages("INBOX", 2, 0)
                    
                    assert len(result) == 2
                    assert result[0].id == "1"
                    assert result[1].id == "2"
    
    @pytest.mark.asyncio
    async def test_list_messages_with_offset(self, imap_service, sample_messages):
        """测试分页偏移"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch('imaplib.IMAP4_SSL') as mock_ssl:
                mock_connection = Mock()
                mock_connection.search.return_value = ('OK', [b'3 2 1'])  # IMAP返回最旧邮件在前
                mock_ssl.return_value = mock_connection
                imap_service.connection = mock_connection
                imap_service.connected = True
                
                with patch.object(imap_service, '_get_message_by_id') as mock_get:
                    # 反转顺序后，应该返回邮件2和3（对应索引1和2）
                    mock_get.side_effect = [sample_messages[2], sample_messages[1]]  # 邮件3, 邮件2
                    
                    result = await imap_service.list_messages("INBOX", 2, 1)
                    
                    assert len(result) == 2
                    assert result[0].id == "3"  # 邮件3（最新）
                    assert result[1].id == "2"  # 邮件2（次新）
    
    @pytest.mark.asyncio
    async def test_list_messages_folder_selection_failure(self, imap_service):
        """测试文件夹选择失败"""
        with patch.object(imap_service, 'select_folder', return_value=False):
            result = await imap_service.list_messages("INBOX", 10, 0)
            
            assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_list_messages_empty_folder(self, imap_service):
        """测试空文件夹"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch.object(imap_service, '_get_message_by_id') as mock_get:
                mock_get.return_value = None
                
                result = await imap_service.list_messages("INBOX", 10, 0)
                
                assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_list_messages_invalid_pagination(self, imap_service):
        """测试无效分页参数"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch('imaplib.IMAP4_SSL') as mock_ssl:
                mock_connection = Mock()
                mock_connection.search.return_value = ('OK', [b'1 2 3'])
                mock_ssl.return_value = mock_connection
                imap_service.connection = mock_connection
                imap_service.connected = True
                
                # 测试无效的偏移量 - 应该返回空列表而不是错误
                result = await imap_service.list_messages("INBOX", 10, 10)
                assert len(result) == 0
                
                # 测试零限制 - 应该返回空列表
                result = await imap_service.list_messages("INBOX", 0, 0)
                assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_list_messages_connection_error(self, imap_service):
        """测试连接错误处理"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch('imaplib.IMAP4_SSL') as mock_ssl:
                mock_connection = Mock()
                mock_connection.search.side_effect = Exception("Connection error")
                mock_ssl.return_value = mock_connection
                imap_service.connection = mock_connection
                imap_service.connected = True
                
                result = await imap_service.list_messages("INBOX", 10, 0)
                
                assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_list_messages_different_folders(self, imap_service, sample_messages):
        """测试不同文件夹"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch('imaplib.IMAP4_SSL') as mock_ssl:
                mock_connection = Mock()
                mock_connection.search.return_value = ('OK', [b'3 2 1'])  # IMAP返回最旧邮件在前
                mock_ssl.return_value = mock_connection
                imap_service.connection = mock_connection
                imap_service.connected = True
                
                # 测试INBOX
                with patch.object(imap_service, '_get_message_by_id') as mock_get:
                    mock_get.side_effect = sample_messages
                    
                    result = await imap_service.list_messages("INBOX", 2, 0)
                    assert len(result) == 2
                
                # 测试Sent文件夹 (使用新的mock)
                with patch.object(imap_service, '_get_message_by_id') as mock_get2:
                    mock_get2.side_effect = sample_messages
                    
                    result = await imap_service.list_messages("Sent", 2, 0)
                    assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_list_messages_reverse_order(self, imap_service, sample_messages):
        """测试邮件按倒序排列（最新在前）"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch('imaplib.IMAP4_SSL') as mock_ssl:
                mock_connection = Mock()
                mock_connection.search.return_value = ('OK', [b'1 2 3'])  # IMAP返回最旧邮件在前
                mock_ssl.return_value = mock_connection
                imap_service.connection = mock_connection
                imap_service.connected = True
                
                with patch.object(imap_service, '_get_message_by_id') as mock_get:
                    # 反转后应该返回邮件3, 2, 1
                    mock_get.side_effect = [sample_messages[2], sample_messages[1], sample_messages[0]]
                    
                    result = await imap_service.list_messages("INBOX", 3, 0)
                    
                    # 验证结果是按最新在前排列的
                    assert result[0].id == "3"  # 最新邮件
                    assert result[1].id == "2"  # 中间邮件
                    assert result[2].id == "1"  # 最旧邮件
    
    @pytest.mark.asyncio
    async def test_list_messages_large_offset(self, imap_service, sample_messages):
        """测试大偏移量（超出范围）"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch.object(imap_service, '_get_message_by_id') as mock_get:
                mock_get.side_effect = sample_messages
                
                # 请求超出范围的偏移量
                result = await imap_service.list_messages("INBOX", 10, 10)
                
                # 应该返回空列表
                assert len(result) == 0