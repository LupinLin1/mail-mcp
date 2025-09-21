"""
测试搜索和标记功能的额外单元测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from mail_mcp.imap_service import IMAPService
from mail_mcp.config import Config
from mail_mcp.models import EmailMessage, EmailSearchCriteria


class TestSearchAndMarkFunctionality:
    """测试搜索和标记功能"""

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        return Mock(spec=Config)

    @pytest.fixture
    def imap_service(self, mock_config):
        """创建 IMAP 服务实例"""
        service = IMAPService(mock_config)
        service.connected = True
        service.connection = Mock()
        return service

    @pytest.mark.asyncio
    async def test_search_messages_simple_success(self, imap_service):
        """测试简单搜索功能成功"""
        # 模拟连接和文件夹选择
        imap_service.connection.select.return_value = ('OK', [b'1'])
        imap_service.connection.search.return_value = ('OK', [b'1 2 3'])
        
        # 模拟邮件获取
        with patch.object(imap_service, '_get_message_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(
                subject="测试邮件",
                from_address="sender@example.com",
                is_read=False
            )
            
            results = await imap_service.search_messages_simple(
                query="测试",
                folder="INBOX",
                limit=10
            )
            
            assert len(results) == 3  # 搜索返回3封邮件
            mock_get.assert_called()

    @pytest.mark.asyncio
    async def test_search_messages_simple_no_results(self, imap_service):
        """测试搜索无结果的情况"""
        imap_service.connection.select.return_value = ('OK', [b'1'])
        imap_service.connection.search.return_value = ('OK', [b''])
        
        results = await imap_service.search_messages_simple(
            query="不存在的关键词",
            folder="INBOX",
            limit=10
        )
        
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_messages_simple_folder_selection_failure(self, imap_service):
        """测试文件夹选择失败的情况"""
        imap_service.connection.select.return_value = ('NO', [b'Folder not found'])
        
        results = await imap_service.search_messages_simple(
            query="test",
            folder="INVALID_FOLDER",
            limit=10
        )
        
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_mark_messages_as_read_success(self, imap_service):
        """测试批量标记邮件为已读成功"""
        imap_service.connection.select.return_value = ('OK', [b'1'])
        
        # 模拟成功的标记操作
        imap_service.connection.store.side_effect = [
            ('OK', [b'1']),  # 第一封邮件成功
            ('OK', [b'2']),  # 第二封邮件成功
            ('OK', [b'3'])   # 第三封邮件成功
        ]
        
        result = await imap_service.mark_messages_as_read(
            ['1', '2', '3'],
            folder="INBOX"
        )
        
        assert result['success'] is True
        assert result['successful_count'] == 3
        assert result['failed_count'] == 0
        assert result['total_count'] == 3
        assert len(result['successful_ids']) == 3
        
        # 验证调用了3次标记操作
        assert imap_service.connection.store.call_count == 3

    @pytest.mark.asyncio
    async def test_mark_messages_as_read_partial_failure(self, imap_service):
        """测试批量标记部分成功的情况"""
        imap_service.connection.select.return_value = ('OK', [b'1'])
        
        # 模拟部分成功的标记操作
        imap_service.connection.store.side_effect = [
            ('OK', [b'1']),      # 第一封邮件成功
            ('NO', [b'Error']),  # 第二封邮件失败
            ('OK', [b'3'])       # 第三封邮件成功
        ]
        
        result = await imap_service.mark_messages_as_read(
            ['1', '2', '3'],
            folder="INBOX"
        )
        
        assert result['success'] is False
        assert result['successful_count'] == 2
        assert result['failed_count'] == 1
        assert result['total_count'] == 3
        assert result['successful_ids'] == ['1', '3']
        assert result['failed_ids'] == ['2']

    @pytest.mark.asyncio
    async def test_mark_messages_as_read_empty_list(self, imap_service):
        """测试空邮件ID列表的情况"""
        result = await imap_service.mark_messages_as_read([], folder="INBOX")
        
        assert result['success'] is False
        assert '必须提供至少一个邮件ID' in result['error']

    @pytest.mark.asyncio
    async def test_mark_messages_as_read_folder_selection_failure(self, imap_service):
        """测试文件夹选择失败的情况"""
        imap_service.connection.select.return_value = ('NO', [b'Folder not found'])
        
        result = await imap_service.mark_messages_as_read(
            ['1', '2'],
            folder="INVALID_FOLDER"
        )
        
        assert result['success'] is False
        assert '无法选择文件夹' in result['error']

    @pytest.mark.asyncio
    async def test_mark_messages_as_read_exception_handling(self, imap_service):
        """测试异常处理"""
        imap_service.connection.select.return_value = ('OK', [b'1'])
        imap_service.connection.store.side_effect = Exception("IMAP error")
        
        result = await imap_service.mark_messages_as_read(
            ['1', '2'],
            folder="INBOX"
        )
        
        assert result['success'] is False
        assert result['successful_count'] == 0
        assert result['failed_count'] == 2
        assert result['failed_ids'] == ['1', '2']

    @pytest.mark.asyncio
    async def test_mark_as_read_single_message_success(self, imap_service):
        """测试单邮件标记成功"""
        imap_service.connection.select.return_value = ('OK', [b'1'])
        imap_service.connection.store.return_value = ('OK', [b'1'])
        
        result = await imap_service.mark_as_read('123', folder="INBOX")
        
        assert result is True
        imap_service.connection.store.assert_called_once_with('123', '+FLAGS', '\\Seen')

    @pytest.mark.asyncio
    async def test_mark_as_read_single_message_failure(self, imap_service):
        """测试单邮件标记失败的情况"""
        imap_service.connection.select.return_value = ('OK', [b'1'])
        imap_service.connection.store.return_value = ('NO', [b'Error'])
        
        result = await imap_service.mark_as_read('123', folder="INBOX")
        
        assert result is False

    def test_search_criteria_creation(self):
        """测试搜索条件创建"""
        criteria = EmailSearchCriteria(
            folder="INBOX",
            subject="测试",
            from_address="sender@example.com",
            is_read=False,
            limit=10
        )
        
        assert criteria.folder == "INBOX"
        assert criteria.subject == "测试"
        assert criteria.from_address == "sender@example.com"
        assert criteria.is_read is False
        assert criteria.limit == 10

    def test_search_criteria_validation(self):
        """测试搜索条件验证"""
        # 有效条件
        criteria = EmailSearchCriteria(folder="INBOX")
        assert criteria.folder == "INBOX"
        
        # 测试默认值
        criteria = EmailSearchCriteria()
        assert criteria.folder == "INBOX"  # 默认文件夹
        assert criteria.limit > 0

    @pytest.mark.asyncio
    async def test_search_messages_with_criteria_success(self, imap_service):
        """测试使用完整搜索条件的搜索成功"""
        imap_service.connection.select.return_value = ('OK', [b'1'])
        imap_service.connection.search.return_value = ('OK', [b'1'])
        
        criteria = EmailSearchCriteria(
            folder="INBOX",
            subject="重要通知",
            from_address="admin@example.com",
            to_address="user@example.com",
            body_text="请查收",
            is_read=False,
            limit=5
        )
        
        with patch.object(imap_service, '_get_message_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(
                subject="重要通知",
                from_address="admin@example.com",
                is_read=False
            )
            
            results = await imap_service.search_messages(criteria)
            
            assert len(results) == 1
            # 验证搜索调用了正确的参数
            imap_service.connection.search.assert_called_once()