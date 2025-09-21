"""
测试邮件附件MCP工具
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock

from mail_mcp.main import MailMCPServer
from mail_mcp.config import Config
from mail_mcp.imap_service import IMAPService


class TestAttachmentTools:
    """测试附件相关的MCP工具"""
    
    async def get_tool(self, mail_server, tool_name):
        """获取指定名称的MCP工具"""
        tools_list = await mail_server.mcp._list_tools()
        for tool in tools_list:
            if tool.name == tool_name:
                return tool
        return None
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=Config)
        config.is_valid = True
        config.imap = Mock()
        config.imap.host = "imap.test.com"
        config.imap.port = 993
        config.imap.username = "test@test.com"
        config.imap.password = "test_password"
        config.imap.use_ssl = True
        return config
    
    @pytest.fixture
    def mock_imap_service(self, mock_config):
        """创建模拟IMAP服务"""
        service = Mock(spec=IMAPService)
        return service
    
    @pytest.fixture
    def mail_server(self, mock_config, mock_imap_service):
        """创建邮件MCP服务器实例"""
        server = MailMCPServer()
        server.config = mock_config
        server.imap_service = mock_imap_service
        server.smtp_service = Mock()  # 不需要SMTP服务
        server.register_tools()
        return server
    
    @pytest.mark.asyncio
    async def test_list_attachments_with_attachments(self, mail_server, mock_imap_service):
        """测试列出包含附件的邮件的附件列表"""
        # 模拟附件数据
        mock_attachments = [
            {
                'filename': 'document.pdf',
                'content_type': 'application/pdf',
                'size': 1024000,  # 1MB
                'part_id': 2
            },
            {
                'filename': 'image.jpg',
                'content_type': 'image/jpeg',
                'size': 512000,   # 512KB
                'part_id': 3
            }
        ]
        
        mock_imap_service.get_message_attachments.return_value = mock_attachments
        
        # 获取list_attachments工具
        list_attachments_tool = await self.get_tool(mail_server, 'list_attachments')
        assert list_attachments_tool is not None, "list_attachments tool not found"
        
        # 调用工具
        result = await list_attachments_tool.fn(message_id="123", folder="INBOX")
        
        # 验证结果
        assert "邮件 123 的附件列表 (2 个)" in result
        assert "document.pdf" in result
        assert "application/pdf" in result
        assert "1000.0 KB" in result  # 1024000 / 1024 = 1000 KB
        assert "image.jpg" in result
        assert "image/jpeg" in result
        assert "500.0 KB" in result  # 512000 / 1024 = 500 KB
        
        # 验证调用
        mock_imap_service.get_message_attachments.assert_called_once_with("123", "INBOX")
    
    @pytest.mark.asyncio
    async def test_list_attachments_no_attachments(self, mail_server, mock_imap_service):
        """测试列出不含附件的邮件"""
        mock_imap_service.get_message_attachments.return_value = []
        
        list_attachments_tool = await self.get_tool(mail_server, 'list_attachments')
        assert list_attachments_tool is not None
        
        result = await list_attachments_tool.fn(message_id="123", folder="INBOX")
        
        assert "邮件 123 没有附件" in result
        mock_imap_service.get_message_attachments.assert_called_once_with("123", "INBOX")
    
    @pytest.mark.asyncio
    async def test_list_attachments_imap_service_not_initialized(self, mail_server):
        """测试IMAP服务未初始化的情况"""
        mail_server.imap_service = None
        
        list_attachments_tool = await self.get_tool(mail_server, 'list_attachments')
        assert list_attachments_tool is not None
        
        result = await list_attachments_tool.fn(message_id="123")
        
        assert "IMAP service not initialized" in result
    
    @pytest.mark.asyncio
    async def test_list_attachments_exception_handling(self, mail_server, mock_imap_service):
        """测试列出附件时的异常处理"""
        mock_imap_service.get_message_attachments.side_effect = Exception("Network error")
        
        list_attachments_tool = await self.get_tool(mail_server, 'list_attachments')
        assert list_attachments_tool is not None
        
        result = await list_attachments_tool.fn(message_id="123")
        
        assert "获取附件列表时发生错误" in result
        assert "Network error" in result
    
    @pytest.mark.asyncio
    async def test_download_attachments_success(self, mail_server, mock_imap_service):
        """测试成功下载附件"""
        # 模拟附件内容
        mock_imap_service.download_attachment_payload.side_effect = [
            b"PDF content here",  # test.pdf
            b"JPEG content here"  # image.jpg
        ]
        
        download_attachments_tool = await self.get_tool(mail_server, 'download_attachments')
        assert download_attachments_tool is not None
        
        # 使用临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await download_attachments_tool.fn(
                message_id="123",
                filenames=["test.pdf", "image.jpg"],
                save_path=temp_dir,
                folder="INBOX"
            )
            
            # 验证结果
            assert "附件下载完成" in result
            assert "成功下载 2 个附件" in result
            assert "test.pdf" in result
            assert "image.jpg" in result
            
            # 验证文件已创建
            assert os.path.exists(os.path.join(temp_dir, "test.pdf"))
            assert os.path.exists(os.path.join(temp_dir, "image.jpg"))
            
            # 验证文件内容
            with open(os.path.join(temp_dir, "test.pdf"), "rb") as f:
                assert f.read() == b"PDF content here"
            
            with open(os.path.join(temp_dir, "image.jpg"), "rb") as f:
                assert f.read() == b"JPEG content here"
            
            # 验证调用次数
            assert mock_imap_service.download_attachment_payload.call_count == 2
    
    @pytest.mark.asyncio
    async def test_download_attachments_partial_failure(self, mail_server, mock_imap_service):
        """测试部分附件下载失败"""
        # 第一个附件成功，第二个失败
        mock_imap_service.download_attachment_payload.side_effect = [
            b"PDF content here",  # test.pdf 成功
            None                  # image.jpg 失败
        ]
        
        download_attachments_tool = await self.get_tool(mail_server, 'download_attachments')
        assert download_attachments_tool is not None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await download_attachments_tool.fn(
                message_id="123",
                filenames=["test.pdf", "image.jpg"],
                save_path=temp_dir,
                folder="INBOX"
            )
            
            # 验证结果包含成功和失败信息
            assert "成功下载 1 个附件" in result
            assert "下载失败 1 个附件" in result
            assert "test.pdf" in result
            assert "image.jpg" in result
            
            # 验证只有成功的文件被创建
            assert os.path.exists(os.path.join(temp_dir, "test.pdf"))
            assert not os.path.exists(os.path.join(temp_dir, "image.jpg"))
    
    @pytest.mark.asyncio
    async def test_download_attachments_no_filenames(self, mail_server, mock_imap_service):
        """测试下载附件时未提供文件名"""
        download_attachments_tool = await self.get_tool(mail_server, 'download_attachments')
        assert download_attachments_tool is not None
        
        result = await download_attachments_tool.fn(
            message_id="123",
            filenames=[],
            save_path="./downloads"
        )
        
        assert "必须指定要下载的附件文件名" in result
    
    @pytest.mark.asyncio
    async def test_download_attachments_imap_service_not_initialized(self, mail_server):
        """测试IMAP服务未初始化的情况"""
        mail_server.imap_service = None
        
        download_attachments_tool = await self.get_tool(mail_server, 'download_attachments')
        assert download_attachments_tool is not None
        
        result = await download_attachments_tool.fn(
            message_id="123",
            filenames=["test.pdf"]
        )
        
        assert "IMAP service not initialized" in result
    
    @pytest.mark.asyncio
    async def test_download_attachments_directory_creation(self, mail_server, mock_imap_service):
        """测试下载附件时自动创建目录"""
        mock_imap_service.download_attachment_payload.return_value = b"PDF content"
        
        download_attachments_tool = await self.get_tool(mail_server, 'download_attachments')
        assert download_attachments_tool is not None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 使用不存在的子目录
            save_path = os.path.join(temp_dir, "new_folder", "downloads")
            
            result = await download_attachments_tool.fn(
                message_id="123",
                filenames=["test.pdf"],
                save_path=save_path
            )
            
            # 验证目录被创建
            assert os.path.exists(save_path)
            assert os.path.exists(os.path.join(save_path, "test.pdf"))
            
            # 验证结果
            assert "成功下载 1 个附件" in result
    
    @pytest.mark.asyncio
    async def test_download_attachments_exception_handling(self, mail_server, mock_imap_service):
        """测试下载附件时的异常处理"""
        mock_imap_service.download_attachment_payload.side_effect = Exception("Network error")
        
        download_attachments_tool = await self.get_tool(mail_server, 'download_attachments')
        assert download_attachments_tool is not None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await download_attachments_tool.fn(
                message_id="123",
                filenames=["test.pdf"],
                save_path=temp_dir
            )
            
            assert "下载失败 1 个附件" in result
            assert "test.pdf" in result
    
    @pytest.mark.asyncio
    async def test_download_attachments_file_write_error(self, mail_server, mock_imap_service):
        """测试文件写入错误的处理"""
        mock_imap_service.download_attachment_payload.return_value = b"PDF content"
        
        download_attachments_tool = await self.get_tool(mail_server, 'download_attachments')
        assert download_attachments_tool is not None
        
        # 使用只读目录来模拟写入错误
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(readonly_dir)
            os.chmod(readonly_dir, 0o444)  # 只读权限
            
            try:
                result = await download_attachments_tool.fn(
                    message_id="123",
                    filenames=["test.pdf"],
                    save_path=readonly_dir
                )
                
                # 应该包含失败信息
                assert "下载失败 1 个附件" in result
                
            finally:
                # 恢复权限以便清理
                os.chmod(readonly_dir, 0o755)
    
    @pytest.mark.asyncio
    async def test_attachment_tools_file_size_formatting(self, mail_server, mock_imap_service):
        """测试文件大小格式化"""
        # 测试不同大小的文件
        test_cases = [
            {'size': 500, 'expected': '500 B'},
            {'size': 1536, 'expected': '1.5 KB'},  # 1.5 KB
            {'size': 2097152, 'expected': '2.0 MB'},  # 2 MB
            {'size': 1073741824, 'expected': '1024.0 MB'},  # 1 GB (显示为MB)
        ]
        
        for case in test_cases:
            mock_attachments = [{
                'filename': 'test_file.txt',
                'content_type': 'text/plain',
                'size': case['size'],
                'part_id': 1
            }]
            
            mock_imap_service.get_message_attachments.return_value = mock_attachments
            
            list_attachments_tool = await self.get_tool(mail_server, 'list_attachments')
            assert list_attachments_tool is not None
            
            result = await list_attachments_tool.fn(message_id="123")
            
            assert case['expected'] in result, f"Size {case['size']} should format to {case['expected']}"