"""
测试邮件数据模型
"""

import pytest
import json
from datetime import datetime
from mail_mcp.models import (
    EmailAttachment, 
    EmailMessage, 
    EmailSearchCriteria,
    MAX_EMAIL_SIZE,
    MAX_ATTACHMENTS,
    MAX_ATTACHMENT_SIZE
)


class TestEmailAttachment:
    """测试EmailAttachment模型"""
    
    def test_attachment_creation(self):
        """测试附件创建"""
        attachment = EmailAttachment(
            filename="test.pdf",
            content_type="application/pdf",
            size=1024
        )
        
        assert attachment.filename == "test.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.size == 1024
        assert attachment.content is None
        assert attachment.attachment_id is None
    
    def test_attachment_with_content(self):
        """测试带内容的附件"""
        content = b"test content"
        attachment = EmailAttachment(
            filename="test.txt",
            content_type="text/plain",
            size=len(content),
            content=content,
            attachment_id="att123"
        )
        
        assert attachment.content == content
        assert attachment.attachment_id == "att123"
    
    def test_attachment_size_validation(self):
        """测试附件大小验证"""
        # 测试负大小
        with pytest.raises(ValueError, match="Attachment size cannot be negative"):
            EmailAttachment(filename="test.txt", content_type="text/plain", size=-1)
        
        # 测试超过最大大小
        with pytest.raises(ValueError, match=f"Attachment size exceeds maximum limit of {MAX_ATTACHMENT_SIZE}"):
            EmailAttachment(filename="test.txt", content_type="text/plain", size=MAX_ATTACHMENT_SIZE + 1)
    
    def test_attachment_to_dict(self):
        """测试附件转换为字典"""
        content = b"test content"
        attachment = EmailAttachment(
            filename="test.txt",
            content_type="text/plain",
            size=len(content),
            content=content,
            attachment_id="att123"
        )
        
        result = attachment.to_dict()
        
        assert result['filename'] == "test.txt"
        assert result['content_type'] == "text/plain"
        assert result['size'] == len(content)
        assert result['attachment_id'] == "att123"
        assert 'content' in result  # base64编码的内容
    
    def test_attachment_from_dict(self):
        """测试从字典创建附件"""
        data = {
            'filename': 'test.txt',
            'content_type': 'text/plain',
            'size': 12,
            'attachment_id': 'att123'
        }
        
        attachment = EmailAttachment.from_dict(data)
        
        assert attachment.filename == "test.txt"
        assert attachment.content_type == "text/plain"
        assert attachment.size == 12
        assert attachment.attachment_id == "att123"
    
    def test_attachment_json_serialization(self):
        """测试附件JSON序列化"""
        attachment = EmailAttachment(
            filename="test.pdf",
            content_type="application/pdf",
            size=2048
        )
        
        json_str = attachment.to_json()
        assert isinstance(json_str, str)
        
        # 验证JSON可以解析
        data = json.loads(json_str)
        assert data['filename'] == "test.pdf"
        
        # 测试从JSON重建
        rebuilt = EmailAttachment.from_json(json_str)
        assert rebuilt.filename == attachment.filename
        assert rebuilt.content_type == attachment.content_type
        assert rebuilt.size == attachment.size


