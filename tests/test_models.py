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
    SearchRequest,
    EmailResult,
    SearchResult,
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


class TestSearchRequest:
    """测试SearchRequest模型"""
    
    def test_search_request_creation(self):
        """测试搜索请求创建"""
        request = SearchRequest(
            query="test email",
            date_from="2025-01-01",
            date_to="2025-01-31",
            page=2,
            page_size=10,
            folder="Sent",
            sender="sender@example.com"
        )
        
        assert request.query == "test email"
        assert request.date_from == "2025-01-01"
        assert request.date_to == "2025-01-31"
        assert request.page == 2
        assert request.page_size == 10
        assert request.folder == "Sent"
        assert request.sender == "sender@example.com"
        assert request.recipient is None
        assert request.has_attachments is None
    
    def test_search_request_defaults(self):
        """测试搜索请求默认值"""
        request = SearchRequest()
        
        assert request.query is None
        assert request.date_from is None
        assert request.date_to is None
        assert request.page == 1
        assert request.page_size == 20
        assert request.folder == "INBOX"
        assert request.sender is None
        assert request.recipient is None
        assert request.has_attachments is None
    
    def test_search_request_validation(self):
        """测试搜索请求验证"""
        # 测试页码小于1
        with pytest.raises(ValueError, match="Page must be at least 1"):
            SearchRequest(page=0)
        
        # 测试页面大小小于1
        with pytest.raises(ValueError, match="Page size must be at least 1"):
            SearchRequest(page_size=0)
        
        # 测试页面大小超过限制
        with pytest.raises(ValueError, match="Page size cannot exceed 100"):
            SearchRequest(page_size=101)
        
        # 测试日期格式错误
        with pytest.raises(ValueError, match="date_from must be in YYYY-MM-DD format"):
            SearchRequest(date_from="2025/01/01")
        
        with pytest.raises(ValueError, match="date_to must be in YYYY-MM-DD format"):
            SearchRequest(date_to="01-01-2025")
    
    def test_search_request_to_dict(self):
        """测试搜索请求转换为字典"""
        request = SearchRequest(
            query="test",
            page=2,
            page_size=10,
            sender="sender@example.com"
        )
        
        result = request.to_dict()
        
        assert result['query'] == "test"
        assert result['page'] == 2
        assert result['page_size'] == 10
        assert result['folder'] == "INBOX"
        assert result['sender'] == "sender@example.com"
        # None值应该被排除
        assert 'date_from' not in result
        assert 'date_to' not in result
        assert 'recipient' not in result
        assert 'has_attachments' not in result
    
    def test_search_request_json_serialization(self):
        """测试搜索请求JSON序列化"""
        request = SearchRequest(
            query="test email",
            date_from="2025-01-01",
            page=1,
            page_size=20
        )
        
        json_str = request.to_json()
        assert isinstance(json_str, str)
        
        # 验证JSON可以解析
        data = json.loads(json_str)
        assert data['query'] == "test email"
        assert data['date_from'] == "2025-01-01"
        
        # 测试从JSON重建
        rebuilt = SearchRequest.from_json(json_str)
        assert rebuilt.query == request.query
        assert rebuilt.date_from == request.date_from


class TestEmailResult:
    """测试EmailResult模型"""
    
    def test_email_result_creation(self):
        """测试邮件结果创建"""
        result = EmailResult(
            uid="12345",
            subject="Test Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            date="2025-01-20T10:00:00Z",
            folder="INBOX",
            summary="This is a test email summary",
            has_attachments=True,
            is_read=False,
            message_id="msg-123"
        )
        
        assert result.uid == "12345"
        assert result.subject == "Test Email"
        assert result.sender == "sender@example.com"
        assert result.recipient == "recipient@example.com"
        assert result.date == "2025-01-20T10:00:00Z"
        assert result.folder == "INBOX"
        assert result.summary == "This is a test email summary"
        assert result.has_attachments is True
        assert result.is_read is False
        assert result.message_id == "msg-123"
    
    def test_email_result_validation(self):
        """测试邮件结果验证"""
        # 测试空UID
        with pytest.raises(ValueError, match="UID cannot be empty"):
            EmailResult("", "subject", "sender", "recipient", "date", "folder", "summary")
        
        # 测试空主题
        with pytest.raises(ValueError, match="Subject cannot be empty"):
            EmailResult("uid", "", "sender", "recipient", "date", "folder", "summary")
        
        # 测试空发件人
        with pytest.raises(ValueError, match="Sender cannot be empty"):
            EmailResult("uid", "subject", "", "recipient", "date", "folder", "summary")
        
        # 测试空收件人
        with pytest.raises(ValueError, match="Recipient cannot be empty"):
            EmailResult("uid", "subject", "sender", "", "date", "folder", "summary")
        
        # 测试空日期
        with pytest.raises(ValueError, match="Date cannot be empty"):
            EmailResult("uid", "subject", "sender", "recipient", "", "folder", "summary")
        
        # 测试空文件夹
        with pytest.raises(ValueError, match="Folder cannot be empty"):
            EmailResult("uid", "subject", "sender", "recipient", "date", "", "summary")
    
    def test_email_result_summary_truncation(self):
        """测试邮件结果摘要截断"""
        long_summary = "A" * 250  # 超过200字符的摘要
        result = EmailResult(
            uid="12345",
            subject="Test",
            sender="sender@example.com",
            recipient="recipient@example.com",
            date="2025-01-20T10:00:00Z",
            folder="INBOX",
            summary=long_summary
        )
        
        # 摘要应该被截断为200字符，末尾添加"..."
        assert len(result.summary) == 200
        assert result.summary.endswith("...")
        assert result.summary == "A" * 197 + "..."
    
    def test_email_result_json_serialization(self):
        """测试邮件结果JSON序列化"""
        result = EmailResult(
            uid="12345",
            subject="Test Email",
            sender="sender@example.com",
            recipient="recipient@example.com",
            date="2025-01-20T10:00:00Z",
            folder="INBOX",
            summary="Test summary"
        )
        
        json_str = result.to_json()
        assert isinstance(json_str, str)
        
        # 验证JSON可以解析
        data = json.loads(json_str)
        assert data['uid'] == "12345"
        assert data['subject'] == "Test Email"
        
        # 测试从JSON重建
        rebuilt = EmailResult.from_json(json_str)
        assert rebuilt.uid == result.uid
        assert rebuilt.subject == result.subject


