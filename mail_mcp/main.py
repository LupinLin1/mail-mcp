"""
Main entry point for the Mail MCP server
"""

import asyncio
import json
import logging
import sys
from typing import Optional

from fastmcp import FastMCP
from dotenv import load_dotenv

from .config import Config
from .imap_service import IMAPService
from .smtp_service import SMTPService
from .connection_pool import ConnectionPool
from .cache import EmailCache
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
        self.email_cache: Optional[EmailCache] = None
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
                
                self.email_cache = EmailCache(
                    max_emails=1000,
                    max_message_content=500,
                    email_ttl=1800,  # 30分钟
                    content_ttl=3600  # 1小时
                )
                
                # 启动性能优化组件
                await self.connection_pool.start()
                await self.email_cache.start()
                await self.performance_monitor.start()
                
                # 初始化邮件服务（传入性能优化组件）
                self.imap_service = IMAPService(
                    config=self.config, 
                    connection_pool=self.connection_pool,
                    email_cache=self.email_cache
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
            if self.email_cache:
                await self.email_cache.stop()
            if self.performance_monitor:
                await self.performance_monitor.stop()
        except Exception as e:
            logger.warning(f"Error during service cleanup: {e}")

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
                logger.error(f"check工具发生未预期错误: {e}", exc_info=True)
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
            """获取性能统计信息，包括连接池、缓存和监控指标"""
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
                
                # 缓存统计
                if self.email_cache:
                    stats['email_cache'] = self.email_cache.get_stats()
                else:
                    stats['email_cache'] = {'status': 'not_initialized'}
                
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

        logger.info("V2.0 MCP tools registered: check, reply, performance_stats")

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
    async def async_main():
        try:
            # 创建直接的服务器实例
            server = MailMCPServer()
            await server.setup_services()
            server.register_tools()
            
            logger.info("Starting Mail MCP server in stdio mode")
            try:
                # 对于stdio模式，明确指定transport为"stdio"
                server.mcp.run(transport="stdio")
            finally:
                await server._cleanup_services()
                
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)
    
    # 运行异步主函数
    asyncio.run(async_main())


if __name__ == "__main__":
    sync_main()