class TestEmailMessage:
    """测试EmailMessage模型"""
    
    def test_email_creation(self):
        """测试邮件创建"""
        email = EmailMessage(
            id="msg123",
            subject="Test Subject",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            date="2025-01-20T10:00:00Z",
            body_text="Test body"
        )
        
        assert email.id == "msg123"
        assert email.subject == "Test Subject"
        assert email.from_address == "sender@example.com"
        assert email.to_addresses == ["recipient@example.com"]
        assert email.date == "2025-01-20T10:00:00Z"
        assert email.body_text == "Test body"
        assert email.body_html is None
        assert email.attachments == []
        assert email.is_read is False
        assert email.folder == "INBOX"
    
    def test_email_validation(self):
        """测试邮件验证"""
        # 测试空ID
        with pytest.raises(ValueError, match="Email ID cannot be empty"):
            EmailMessage(
                id="",
                subject="Test",
                from_address="sender@example.com",
                to_addresses=["recipient@example.com"],
                date="2025-01-20T10:00:00Z",
                body_text="Test"
            )
        
        # 测试空主题
        with pytest.raises(ValueError, match="Email subject cannot be empty"):
            EmailMessage(
                id="msg123",
                subject="",
                from_address="sender@example.com",
                to_addresses=["recipient@example.com"],
                date="2025-01-20T10:00:00Z",
                body_text="Test"
            )
        
        # 测试空收件人
        with pytest.raises(ValueError, match="At least one recipient is required"):
            EmailMessage(
                id="msg123",
                subject="Test",
                from_address="sender@example.com",
                to_addresses=[],
                date="2025-01-20T10:00:00Z",
                body_text="Test"
            )
        
        # 测试附件数量限制
        attachments = [
            EmailAttachment(f"test{i}.pdf", "application/pdf", 1000)
            for i in range(MAX_ATTACHMENTS + 1)
        ]
        with pytest.raises(ValueError, match=f"Number of attachments exceeds maximum limit of {MAX_ATTACHMENTS}"):
            EmailMessage(
                id="msg123",
                subject="Test",
                from_address="sender@example.com",
                to_addresses=["recipient@example.com"],
                date="2025-01-20T10:00:00Z",
                body_text="Test",
                attachments=attachments
            )
    
    def test_email_to_dict(self):
        """测试邮件转换为字典"""
        email = EmailMessage(
            id="msg123",
            subject="Test Subject",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            cc_addresses=["cc@example.com"],
            bcc_addresses=["bcc@example.com"],
            date="2025-01-20T10:00:00Z",
            body_text="Test body",
            body_html="<p>Test HTML</p>",
            is_read=True,
            message_id="msg-id-123",
            folder="Sent",
            reply_to="reply@example.com",
            flags=["\\Seen", "\\Answered"]
        )
        
        result = email.to_dict()
        
        assert result['id'] == "msg123"
        assert result['subject'] == "Test Subject"
        assert result['from_address'] == "sender@example.com"
        assert result['to_addresses'] == ["recipient@example.com"]
        assert result['cc_addresses'] == ["cc@example.com"]
        assert result['bcc_addresses'] == ["bcc@example.com"]
        assert result['date'] == "2025-01-20T10:00:00Z"
        assert result['body_text'] == "Test body"
        assert result['body_html'] == "<p>Test HTML</p>"
        assert result['is_read'] is True
        assert result['folder'] == "Sent"
        assert result['message_id'] == "msg-id-123"
        assert result['reply_to'] == "reply@example.com"
        assert result['flags'] == ["\\Seen", "\\Answered"]
    
    def test_email_from_dict(self):
        """测试从字典创建邮件"""
        data = {
            'id': 'msg123',
            'subject': 'Test Subject',
            'from_address': 'sender@example.com',
            'to_addresses': ['recipient@example.com'],
            'cc_addresses': ['cc@example.com'],
            'bcc_addresses': ['bcc@example.com'],
            'date': '2025-01-20T10:00:00Z',
            'body_text': 'Test body',
            'body_html': '<p>Test HTML</p>',
            'attachments': [
                {
                    'filename': 'test.pdf',
                    'content_type': 'application/pdf',
                    'size': 1024
                }
            ],
            'is_read': True,
            'folder': 'Sent',
            'message_id': 'msg-id-123',
            'reply_to': 'reply@example.com',
            'flags': ['\\Seen', '\\Answered']
        }
        
        email = EmailMessage.from_dict(data)
        
        assert email.id == "msg123"
        assert email.subject == "Test Subject"
        assert email.from_address == "sender@example.com"
        assert email.to_addresses == ["recipient@example.com"]
        assert email.cc_addresses == ["cc@example.com"]
        assert email.bcc_addresses == ["bcc@example.com"]
        assert len(email.attachments) == 1
        assert email.attachments[0].filename == "test.pdf"
    
    def test_email_summary(self):
        """测试邮件摘要"""
        email = EmailMessage(
            id="msg123",
            subject="Test Subject",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            date="2025-01-20T10:00:00Z",
            body_text="Test body",
            attachments=[EmailAttachment("test.pdf", "application/pdf", 1024)]
        )
        
        summary = email.get_summary()
        
        assert summary['id'] == "msg123"
        assert summary['subject'] == "Test Subject"
        assert summary['from_address'] == "sender@example.com"
        assert summary['to_addresses'] == ["recipient@example.com"]
        assert summary['date'] == "2025-01-20T10:00:00Z"
        assert summary['is_read'] is False
        assert summary['has_attachments'] is True
        assert summary['attachment_count'] == 1
        assert summary['folder'] == "INBOX"
    
    def test_email_json_serialization(self):
        """测试邮件JSON序列化"""
        email = EmailMessage(
            id="msg123",
            subject="Test Subject",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            date="2025-01-20T10:00:00Z",
            body_text="Test body"
        )
        
        json_str = email.to_json()
        assert isinstance(json_str, str)
        
        # 验证JSON可以解析
        data = json.loads(json_str)
        assert data['id'] == "msg123"
        
        # 测试从JSON重建
        rebuilt = EmailMessage.from_json(json_str)
        assert rebuilt.id == email.id
        assert rebuilt.subject == email.subject
        assert rebuilt.from_address == email.from_address


