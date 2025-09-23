"""
Main entry point for the Mail MCP server
"""

import asyncio
import json
import logging
import sys
from typing import Optional, List
import anyio

from fastmcp import FastMCP
from dotenv import load_dotenv

from .config import Config
from .imap_service import IMAPService
from .smtp_service import SMTPService
from .models import SearchRequest
from .connection_pool import ConnectionPool

from .performance import get_global_monitor
from .errors import (
    MailMCPError,
    create_error_response,
    logger,
    log_error_with_context
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class MailMCPServer:
    """Main MCP server for email operations"""

    def __init__(self):
        self.mcp = FastMCP("Mail MCP Server")
        self.config = Config()
        self.imap_service: Optional[IMAPService] = None
        self.smtp_service: Optional[SMTPService] = None
        
        # 性能优化组件
        self.connection_pool: Optional[ConnectionPool] = None
        self.performance_monitor = get_global_monitor()

    async def setup_services(self):
        """Initialize email services with performance optimization components"""
        if self.config.is_valid:
            try:
                # 初始化性能优化组件
                self.connection_pool = ConnectionPool(
                    config=self.config,
                    max_imap_connections=3,
                    max_smtp_connections=2,
                    connection_timeout=300,  # 5分钟
                    health_check_interval=60  # 1分钟
                )
                
                # 启动性能优化组件
                await self.connection_pool.start()
                await self.performance_monitor.start()
                
                # 初始化邮件服务（传入性能优化组件）
                self.imap_service = IMAPService(
                    config=self.config, 
                    connection_pool=self.connection_pool
                )
                self.smtp_service = SMTPService(
                    config=self.config, 
                    connection_pool=self.connection_pool
                )
                
                logger.info("Email services with performance optimization initialized successfully")
                
            except Exception as e:
                logger.warning(f"Failed to initialize email services: {e}")
                logger.info("Starting in limited mode - tools will return configuration errors")
                await self._cleanup_services()
                self.imap_service = None
                self.smtp_service = None
        else:
            logger.warning("Configuration validation failed - starting in limited mode")
            logger.info(f"Configuration errors: {self.config.errors}")
            self.imap_service = None
            self.smtp_service = None
    
    async def _cleanup_services(self):
        """清理性能优化组件"""
        try:
            if self.connection_pool:
                await self.connection_pool.stop()
            if self.performance_monitor:
                await self.performance_monitor.stop()
        except Exception as e:
            logger.warning(f"Error during service cleanup: {e}")

    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小为人类可读格式"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def register_tools(self):
        """Register MCP tools for v2.0"""
        
        @self.mcp.tool()
        async def check() -> str:
            """检查可信发件人的新未读邮件"""
            logger.info("执行check工具：检查可信发件人邮件")
            
            if not self.imap_service:
                error_response = create_error_response(
                    MailMCPError('IMAP服务未初始化，请检查配置')
                )
                return json.dumps(error_response, ensure_ascii=False)
            
            try:
                trusted_senders = self.config.trusted_senders.senders
                if not trusted_senders:
                    error_response = create_error_response(
                        MailMCPError('未配置可信发件人列表，请在环境变量 TRUSTED_SENDERS 中配置')
                    )
                    return json.dumps(error_response, ensure_ascii=False)
                
                emails = await self.imap_service.check_trusted_emails(trusted_senders)
                
                result = {
                    'success': True,
                    'emails': [
                        {
                            'id': msg.id,
                            'from': msg.from_address,
                            'subject': msg.subject,
                            'body_text': msg.body_text,
                            'body_html': msg.body_html,
                            'attachments': [att.filename for att in msg.attachments] if msg.attachments else [],
                            'attachment_count': len(msg.attachments) if msg.attachments else 0,
                            'received_time': msg.date,
                            'cc_addresses': msg.cc_addresses,
                            'is_read': msg.is_read,
                            'message_id': msg.message_id
                        }
                        for msg in emails
                    ],
                    'total_count': len(emails),
                    'trusted_senders': trusted_senders
                }
                
                logger.info(f"成功检查可信邮件，找到 {len(emails)} 封邮件")
                return json.dumps(result, ensure_ascii=False, indent=2)
                
            except MailMCPError as e:
                log_error_with_context(e, context={"tool": "check", "trusted_senders": trusted_senders})
                error_response = create_error_response(e)
                return json.dumps(error_response, ensure_ascii=False)
            except Exception as e:
                logger.error(f"check工具��生未预期错误: {e}", exc_info=True)
                error_response = create_error_response(e)
                return json.dumps(error_response, ensure_ascii=False)
        
        @self.mcp.tool()
        async def reply(
            message_id: str,
            body: str,
            subject: Optional[str] = None,
            attachments: Optional[list[str]] = None
        ) -> str:
            """回复指定的邮件"""
            logger.info(f"执行reply工具：回复邮件 {message_id}")
            
            if not self.imap_service:
                error_response = create_error_response(
                    MailMCPError('IMAP服务未初始化，请检查配置')
                )
                return json.dumps(error_response, ensure_ascii=False)
            
            if not self.smtp_service:
                error_response = create_error_response(
                    MailMCPError('SMTP服务未初始化，请检查配置')
                )
                return json.dumps(error_response, ensure_ascii=False)
            
            if not message_id:
                error_response = create_error_response(
                    MailMCPError('必须提供邮件ID')
                )
                return json.dumps(error_response, ensure_ascii=False)
            
            if not body:
                error_response = create_error_response(
                    MailMCPError('回复内容不能为空')
                )
                return json.dumps(error_response, ensure_ascii=False)
            
            try:
                result = await self.smtp_service.reply_to_message(
                    imap_service=self.imap_service,
                    message_id=message_id,
                    body=body,
                    subject=subject,
                    attachments=attachments
                )
                
                logger.info(f"成功回复邮件 {message_id}")
                return json.dumps(result, ensure_ascii=False, indent=2)
                
            except MailMCPError as e:
                log_error_with_context(e, context={
                    "tool": "reply",
                    "message_id": message_id,
                    "body_length": len(body) if body else 0,
                    "has_subject": bool(subject),
                    "attachment_count": len(attachments) if attachments else 0
                })
                error_response = create_error_response(e)
                return json.dumps(error_response, ensure_ascii=False)
            except Exception as e:
                logger.error(f"reply工具发生未预期错误: {e}", exc_info=True)
                error_response = create_error_response(e)
                return json.dumps(error_response, ensure_ascii=False)
        
        @self.mcp.tool()
        async def performance_stats() -> str:
            """获取性能统计信息，包括连接池和监控指标"""
            logger.info("执行performance_stats工具：获取性能统计")
            
            try:
                stats = {
                    'timestamp': asyncio.get_event_loop().time(),
                    'server_status': 'running'
                }
                
                # 连接池统计
                if self.connection_pool:
                    stats['connection_pool'] = self.connection_pool.get_stats()
                else:
                    stats['connection_pool'] = {'status': 'not_initialized'}
                
                # 性能监控统计
                if self.performance_monitor:
                    stats['performance_monitor'] = self.performance_monitor.get_stats()
                else:
                    stats['performance_monitor'] = {'status': 'not_initialized'}
                
                # 服务状态
                stats['services'] = {
                    'imap_service': 'initialized' if self.imap_service else 'not_initialized',
                    'smtp_service': 'initialized' if self.smtp_service else 'not_initialized',
                    'config_valid': self.config.is_valid
                }
                
                logger.info("成功获取性能统计信息")
                return json.dumps(stats, ensure_ascii=False, indent=2)
                
            except Exception as e:
                logger.error(f"performance_stats工具发生错误: {e}", exc_info=True)
                error_response = create_error_response(e)
                return json.dumps(error_response, ensure_ascii=False)

        @self.mcp.tool()
        async def download_attachments(
            message_id: str, 
            filenames: Optional[List[str]] = None, 
            save_path: str = "./downloads"
        ) -> str:
            """下载邮件附件到本地目录
            
            Args:
                message_id: 邮件ID
                filenames: 要下载的附件文件名列表，如果为空则下载所有附件
                save_path: 保存路径，默认为./downloads
                
            Returns:
                JSON格式的下载结果
            """
            logger.info(f"执行download_attachments工具：下载邮件 {message_id} 的附件")
            
            if not self.imap_service:
                error_response = create_error_response(
                    MailMCPError('IMAP服务未初始化，请检查配置')
                )
                return json.dumps(error_response, ensure_ascii=False)
            
            if not message_id or not message_id.strip():
                error_response = create_error_response(
                    MailMCPError('邮件ID不能为空')
                )
                return json.dumps(error_response, ensure_ascii=False)
            
            try:
                import os
                
                # 确保保存目录存在
                os.makedirs(save_path, exist_ok=True)
                
                # 获取邮件的所有附件列表
                attachments = await self.imap_service.get_message_attachments(message_id)
                
                if not attachments:
                    result = {
                        "success": True,
                        "message": f"邮件 {message_id} 没有附件",
                        "downloaded_count": 0,
                        "attachments": []
                    }
                    return json.dumps(result, ensure_ascii=False, indent=2)
                
                # 如果指定了文件名，则只下载指定的附件
                if filenames:
                    available_filenames = [att['filename'] for att in attachments]
                    attachments_to_download = [
                        att for att in attachments 
                        if att['filename'] in filenames
                    ]
                    
                    # 检查是否有不存在的文件名
                    missing_files = [name for name in filenames if name not in available_filenames]
                    if missing_files:
                        logger.warning(f"以下附件不存在: {missing_files}")
                else:
                    attachments_to_download = attachments
                
                download_results = []
                success_count = 0
                
                for attachment in attachments_to_download:
                    filename = attachment['filename']
                    file_path = os.path.join(save_path, filename)
                    
                    try:
                        # 下载附件内容
                        payload = await self.imap_service.download_attachment_payload(
                            message_id, filename
                        )
                        
                        if payload:
                            # 处理文件名冲突
                            counter = 1
                            original_file_path = file_path
                            while os.path.exists(file_path):
                                name, ext = os.path.splitext(original_file_path)
                                file_path = f"{name}_{counter}{ext}"
                                counter += 1
                            
                            # 写入文件
                            with open(file_path, 'wb') as f:
                                f.write(payload)
                            
                            file_size = len(payload)
                            success_count += 1
                            
                            download_results.append({
                                "filename": filename,
                                "status": "success",
                                "file_path": file_path,
                                "size_bytes": file_size,
                                "size_human": self._format_file_size(file_size)
                            })
                            
                            logger.info(f"成功下载附件: {filename} -> {file_path}")
                        else:
                            download_results.append({
                                "filename": filename,
                                "status": "failed",
                                "error": "无法获取附件内容"
                            })
                            logger.warning(f"下载附件失败: {filename}")
                    
                    except Exception as e:
                        download_results.append({
                            "filename": filename,
                            "status": "failed",
                            "error": str(e)
                        })
                        logger.error(f"下载附件 {filename} 时发生错误: {e}")
                
                result = {
                    "success": True,
                    "message": f"完成下载，成功 {success_count}/{len(attachments_to_download)} 个附件",
                    "downloaded_count": success_count,
                    "total_count": len(attachments_to_download),
                    "save_path": save_path,
                    "attachments": download_results
                }
                
                if filenames and missing_files:
                    result["missing_files"] = missing_files
                
                logger.info(f"附件下载完成: {success_count}/{len(attachments_to_download)} 成功")
                return json.dumps(result, ensure_ascii=False, indent=2)
                
            except MailMCPError as e:
                log_error_with_context(e, context={
                    "tool": "download_attachments",
                    "message_id": message_id,
                    "filenames": filenames,
                    "save_path": save_path
                })
                error_response = create_error_response(e)
                return json.dumps(error_response, ensure_ascii=False)
            except Exception as e:
                logger.error(f"download_attachments工具发生未预期错误: {e}", exc_info=True)
                error_response = create_error_response(e)
                return json.dumps(error_response, ensure_ascii=False)

        @self.mcp.tool()
        async def search(
            query: str,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            page: Optional[int] = 1,
            page_size: Optional[int] = 20,
            folder: Optional[str] = "INBOX",
            sender: Optional[str] = None,
            recipient: Optional[str] = None,
            has_attachments: Optional[bool] = None
        ) -> str:
            """搜索邮件
            
            Args:
                query: 搜索关键词
                date_from: 开始日期 (YYYY-MM-DD)
                date_to: 结束日期 (YYYY-MM-DD)
                page: 页码，从1开始
                page_size: 每页结果数量
                folder: 搜索文件夹，默认为INBOX
                sender: 发件人过滤
                recipient: 收件人过滤
                has_attachments: 是否有附件过滤
                
            Returns:
                JSON格式的搜索结果
            """
            logger.info(f"执行search工具：搜索邮件，关键词: {query}")
            
            if not self.imap_service:
                error_response = create_error_response(
                    MailMCPError('IMAP服务未初始化，请检查配置')
                )
                return json.dumps(error_response, ensure_ascii=False)
            
            if not query or not query.strip():
                error_response = create_error_response(
                    MailMCPError('搜索关键词不能为空')
                )
                return json.dumps(error_response, ensure_ascii=False)
            
            try:
                # 日期格式验证
                if date_from and not self._validate_date_format(date_from):
                    error_response = create_error_response(
                        MailMCPError('��始日期格式错误，请使用 YYYY-MM-DD 格式')
                    )
                    return json.dumps(error_response, ensure_ascii=False)
                
                if date_to and not self._validate_date_format(date_to):
                    error_response = create_error_response(
                        MailMCPError('结束日期格式错误，请使用 YYYY-MM-DD 格式')
                    )
                    return json.dumps(error_response, ensure_ascii=False)
                
                # 创建搜索请求
                search_request = SearchRequest(
                    query=query.strip(),
                    date_from=date_from,
                    date_to=date_to,
                    page=page or 1,
                    page_size=page_size or 20,
                    folder=folder or "INBOX",
                    sender=sender,
                    recipient=recipient,
                    has_attachments=has_attachments
                )
                
                # 执行搜索
                search_result = await self.imap_service.search_emails(search_request)
                
                # 格式化结果
                result = {
                    'success': True,
                    'query': search_result.query,
                    'total_count': search_result.total_count,
                    'current_page': search_result.current_page,
                    'total_pages': search_result.total_pages,
                    'page_size': search_result.page_size,
                    'search_time_ms': search_result.search_time_ms,
                    'emails': [
                        {
                            'uid': email.uid,
                            'subject': email.subject,
                            'sender': email.sender,
                            'recipient': email.recipient,
                            'date': email.date,
                            'folder': email.folder,
                            'summary': email.summary,
                            'has_attachments': email.has_attachments,
                            'is_read': email.is_read,
                            'message_id': email.message_id
                        }
                        for email in search_result.emails
                    ]
                }
                
                logger.info(f"搜索完成，找到 {search_result.total_count} 条结果")
                return json.dumps(result, ensure_ascii=False, indent=2)
                
            except MailMCPError as e:
                log_error_with_context(e, context={
                    "tool": "search",
                    "query": query,
                    "date_from": date_from,
                    "date_to": date_to,
                    "page": page,
                    "page_size": page_size,
                    "folder": folder
                })
                error_response = create_error_response(e)
                return json.dumps(error_response, ensure_ascii=False)
            except Exception as e:
                logger.error(f"search工具发生未预期错误: {e}", exc_info=True)
                error_response = create_error_response(e)
                return json.dumps(error_response, ensure_ascii=False)
        
        def _validate_date_format(self, date_str: str) -> bool:
            """验证日期格式是否为 YYYY-MM-DD"""
            try:
                from datetime import datetime
                datetime.strptime(date_str, '%Y-%m-%d')
                return True
            except ValueError:
                return False

        logger.info("V2.0 MCP tools registered: check, reply, performance_stats, download_attachments, search")

    async def run(self, host: str = "localhost", port: int = 8000):
        """Run the MCP server"""
        await self.setup_services()
        self.register_tools()

        logger.info(f"Starting Mail MCP server on {host}:{port}")
        try:
            await self.mcp.run(host=host, port=port)
        finally:
            await self._cleanup_services()
    
    async def run_stdio(self):
        """Run the MCP server in stdio mode"""
        await self.setup_services()
        self.register_tools()

        logger.info("Starting Mail MCP server in stdio mode")
        try:
            # FastMCP stdio模式 - 直接使用mcp实例
            return self.mcp.run()
        finally:
            await self._cleanup_services()


async def main():
    """Main entry point"""
    server = MailMCPServer()
    await server.run()


def sync_main():
    """同步入口点，用于CLI脚本 - MCP stdio模式"""
    try:
        # 创建直接的服务器实例
        server = MailMCPServer()
        
        # 同步运行async setup
        async def setup():
            await server.setup_services()
            server.register_tools()
        
        asyncio.run(setup())
        
        logger.info("Starting Mail MCP server in stdio mode")
        
        # 现在运行stdio服务器（这是同步的）
        server.mcp.run(transport="stdio")
                
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    server = MailMCPServer()
    anyio.run(server.run)