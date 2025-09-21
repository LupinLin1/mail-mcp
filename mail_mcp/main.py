"""
Main entry point for the Mail MCP server
"""

import asyncio
import logging
import sys
from typing import Optional

from fastmcp import FastMCP
from dotenv import load_dotenv

from .config import Config
from .imap_service import IMAPService
from .smtp_service import SMTPService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MailMCPServer:
    """Main MCP server for email operations"""

    def __init__(self):
        self.mcp = FastMCP("Mail MCP Server")
        self.config = Config()
        self.imap_service: Optional[IMAPService] = None
        self.smtp_service: Optional[SMTPService] = None

    def setup_services(self):
        """Initialize email services"""
        if self.config.is_valid:
            try:
                self.imap_service = IMAPService(self.config)
                self.smtp_service = SMTPService(self.config)
                logger.info("Email services initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize email services: {e}")
                logger.info("Starting in limited mode - tools will return configuration errors")
                self.imap_service = None
                self.smtp_service = None
        else:
            logger.warning("Configuration validation failed - starting in limited mode")
            logger.info(f"Configuration errors: {self.config.errors}")
            self.imap_service = None
            self.smtp_service = None

    def register_tools(self):
        """Register MCP tools"""

        @self.mcp.tool()
        async def list_messages(folder: str = "INBOX", limit: int = 20) -> str:
            """List messages in specified folder (newest first)"""
            if not self.imap_service:
                return "IMAP service not initialized"

            try:
                messages = await self.imap_service.list_messages(folder, limit)
                
                if not messages:
                    return f"文件夹 {folder} 中没有邮件"
                
                result_lines = [f"📬 文件夹 {folder} 中的最新 {len(messages)} 封邮件 (最新优先):"]
                
                for i, msg in enumerate(messages, 1):
                    # 格式化日期 - msg.date 已经是字符串格式
                    if msg.date:
                        try:
                            # 尝试解析ISO格式日期字符串
                            from datetime import datetime
                            if 'T' in msg.date:
                                # ISO格式: 2024-01-01T12:34:56
                                dt = datetime.fromisoformat(msg.date.replace('Z', '+00:00'))
                                date_str = dt.strftime('%Y-%m-%d %H:%M')
                            else:
                                # 已经是格式化的字符串，直接使用
                                date_str = msg.date
                        except Exception:
                            # 如果解析失败，直接使用原始字符串
                            date_str = str(msg.date)
                    else:
                        date_str = "未知日期"
                    
                    # 显示邮件状态和基本信息
                    status_icon = "📭" if not msg.is_read else "📬"
                    from_name = msg.from_address or "未知发件人"
                    subject = msg.subject or "无主题"
                    
                    # 检查是否有附件
                    attachment_icon = ""
                    if hasattr(msg, 'attachments') and msg.attachments:
                        attachment_count = len(msg.attachments)
                        if attachment_count == 1:
                            attachment_icon = " 📎"
                        else:
                            attachment_icon = f" 📎({attachment_count})"
                    
                    # 截断过长的主题和发件人
                    if len(subject) > 50:
                        subject = subject[:47] + "..."
                    if len(from_name) > 30:
                        from_name = from_name[:27] + "..."
                    
                    result_lines.append(f"{i:2d}. {status_icon} {date_str} | {from_name} | {subject}{attachment_icon}")
                
                return "\n".join(result_lines)
                    
            except Exception as e:
                return f"获取邮件列表时发生错误: {str(e)}"

        @self.mcp.tool()
        async def get_message(message_id: str) -> str:
            """Get detailed message information by ID"""
            if not self.imap_service:
                return "IMAP service not initialized"

            try:
                message = await self.imap_service.get_message(message_id)
                if not message:
                    return f"未找到邮件 ID: {message_id}"
                
                # 格式化邮件详细信息
                if message.date:
                    try:
                        # 尝试解析ISO格式日期字符串
                        from datetime import datetime
                        if 'T' in message.date:
                            # ISO格式: 2024-01-01T12:34:56
                            dt = datetime.fromisoformat(message.date.replace('Z', '+00:00'))
                            date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            # 已经是格式化的字符串，直接使用
                            date_str = message.date
                    except Exception:
                        # 如果解析失败，直接使用原始字符串
                        date_str = str(message.date)
                else:
                    date_str = "未知日期"
                status = "📭 未读" if not message.is_read else "📬 已读"
                
                result_lines = [
                    f"📧 邮件详情 (ID: {message_id})",
                    f"├─ 状态: {status}",
                    f"├─ 日期: {date_str}",
                    f"├─ 发件人: {message.from_address or '未知'}",
                    f"├─ 收件人: {', '.join(message.to_addresses) if message.to_addresses else '未知'}",
                ]
                
                if message.cc_addresses:
                    result_lines.append(f"├─ 抄送: {', '.join(message.cc_addresses)}")
                
                result_lines.append(f"├─ 主题: {message.subject or '无主题'}")
                
                # 如果有附件，显示附件信息
                if hasattr(message, 'attachments') and message.attachments:
                    result_lines.append(f"├─ 附件: {len(message.attachments)} 个")
                    for i, attachment in enumerate(message.attachments[:3], 1):  # 最多显示前3个
                        result_lines.append(f"│  {i}. {attachment}")
                    if len(message.attachments) > 3:
                        result_lines.append(f"│  ... 还有 {len(message.attachments) - 3} 个附件")
                
                # 显示邮件内容预览
                if message.body_text:
                    # 清理HTML标签并截断
                    body_preview = message.body_text[:500] + "..." if len(message.body_text) > 500 else message.body_text
                    result_lines.append(f"└─ 内容预览:\n{body_preview}")
                
                return "\n".join(result_lines)
                    
            except Exception as e:
                return f"获取邮件详情时发生错误: {str(e)}"

        @self.mcp.tool()
        async def send_email(to: str, subject: str, body: str, html_body: Optional[str] = None) -> str:
            """Send email"""
            if not self.smtp_service:
                return "SMTP service not initialized"

            success = await self.smtp_service.send_email(to, subject, body, html_body)
            if success:
                return "Email sent successfully"
            return "Failed to send email"

        @self.mcp.tool()
        async def send_email_with_attachments(
            to: str, 
            subject: str, 
            body: str, 
            attachments: list[str],
            html_body: Optional[str] = None
        ) -> str:
            """Send email with attachments"""
            if not self.smtp_service:
                return "SMTP service not initialized"

            result = await self.smtp_service.send_email_with_attachments(
                to=to,
                subject=subject,
                body_text=body,
                attachments=attachments,
                body_html=html_body
            )
            
            if result['success']:
                return f"邮件发送成功，包含 {len(result['attachments'])} 个附件: {', '.join(result['attachments'])}"
            else:
                return f"发送失败: {result['error']}"

        @self.mcp.tool()
        async def search_messages(
            query: str,
            folder: str = "INBOX", 
            unread_only: bool = False,
            limit: int = 20
        ) -> str:
            """搜索邮件"""
            if not self.imap_service:
                return "IMAP service not initialized"

            try:
                messages = await self.imap_service.search_messages_simple(
                    query=query,
                    folder=folder,
                    unread_only=unread_only,
                    limit=limit
                )
                
                if messages:
                    result_lines = [f"找到 {len(messages)} 封匹配的邮件:"]
                    for msg in messages:
                        status = "已读" if msg.is_read else "未读"
                        result_lines.append(f"  📧 {msg.subject} - {msg.from_address} ({status})")
                    return "\n".join(result_lines)
                else:
                    return f"在文件夹 {folder} 中未找到匹配 '{query}' 的邮件"
                    
            except Exception as e:
                return f"搜索邮件时发生错误: {str(e)}"

        @self.mcp.tool()
        async def mark_as_read(message_ids: list[str]) -> str:
            """标记邮件为已读（支持批量操作）"""
            if not self.imap_service:
                return "IMAP service not initialized"

            if not message_ids:
                return "必须提供至少一个邮件ID"

            try:
                if len(message_ids) == 1:
                    # 单邮件标记
                    success = await self.imap_service.mark_as_read(message_ids[0])
                    if success:
                        return f"邮件 {message_ids[0]} 已标记为已读"
                    else:
                        return f"标记邮件 {message_ids[0]} 为已读失败"
                else:
                    # 批量标记
                    result = await self.imap_service.mark_messages_as_read(message_ids)
                    if result['success']:
                        return f"成功标记 {result['successful_count']} 封邮件为已读"
                    else:
                        return f"批量标记完成：成功 {result['successful_count']} 封，失败 {result['failed_count']} 封"
                        
            except Exception as e:
                return f"标记邮件时发生错误: {str(e)}"

        @self.mcp.tool()
        async def list_unread_messages(folder: str = "INBOX", limit: int = 20) -> str:
            """获取未读邮件列表（最新优先）"""
            if not self.imap_service:
                return "IMAP service not initialized"

            try:
                # 使用search_messages搜索未读邮件
                messages = await self.imap_service.search_messages_simple(
                    query="",
                    folder=folder,
                    unread_only=True,
                    limit=limit
                )
                
                if not messages:
                    return f"📭 文件夹 {folder} 中没有未读邮件"
                
                result_lines = [f"📭 文件夹 {folder} 中的未读邮件 ({len(messages)} 封，最新优先):"]
                
                for i, msg in enumerate(messages, 1):
                    # 格式化日期
                    if msg.date:
                        try:
                            # 尝试解析ISO格式日期字符串
                            from datetime import datetime
                            if 'T' in msg.date:
                                # ISO格式: 2024-01-01T12:34:56
                                dt = datetime.fromisoformat(msg.date.replace('Z', '+00:00'))
                                date_str = dt.strftime('%Y-%m-%d %H:%M')
                            else:
                                # 已经是格式化的字符串，直接使用
                                date_str = msg.date
                        except Exception:
                            # 如果解析失败，直接使用原始字符串
                            date_str = str(msg.date)
                    else:
                        date_str = "未知日期"
                    
                    # 显示邮件基本信息
                    from_name = msg.from_address or "未知发件人"
                    subject = msg.subject or "无主题"
                    
                    # 截断过长的主题和发件人
                    if len(subject) > 50:
                        subject = subject[:47] + "..."
                    if len(from_name) > 30:
                        from_name = from_name[:27] + "..."
                    
                    result_lines.append(f"{i:2d}. 📭 {date_str} | {from_name} | {subject}")
                
                result_lines.append(f"\n💡 提示：使用 'mark_as_read' 工具可以将邮件标记为已读")
                return "\n".join(result_lines)
                    
            except Exception as e:
                return f"获取未读邮件时发生错误: {str(e)}"

        @self.mcp.tool()
        async def list_attachments(message_id: str, folder: str = "INBOX") -> str:
            """列出指定邮件的所有附件"""
            if not self.imap_service:
                return "IMAP service not initialized"

            try:
                attachments = await self.imap_service.get_message_attachments(message_id, folder)
                
                if not attachments:
                    return f"邮件 {message_id} 没有附件"
                
                result_lines = [f"📎 邮件 {message_id} 的附件列表 ({len(attachments)} 个):"]
                
                for i, attachment in enumerate(attachments, 1):
                    filename = attachment.get('filename', '未知文件名')
                    content_type = attachment.get('content_type', '未知类型')
                    size = attachment.get('size', 0)
                    
                    # 格式化文件大小
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size/1024:.1f} KB"
                    else:
                        size_str = f"{size/(1024*1024):.1f} MB"
                    
                    result_lines.append(f"{i:2d}. 📎 {filename}")
                    result_lines.append(f"     类型: {content_type}")
                    result_lines.append(f"     大小: {size_str}")
                
                result_lines.append(f"\n💡 提示：使用 'download_attachments' 工具可以下载这些附件")
                return "\n".join(result_lines)
                
            except Exception as e:
                return f"获取附件列表时发生错误: {str(e)}"

        @self.mcp.tool()
        async def download_attachments(
            message_id: str, 
            filenames: list[str], 
            save_path: str = "./downloads",
            folder: str = "INBOX"
        ) -> str:
            """下载指定邮件的附件到本地目录"""
            import os
            
            if not self.imap_service:
                return "IMAP service not initialized"

            if not filenames:
                return "必须指定要下载的附件文件名"

            try:
                # 确保保存目录存在
                os.makedirs(save_path, exist_ok=True)
                
                downloaded = []
                failed = []
                
                for filename in filenames:
                    try:
                        # 下载附件内容
                        payload = await self.imap_service.download_attachment_payload(
                            message_id, filename, folder
                        )
                        
                        if payload:
                            # 构建文件路径
                            file_path = os.path.join(save_path, filename)
                            
                            # 写入文件
                            with open(file_path, 'wb') as f:
                                f.write(payload)
                            
                            downloaded.append(filename)
                        else:
                            failed.append(filename)
                            
                    except Exception as e:
                        print(f"Failed to download attachment '{filename}': {e}")
                        failed.append(filename)
                
                # 构建结果消息
                result_lines = [f"📎 附件下载完成 (邮件 {message_id}):"]
                
                if downloaded:
                    result_lines.append(f"✅ 成功下载 {len(downloaded)} 个附件:")
                    for filename in downloaded:
                        file_path = os.path.join(save_path, filename)
                        result_lines.append(f"   📎 {filename} -> {file_path}")
                
                if failed:
                    result_lines.append(f"❌ 下载失败 {len(failed)} 个附件:")
                    for filename in failed:
                        result_lines.append(f"   ❌ {filename}")
                
                result_lines.append(f"\n💾 保存目录: {os.path.abspath(save_path)}")
                
                return "\n".join(result_lines)
                
            except Exception as e:
                return f"下载附件时发生错误: {str(e)}"

        logger.info("MCP tools registered")

    async def run(self, host: str = "localhost", port: int = 8000):
        """Run the MCP server"""
        self.setup_services()
        self.register_tools()

        logger.info(f"Starting Mail MCP server on {host}:{port}")
        await self.mcp.run(host=host, port=port)
    
    def run_stdio(self):
        """Run the MCP server in stdio mode"""
        self.setup_services()
        self.register_tools()

        logger.info("Starting Mail MCP server in stdio mode")
        # FastMCP stdio模式 - 直接使用mcp实例
        return self.mcp.run()


async def main():
    """Main entry point"""
    server = MailMCPServer()
    await server.run()


def sync_main():
    """同步入口点，用于CLI脚本 - MCP stdio模式"""
    try:
        # 创建直接的服务器实例
        server = MailMCPServer()
        server.setup_services()
        server.register_tools()
        
        logger.info("Starting Mail MCP server in stdio mode")
        # 对于stdio模式，明确指定transport为"stdio"
        server.mcp.run(transport="stdio")
            
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sync_main()