class TestEmailSearchCriteria:
    """测试EmailSearchCriteria模型"""
    
    def test_search_criteria_creation(self):
        """测试搜索条件创建"""
        criteria = EmailSearchCriteria(
            folder="Sent",
            from_address="sender@example.com",
            subject="Test",
            limit=50
        )
        
        assert criteria.folder == "Sent"
        assert criteria.from_address == "sender@example.com"
        assert criteria.subject == "Test"
        assert criteria.limit == 50
        assert criteria.offset == 0  # 默认值
    
    def test_search_criteria_validation(self):
        """测试搜索条件验证"""
        # 测试limit太小
        with pytest.raises(ValueError, match="Limit must be at least 1"):
            EmailSearchCriteria(limit=0)
        
        # 测试limit太大
        with pytest.raises(ValueError, match="Limit cannot exceed 100"):
            EmailSearchCriteria(limit=101)
        
        # 测试offset为负数
        with pytest.raises(ValueError, match="Offset cannot be negative"):
            EmailSearchCriteria(offset=-1)
    
    def test_search_criteria_to_dict(self):
        """测试搜索条件转换为字典"""
        criteria = EmailSearchCriteria(
            folder="INBOX",
            from_address="sender@example.com",
            subject="Test",
            is_read=True,
            limit=20,
            offset=10
        )
        
        result = criteria.to_dict()
        
        assert result['folder'] == "INBOX"
        assert result['from_address'] == "sender@example.com"
        assert result['subject'] == "Test"
        assert result['is_read'] is True
        assert result['limit'] == 20
        assert result['offset'] == 10
    
    def test_search_criteria_has_filters(self):
        """测试是否有过滤条件"""
        # 无过滤条件
        criteria1 = EmailSearchCriteria()
        assert criteria1.has_filters() is False
        
        # 有过滤条件
        criteria2 = EmailSearchCriteria(from_address="sender@example.com")
        assert criteria2.has_filters() is True
        
        criteria3 = EmailSearchCriteria(is_read=False)
        assert criteria3.has_filters() is True
    
    def test_search_criteria_from_dict(self):
        """测试从字典创建搜索条件"""
        data = {
            'folder': 'Sent',
            'from_address': 'sender@example.com',
            'subject': 'Test',
            'limit': 50,
            'offset': 10
        }
        
        criteria = EmailSearchCriteria.from_dict(data)
        
        assert criteria.folder == "Sent"
        assert criteria.from_address == "sender@example.com"
        assert criteria.subject == "Test"
        assert criteria.limit == 50
        assert criteria.offset == 10


class TestConstants:
    """测试常量定义"""
    
    def test_constants_values(self):
        """测试常量值"""
        assert MAX_EMAIL_SIZE == 25 * 1024 * 1024  # 25MB
        assert MAX_ATTACHMENTS == 20
        assert MAX_ATTACHMENT_SIZE == 20 * 1024 * 1024  # 20MB