"""
测试邮件详情获取功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from mail_mcp.config import Config
from mail_mcp.imap_service import IMAPService
from mail_mcp.models import EmailMessage, EmailAttachment


class TestGetMessage:
    """测试邮件详情获取功能"""
    
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
    def sample_message(self):
        """创建示例邮件数据"""
        return EmailMessage(
            id="123",
            subject="测试邮件主题",
            from_address="sender@test.com",
            to_addresses=["recipient@test.com"],
            cc_addresses=["cc@test.com"],
            date="2025-09-20T15:30:00",
            body_text="这是邮件的纯文本内容。\n\n第二段内容。",
            body_html="<html><body><h1>HTML内容</h1><p>这是HTML格式的邮件内容。</p></body></html>",
            attachments=[
                EmailAttachment(
                    filename="document.pdf",
                    content_type="application/pdf",
                    size=1024
                ),
                EmailAttachment(
                    filename="image.jpg", 
                    content_type="image/jpeg",
                    size=512
                )
            ],
            is_read=False,
            message_id="msg123@test.com",
            folder="INBOX"
        )
    
    @pytest.fixture
    def simple_message(self):
        """创建简单邮件数据（无HTML、无附件）"""
        return EmailMessage(
            id="456",
            subject="简单邮件",
            from_address="simple@test.com",
            to_addresses=["recipient@test.com"],
            date="2025-09-20T16:00:00",
            body_text="纯文本邮件内容。",
            body_html=None,
            attachments=[],
            is_read=True,
            message_id="msg456@test.com",
            folder="INBOX"
        )
    
    @pytest.mark.asyncio
    async def test_get_message_success(self, imap_service, sample_message):
        """测试成功获取邮件详情"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch.object(imap_service, '_get_message_by_id', return_value=sample_message):
                result = await imap_service.get_message("123", "INBOX")
                
                assert result is not None
                assert result.id == "123"
                assert result.subject == "测试邮件主题"
                assert result.from_address == "sender@test.com"
                assert result.to_addresses == ["recipient@test.com"]
                assert result.cc_addresses == ["cc@test.com"]
                assert result.body_text == "这是邮件的纯文本内容。\n\n第二段内容。"
                assert result.body_html == "<html><body><h1>HTML内容</h1><p>这是HTML格式的邮件内容。</p></body></html>"
                assert len(result.attachments) == 2
                assert result.is_read is False
                assert result.message_id == "msg123@test.com"
                assert result.folder == "INBOX"
    
    @pytest.mark.asyncio
    async def test_get_message_folder_selection_failure(self, imap_service):
        """测试文件夹选择失败"""
        with patch.object(imap_service, 'select_folder', return_value=False):
            result = await imap_service.get_message("123", "INBOX")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_message_not_found(self, imap_service):
        """测试邮件不存在"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch.object(imap_service, '_get_message_by_id', return_value=None):
                result = await imap_service.get_message("999", "INBOX")
                
                assert result is None
    
    @pytest.mark.asyncio
    async def test_get_message_simple(self, imap_service, simple_message):
        """测试获取简单邮件（无HTML、无附件）"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch.object(imap_service, '_get_message_by_id', return_value=simple_message):
                result = await imap_service.get_message("456", "INBOX")
                
                assert result is not None
                assert result.id == "456"
                assert result.subject == "简单邮件"
                assert result.body_text == "纯文本邮件内容。"
                assert result.body_html is None
                assert len(result.attachments) == 0
                assert result.is_read is True
    
    @pytest.mark.asyncio
    async def test_get_message_different_folders(self, imap_service, sample_message):
        """测试从不同文件夹获取邮件"""
        with patch.object(imap_service, 'select_folder', return_value=True):
            # Mock _get_message_by_id to return objects with different folders
            def mock_get_message(message_id, folder):
                # Create a copy with the correct folder
                message_copy = EmailMessage(
                    id=sample_message.id,
                    subject=sample_message.subject,
                    from_address=sample_message.from_address,
                    to_addresses=sample_message.to_addresses,
                    cc_addresses=sample_message.cc_addresses,
                    date=sample_message.date,
                    body_text=sample_message.body_text,
                    body_html=sample_message.body_html,
                    attachments=sample_message.attachments,
                    is_read=sample_message.is_read,
                    message_id=sample_message.message_id,
                    folder=folder  # Use the provided folder
                )
                return message_copy
            
            with patch.object(imap_service, '_get_message_by_id', side_effect=mock_get_message):
                # 测试INBOX文件夹
                result = await imap_service.get_message("123", "INBOX")
                assert result.folder == "INBOX"
                
                # 测试Sent文件夹
                result = await imap_service.get_message("123", "Sent")
                assert result.folder == "Sent"
    
    @pytest.mark.asyncio
    async def test_get_message_connection_error(self, imap_service):
        """测试连接错误处理"""
        with patch.object(imap_service, 'select_folder', return_value=False):
            result = await imap_service.get_message("123", "INBOX")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_message_empty_body(self, imap_service):
        """测试空邮件正文"""
        empty_message = EmailMessage(
            id="789",
            subject="空邮件",
            from_address="empty@test.com",
            to_addresses=["recipient@test.com"],
            date="2025-09-20T17:00:00",
            body_text="",
            body_html=None,
            attachments=[],
            is_read=False,
            message_id="msg789@test.com",
            folder="INBOX"
        )
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch.object(imap_service, '_get_message_by_id', return_value=empty_message):
                result = await imap_service.get_message("789", "INBOX")
                
                assert result is not None
                assert result.body_text == ""
                assert result.body_html is None
    
    @pytest.mark.asyncio
    async def test_get_message_long_html_body(self, imap_service):
        """测试长HTML邮件正文"""
        long_html = "<html><body>" + "<p>测试内容</p>" * 100 + "</body></html>"
        long_html_message = EmailMessage(
            id="999",
            subject="长HTML邮件",
            from_address="long@test.com",
            to_addresses=["recipient@test.com"],
            date="2025-09-20T18:00:00",
            body_text="这是纯文本版本",
            body_html=long_html,
            attachments=[],
            is_read=False,
            message_id="msg999@test.com",
            folder="INBOX"
        )
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch.object(imap_service, '_get_message_by_id', return_value=long_html_message):
                result = await imap_service.get_message("999", "INBOX")
                
                assert result is not None
                assert result.body_html == long_html
                assert len(result.body_html) > 1000
    
    @pytest.mark.asyncio
    async def test_get_message_multiple_attachments(self, imap_service):
        """测试多附件邮件"""
        multi_attach_message = EmailMessage(
            id="1000",
            subject="多附件邮件",
            from_address="attach@test.com",
            to_addresses=["recipient@test.com"],
            date="2025-09-20T19:00:00",
            body_text="请查看附件。",
            body_html=None,
            attachments=[
                EmailAttachment("file1.pdf", "application/pdf", 2048),
                EmailAttachment("file2.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 4096),
                EmailAttachment("file3.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 8192),
                EmailAttachment("image.png", "image/png", 1024)
            ],
            is_read=False,
            message_id="msg1000@test.com",
            folder="INBOX"
        )
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch.object(imap_service, '_get_message_by_id', return_value=multi_attach_message):
                result = await imap_service.get_message("1000", "INBOX")
                
                assert result is not None
                assert len(result.attachments) == 4
                # 验证第一个附件
                assert result.attachments[0].filename == "file1.pdf"
                assert result.attachments[0].content_type == "application/pdf"
                assert result.attachments[0].size == 2048
                # 验证最后一个附件
                assert result.attachments[3].filename == "image.png"
                assert result.attachments[3].content_type == "image/png"
                assert result.attachments[3].size == 1024
    
    @pytest.mark.asyncio
    async def test_get_message_special_characters(self, imap_service):
        """测试特殊字符邮件"""
        special_message = EmailMessage(
            id="2000",
            subject="特殊字符邮件: 📧 测试 & 特殊符号",
            from_address="特殊@测试.com",
            to_addresses=["收件人@测试.com"],
            date="2025-09-20T20:00:00",
            body_text="邮件内容包含特殊字符：\n- 中文\n- Emoji 😊\n- 特殊符号 @#$%",
            body_html="<html><body><h1>标题 🌟</h1><p>内容包含中文和Emoji 😊</p></body></html>",
            attachments=[
                EmailAttachment("测试_文件.pdf", "application/pdf", 500)
            ],
            is_read=True,
            message_id="msg2000@测试.com",
            folder="INBOX"
        )
        
        with patch.object(imap_service, 'select_folder', return_value=True):
            with patch.object(imap_service, '_get_message_by_id', return_value=special_message):
                result = await imap_service.get_message("2000", "INBOX")
                
                assert result is not None
                assert "📧" in result.subject
                assert "😊" in result.body_text
                assert "🌟" in result.body_html
                assert result.attachments[0].filename == "测试_文件.pdf"