"""
测试带附件的邮件发送功能
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from email.mime.base import MIMEBase

from mail_mcp.config import Config
from mail_mcp.smtp_service import SMTPService


class TestSendEmailWithAttachments:
    """测试带附件的邮件发送功能"""
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=Config)
        config.smtp = Mock()
        config.smtp.host = "smtp.test.com"
        config.smtp.port = 587
        config.smtp.username = "test@test.com"
        config.smtp.password = "test_password"
        config.smtp.use_ssl = False
        return config
    
    @pytest.fixture
    def smtp_service(self, mock_config):
        """创建SMTP服务实例"""
        return SMTPService(mock_config)
    
    @pytest.fixture
    def temp_text_file(self):
        """创建临时文本文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("这是一个测试文件的内容。")
            f.flush()
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def temp_pdf_file(self):
        """创建临时PDF文件（模拟）"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            # 写入一些假的PDF内容
            f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
            f.flush()
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def large_temp_file(self):
        """创建大文件（测试大小限制）"""
        # 创建一个接近限制大小的文件
        large_size = SMTPService.MAX_ATTACHMENT_SIZE - 1000  # 留一点余量
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.dat', delete=False) as f:
            f.write(b'0' * large_size)
            f.flush()
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def oversized_file(self):
        """创建超过大小限制的文件"""
        oversized_size = SMTPService.MAX_ATTACHMENT_SIZE + 1000
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.dat', delete=False) as f:
            f.write(b'0' * oversized_size)
            f.flush()
            yield f.name
        os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_validate_attachment_file_success(self, smtp_service, temp_text_file):
        """测试附件文件验证成功"""
        result = smtp_service._validate_attachment_file(temp_text_file)
        
        assert result['valid'] is True
        assert 'file_size' in result
        assert 'file_path' in result
        assert result['file_path'] == temp_text_file
        assert result['file_size'] > 0
    
    @pytest.mark.asyncio
    async def test_validate_attachment_file_not_exists(self, smtp_service):
        """测试不存在的文件"""
        result = smtp_service._validate_attachment_file("/nonexistent/file.txt")
        
        assert result['valid'] is False
        assert 'error' in result
        assert "文件不存在" in result['error']
    
    @pytest.mark.asyncio
    async def test_validate_attachment_file_is_directory(self, smtp_service, tmp_path):
        """测试目录而非文件"""
        result = smtp_service._validate_attachment_file(str(tmp_path))
        
        assert result['valid'] is False
        assert 'error' in result
        assert "不是有效文件" in result['error']
    
    @pytest.mark.asyncio
    async def test_validate_attachment_file_oversized(self, smtp_service, oversized_file):
        """测试文件大小超过限制"""
        result = smtp_service._validate_attachment_file(oversized_file)
        
        assert result['valid'] is False
        assert 'error' in result
        assert "文件大小超过限制" in result['error']
    
    @pytest.mark.asyncio
    async def test_create_attachment_from_file_success(self, smtp_service, temp_text_file):
        """测试从文件创建附件成功"""
        attachment = smtp_service._create_attachment_from_file(temp_text_file)
        
        assert attachment is not None
        assert isinstance(attachment, MIMEBase)
        # 检查Content-Disposition头
        content_disposition = attachment.get('Content-Disposition', '')
        assert 'attachment' in content_disposition
        assert '.txt' in content_disposition
    
    @pytest.mark.asyncio
    async def test_create_attachment_from_file_invalid(self, smtp_service):
        """测试从无效文件创建附件"""
        attachment = smtp_service._create_attachment_from_file("/nonexistent/file.txt")
        
        assert attachment is None
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_success(self, smtp_service, temp_text_file):
        """测试发送带附件的邮件成功"""
        # 模拟连接
        smtp_service.connected = True
        smtp_service.connection = Mock()
        smtp_service.connection.sendmail = Mock()
        
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试带附件的邮件",
            body_text="请查看附件。",
            attachments=[temp_text_file]
        )
        
        assert result['success'] is True
        assert 'message' in result
        assert 'attachments' in result
        assert len(result['attachments']) == 1
        assert 'total_size' in result
        assert result['total_size'] > 0
        assert result['recipient_count'] == 1
        
        # 验证sendmail被调用
        smtp_service.connection.sendmail.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_multiple(self, smtp_service, temp_text_file, temp_pdf_file):
        """测试发送多个附件的邮件"""
        # 模拟连接
        smtp_service.connected = True
        smtp_service.connection = Mock()
        smtp_service.connection.sendmail = Mock()
        
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试多附件邮件",
            body_text="请查看多个附件。",
            attachments=[temp_text_file, temp_pdf_file]
        )
        
        assert result['success'] is True
        assert len(result['attachments']) == 2
        assert result['recipient_count'] == 1
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_with_html(self, smtp_service, temp_text_file):
        """测试带HTML正文和附件的邮件"""
        # 模拟连接
        smtp_service.connected = True
        smtp_service.connection = Mock()
        smtp_service.connection.sendmail = Mock()
        
        html_body = "<html><body><h1>测试</h1><p>HTML正文内容</p></body></html>"
        
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试HTML和附件",
            body_text="纯文本版本",
            attachments=[temp_text_file],
            body_html=html_body
        )
        
        assert result['success'] is True
        assert len(result['attachments']) == 1
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_invalid_email(self, smtp_service, temp_text_file):
        """测试无效邮箱地址"""
        result = await smtp_service.send_email_with_attachments(
            to="invalid-email",
            subject="测试",
            body_text="内容",
            attachments=[temp_text_file]
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert "无效的收件人邮箱地址" in result['error']
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_no_attachments(self, smtp_service):
        """测试没有提供附件"""
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试",
            body_text="内容",
            attachments=[]
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert "必须提供至少一个附件文件" in result['error']
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_invalid_files(self, smtp_service):
        """测试包含无效文件的附件列表"""
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试",
            body_text="内容",
            attachments=["/nonexistent/file1.txt", "/nonexistent/file2.pdf"]
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert "附件文件验证失败" in result['error']
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_mixed_valid_invalid(self, smtp_service, temp_text_file):
        """测试混合有效和无效文件"""
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试",
            body_text="内容",
            attachments=[temp_text_file, "/nonexistent/file.pdf"]
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert "附件文件验证失败" in result['error']
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_connection_failure(self, smtp_service, temp_text_file):
        """测试连接失败"""
        smtp_service.connected = False
        
        with patch.object(smtp_service, 'connect', return_value=False):
            result = await smtp_service.send_email_with_attachments(
                to="recipient@test.com",
                subject="测试",
                body_text="内容",
                attachments=[temp_text_file]
            )
            
            assert result['success'] is False
            assert 'error' in result
            assert "无法连接到SMTP服务器" in result['error']
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_with_cc_bcc(self, smtp_service, temp_text_file):
        """测试带抄送和密送的邮件"""
        # 模拟连接
        smtp_service.connected = True
        smtp_service.connection = Mock()
        smtp_service.connection.sendmail = Mock()
        
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试抄送密送",
            body_text="内容",
            attachments=[temp_text_file],
            cc=["cc1@test.com", "cc2@test.com"],
            bcc=["bcc@test.com"]
        )
        
        assert result['success'] is True
        assert result['recipient_count'] == 4  # 1 to + 2 cc + 1 bcc
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_send_failure(self, smtp_service, temp_text_file):
        """测试发送失败"""
        # 模拟连接成功但发送失败
        smtp_service.connected = True
        smtp_service.connection = Mock()
        smtp_service.connection.sendmail.side_effect = Exception("SMTP error")
        
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试",
            body_text="内容",
            attachments=[temp_text_file]
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert "发送邮件失败" in result['error']
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_large_file(self, smtp_service, large_temp_file):
        """测试接近大小限制的大文件"""
        # 模拟连接
        smtp_service.connected = True
        smtp_service.connection = Mock()
        smtp_service.connection.sendmail = Mock()
        
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试大文件",
            body_text="内容",
            attachments=[large_temp_file]
        )
        
        assert result['success'] is True
        assert result['total_size'] > 0
        assert len(result['attachments']) == 1
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments_oversized_file(self, smtp_service, oversized_file):
        """测试超过大小限制的文件"""
        result = await smtp_service.send_email_with_attachments(
            to="recipient@test.com",
            subject="测试",
            body_text="内容",
            attachments=[oversized_file]
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert "附件文件验证失败" in result['error']
        assert "文件大小超过限制" in result['error']
    
    def test_max_attachment_size_constant(self):
        """测试最大附件大小常量"""
        assert SMTPService.MAX_ATTACHMENT_SIZE == 25 * 1024 * 1024  # 25MB