class TestSearchResult:
    """测试SearchResult模型"""
    
    def test_search_result_creation(self):
        """测试搜索结果创建"""
        emails = [
            EmailResult("1", "Email 1", "sender1", "recipient1", "2025-01-20", "INBOX", "Summary 1"),
            EmailResult("2", "Email 2", "sender2", "recipient2", "2025-01-21", "INBOX", "Summary 2")
        ]
        
        result = SearchResult(
            total_count=50,
            current_page=2,
            total_pages=5,
            page_size=10,
            emails=emails,
            query="test query",
            search_time_ms=150
        )
        
        assert result.total_count == 50
        assert result.current_page == 2
        assert result.total_pages == 5
        assert result.page_size == 10
        assert len(result.emails) == 2
        assert result.query == "test query"
        assert result.search_time_ms == 150
    
    def test_search_result_validation(self):
        """测试搜索结果验证"""
        # 测试负的总数
        with pytest.raises(ValueError, match="Total count cannot be negative"):
            SearchResult(-1, 1, 1, 10)
        
        # 测试当前页小于1
        with pytest.raises(ValueError, match="Current page must be at least 1"):
            SearchResult(10, 0, 1, 10)
        
        # 测试负的总页数
        with pytest.raises(ValueError, match="Total pages cannot be negative"):
            SearchResult(10, 1, -1, 10)
        
        # 测试页面大小小于1
        with pytest.raises(ValueError, match="Page size must be at least 1"):
            SearchResult(10, 1, 1, 0)
        
        # 测试当前页超过总页数
        with pytest.raises(ValueError, match="Current page cannot exceed total pages"):
            SearchResult(10, 3, 2, 10)
    
    def test_search_result_pagination_methods(self):
        """测试搜索结果分页方法"""
        # 测试有更多页面
        result1 = SearchResult(50, 2, 5, 10)
        assert result1.has_more_pages() is True
        assert result1.has_previous_page() is True
        
        # 测试没有更多页面（最后一页）
        result2 = SearchResult(50, 5, 5, 10)
        assert result2.has_more_pages() is False
        assert result2.has_previous_page() is True
        
        # 测试第一页
        result3 = SearchResult(50, 1, 5, 10)
        assert result3.has_more_pages() is True
        assert result3.has_previous_page() is False
        
        # 测试只有一页
        result4 = SearchResult(10, 1, 1, 10)
        assert result4.has_more_pages() is False
        assert result4.has_previous_page() is False
    
    def test_search_result_to_dict(self):
        """测试搜索结果转换为字典"""
        emails = [
            EmailResult("1", "Email 1", "sender1", "recipient1", "2025-01-20", "INBOX", "Summary 1")
        ]
        
        result = SearchResult(
            total_count=25,
            current_page=2,
            total_pages=3,
            page_size=10,
            emails=emails,
            query="test",
            search_time_ms=100
        )
        
        dict_result = result.to_dict()
        
        assert dict_result['total_count'] == 25
        assert dict_result['current_page'] == 2
        assert dict_result['total_pages'] == 3
        assert dict_result['page_size'] == 10
        assert len(dict_result['emails']) == 1
        assert dict_result['query'] == "test"
        assert dict_result['search_time_ms'] == 100
        assert isinstance(dict_result['emails'][0], dict)
    
    def test_search_result_json_serialization(self):
        """测试搜索结果JSON序列化"""
        emails = [
            EmailResult("1", "Email 1", "sender1", "recipient1", "2025-01-20", "INBOX", "Summary 1")
        ]
        
        result = SearchResult(
            total_count=25,
            current_page=1,
            total_pages=3,
            page_size=10,
            emails=emails
        )
        
        json_str = result.to_json()
        assert isinstance(json_str, str)
        
        # 验证JSON可以解析
        data = json.loads(json_str)
        assert data['total_count'] == 25
        assert len(data['emails']) == 1
        
        # 测试从JSON重建
        rebuilt = SearchResult.from_json(json_str)
        assert rebuilt.total_count == result.total_count
        assert len(rebuilt.emails) == len(result.emails)
        assert rebuilt.emails[0].uid == result.emails[0].uid


class TestConstants:
    """测试常量定义"""
    
    def test_constants_values(self):
        """测试常量值"""
        assert MAX_EMAIL_SIZE == 25 * 1024 * 1024  # 25MB
        assert MAX_ATTACHMENTS == 20
        assert MAX_ATTACHMENT_SIZE == 20 * 1024 * 1024  # 20MB