"""
IMAP service implementation for Mail MCP server
"""

import asyncio
import imaplib
import email
from datetime import datetime
from email import policy
from typing import List, Optional, Dict, Any
import socket
import ssl

from .config import Config
from .models import EmailMessage, EmailAttachment, EmailSearchCriteria
from .utils import (
    decode_email_header,
    parse_email_addresses,
    parse_email_date
)


class IMAPService:
    """
    IMAP服务类，用于邮件收件箱操作
    
    支持安全连接、重试机制、连接池管理和完整的错误处理
    """

    def __init__(self, config: Config):
        self.config = config
        self.connection: Optional[imaplib.IMAP4_SSL] = None
        self.connected = False
        self.connection_timeout = 30
        self.max_retries = 3
        self.retry_delay = 1
        self.last_connection_attempt: Optional[datetime] = None
        self.connection_stats = {
            'total_connections': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'last_error': None,
            'connection_uptime': 0
        }
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> bool:
        """
        连接到IMAP服务器，支持重试机制和SSL连接
        
        Returns:
            bool: 连接是否成功
        """
        async with self._connection_lock:
            # 如果已经连接，直接返回True
            if self.connected and self.is_connected():
                return True
            return await self._connect_with_retry()

    async def _connect_with_retry(self) -> bool:
        """带重试机制的连接实现"""
        self.connection_stats['total_connections'] += 1
        self.last_connection_attempt = datetime.now()

        for attempt in range(self.max_retries):
            try:
                # 清理现有连接
                await self._cleanup_connection()

                # 创建SSL上下文
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE  # 兼容自签名证书

                if self.config.imap.use_ssl:
                    # 使用SSL连接
                    self.connection = imaplib.IMAP4_SSL(
                        self.config.imap.host,
                        self.config.imap.port,
                        timeout=self.connection_timeout,
                        ssl_context=context
                    )
                else:
                    # 使用普通连接（需要后续STARTTLS）
                    self.connection = imaplib.IMAP4(
                        self.config.imap.host,
                        self.config.imap.port,
                        timeout=self.connection_timeout
                    )

                    # 尝试STARTTLS
                    try:
                        self.connection.starttls(ssl_context=context)
                    except Exception:
                        # 某些服务器不支持STARTTLS，继续使用明文连接
                        pass

                # 测试连接
                self.connection.noop()

                # 认证
                success = await self._authenticate()
                if success:
                    self.connected = True
                    self.connection_stats['successful_connections'] += 1
                    self.connection_stats['last_error'] = None
                    print(f"IMAP连接成功建立: {self.config.imap.host}:{self.config.imap.port}")
                    return True

            except imaplib.IMAP4.error as e:
                error_msg = f"IMAP协议错误: {str(e)}"
                self.connection_stats['last_error'] = error_msg
                print(f"连接尝试 {attempt + 1}/{self.max_retries} 失败: {error_msg}")

            except socket.timeout as e:
                error_msg = f"连接超时: {str(e)}"
                self.connection_stats['last_error'] = error_msg
                print(f"连接尝试 {attempt + 1}/{self.max_retries} 失败: {error_msg}")

            except socket.gaierror as e:
                error_msg = f"DNS解析失败: {str(e)}"
                self.connection_stats['last_error'] = error_msg
                print(f"连接尝试 {attempt + 1}/{self.max_retries} 失败: {error_msg}")
                # DNS错误通常不需要重试
                break

            except ConnectionRefusedError as e:
                error_msg = f"连接被拒绝: {str(e)}"
                self.connection_stats['last_error'] = error_msg
                print(f"连接尝试 {attempt + 1}/{self.max_retries} 失败: {error_msg}")

            except Exception as e:
                error_msg = f"未知连接错误: {str(e)}"
                self.connection_stats['last_error'] = error_msg
                print(f"连接尝试 {attempt + 1}/{self.max_retries} 失败: {error_msg}")

            # 如果不是最后一次尝试，等待重试
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))  # 指数退避

        # 所有尝试都失败
        self.connection_stats['failed_connections'] += 1
        self.connected = False
        print(f"IMAP连接失败，已尝试 {self.max_retries} 次")
        return False

    async def _authenticate(self) -> bool:
        """
        执行IMAP认证
        
        Returns:
            bool: 认证是否成功
        """
        try:
            self.connection.login(self.config.imap.username, self.config.imap.password)
            print("IMAP认证成功")
            return True

        except imaplib.IMAP4.error as e:
            if "Authentication failed" in str(e):
                error_msg = "认证失败：用户名或密码错误"
            elif "User is authenticated but not connected" in str(e):
                error_msg = "用户已认证但连接失败"
            else:
                error_msg = f"IMAP认证错误: {str(e)}"

            self.connection_stats['last_error'] = error_msg
            print(f"认证失败: {error_msg}")
            return False

        except Exception as e:
            error_msg = f"认证过程中发生未知错误: {str(e)}"
            self.connection_stats['last_error'] = error_msg
            print(f"认证失败: {error_msg}")
            return False

    async def _cleanup_connection(self):
        """清理现有连接"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except Exception:
                pass
            finally:
                self.connection = None
                self.connected = False

    async def disconnect(self):
        """
        断开IMAP服务器连接，正确清理资源
        """
        async with self._connection_lock:
            await self._cleanup_connection()
            print("IMAP连接已断开")

    def is_connected(self) -> bool:
        """
        检查连接是否仍然活跃
        
        Returns:
            bool: 连接是否活跃
        """
        if not self.connected or not self.connection:
            return False

        try:
            # 发送NOOP命令测试连接
            self.connection.noop()
            return True
        except Exception:
            self.connected = False
            return False

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        获取连接统计信息
        
        Returns:
            Dict[str, Any]: 连接统计信息
        """
        stats = self.connection_stats.copy()
        stats['connected'] = self.connected
        stats['last_connection_attempt'] = (
            self.last_connection_attempt.isoformat() if self.last_connection_attempt else None
        )
        stats['success_rate'] = (
            stats['successful_connections'] / stats['total_connections'] * 100
            if stats['total_connections'] > 0 else 0
        )
        return stats

    async def test_connection(self) -> bool:
        """
        测试IMAP连接，如果未连接则尝试连接
        
        Returns:
            bool: 连接测试是否成功
        """
        if self.is_connected():
            return True

        return await self.connect()

    async def ensure_connection(self) -> bool:
        """
        确保有活跃的连接，如果需要则重新连接
        
        Returns:
            bool: 是否有活跃连接
        """
        if self.is_connected():
            return True

        # 断开现有连接
        await self._cleanup_connection()

        # 尝试重新连接
        return await self.connect()

    async def authenticate(self) -> bool:
        """
        重新认证（如果已连接）
        
        Returns:
            bool: 认证是否成功
        """
        if not self.connection:
            return await self.connect()

        return await self._authenticate()

    async def list_folders(self) -> List[str]:
        """List available folders"""
        if not self.connected:
            await self.connect()

        try:
            status, folder_list = self.connection.list()
            if status == 'OK':
                folders = []
                for folder_data in folder_list:
                    if isinstance(folder_data, bytes):
                        folder_data = folder_data.decode('utf-8')
                    # Extract folder name from IMAP response
                    parts = folder_data.split('"')
                    if len(parts) >= 3:
                        folders.append(parts[-2])
                return folders
        except Exception as e:
            print(f"Failed to list folders: {e}")
        return []

    async def select_folder(self, folder: str = "INBOX") -> bool:
        """Select folder"""
        if not self.connected:
            await self.connect()

        try:
            status, _ = self.connection.select(f'"{folder}"')
            return status == 'OK'
        except Exception as e:
            print(f"Failed to select folder {folder}: {e}")
            return False

    async def list_messages(self, folder: str = "INBOX", limit: int = 20, offset: int = 0) -> List[EmailMessage]:
        """List messages in folder with pagination support"""
        messages = []

        if not await self.select_folder(folder):
            return messages

        try:
            # Search for all messages
            status, message_ids = self.connection.search(None, 'ALL')
            if status != 'OK':
                return messages

            # Get message IDs (IMAP returns oldest first, so we reverse for newest first)
            msg_ids = message_ids[0].split()
            msg_ids.reverse()  # Now newest first
            total_count = len(msg_ids)

            # Apply pagination
            start_idx = offset
            end_idx = min(offset + limit, total_count)

            # Ensure indices are valid
            if start_idx >= total_count or start_idx < 0:
                return messages

            # Get the requested range of messages
            msg_ids = msg_ids[start_idx:end_idx]

            # Fetch messages
            for msg_id in msg_ids:
                message = await self._get_message_by_id(msg_id.decode(), folder)
                if message:
                    messages.append(message)

        except Exception as e:
            print(f"Failed to list messages: {e}")

        return messages

    async def get_message(self, message_id: str, folder: str = "INBOX") -> Optional[EmailMessage]:
        """Get specific message by ID"""
        if not await self.select_folder(folder):
            return None

        return await self._get_message_by_id(message_id, folder)

    async def _get_message_by_id(self, message_id: str, folder: str) -> Optional[EmailMessage]:
        """Get message by internal ID"""
        try:
            status, msg_data = self.connection.fetch(message_id, '(RFC822)')
            if status != 'OK':
                return None

            # Parse email message
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email, policy=policy.default)

            # Extract basic info
            subject = decode_email_header(email_message.get('Subject', ''))
            from_address = decode_email_header(email_message.get('From', ''))
            to_addresses = parse_email_addresses(email_message.get('To', ''))
            cc_addresses = parse_email_addresses(email_message.get('CC', ''))
            date = parse_email_date(email_message.get('Date', ''))
            message_id_header = email_message.get('Message-ID', '')

            # Get body and attachments
            body_text = ""
            body_html = None
            attachments = []

            # 首先使用iter_attachments()获取真正的附件
            try:
                for attachment_part in email_message.iter_attachments():
                    filename = attachment_part.get_filename()
                    if filename:
                        content_type = attachment_part.get_content_type()
                        # 严格过滤回复/转发邮件中的嵌入内容
                        if self._is_embedded_email_content(attachment_part, filename, content_type):
                            continue
                        
                        try:
                            payload = attachment_part.get_payload(decode=True)
                            size = len(payload) if payload else 0
                        except Exception:
                            size = 0
                        
                        attachment = EmailAttachment(
                            filename=filename,
                            content_type=content_type,
                            size=size
                        )
                        attachments.append(attachment)
            except AttributeError:
                # 如果iter_attachments()不可用，使用改进的传统方法
                pass
            
            # 提取邮件正文内容和处理fallback附件检测
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = part.get_content_disposition()

                # 提取正文内容（确保不是附件）
                if content_type == 'text/plain' and content_disposition != 'attachment':
                    body_text = part.get_content() or ""
                elif content_type == 'text/html' and content_disposition != 'attachment':
                    body_html = part.get_content()
                # 仅在iter_attachments()不可用时处理附件
                elif not hasattr(email_message, 'iter_attachments') and content_disposition == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        # 使用统一的过滤逻辑排除嵌入的邮件内容
                        if self._is_embedded_email_content(part, filename, content_type):
                            continue
                        
                        try:
                            payload = part.get_payload(decode=True)
                            size = len(payload) if payload else 0
                        except Exception:
                            size = 0
                        
                        attachment = EmailAttachment(
                            filename=filename,
                            content_type=content_type,
                            size=size
                        )
                        attachments.append(attachment)

            # Check if message is read
            flags = self.connection.fetch(message_id, '(FLAGS)')[1][0]
            is_read = b'\\Seen' in flags

            return EmailMessage(
                id=message_id,
                subject=subject,
                from_address=from_address,
                to_addresses=to_addresses,
                cc_addresses=cc_addresses,
                date=date or "",
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                is_read=is_read,
                message_id=message_id_header,
                folder=folder
            )

        except Exception as e:
            print(f"Failed to get message {message_id}: {e}")
            return None

    async def search_messages(self, criteria: EmailSearchCriteria) -> List[EmailMessage]:
        """Search messages based on criteria"""
        messages = []

        if not await self.select_folder(criteria.folder):
            return messages

        try:
            # Build search criteria
            search_terms = []

            if criteria.from_address:
                search_terms.append(f'FROM "{criteria.from_address}"')
            if criteria.to_address:
                search_terms.append(f'TO "{criteria.to_address}"')
            if criteria.subject:
                search_terms.append(f'SUBJECT "{criteria.subject}"')
            if criteria.body_text:
                search_terms.append(f'BODY "{criteria.body_text}"')
            if criteria.is_read is not None:
                search_terms.append('SEEN' if criteria.is_read else 'UNSEEN')

            # Execute search
            search_query = ' '.join(search_terms) if search_terms else 'ALL'
            # 使用UTF-8编码处理中文搜索
            status, message_ids = self.connection.search(None, search_query.encode('utf-8'))

            if status == 'OK':
                msg_ids = message_ids[0].split()
                # Limit results
                if criteria.limit > 0:
                    msg_ids = msg_ids[-criteria.limit:]

                for msg_id in msg_ids:
                    message = await self._get_message_by_id(msg_id.decode(), criteria.folder)
                    if message:
                        messages.append(message)

        except Exception as e:
            print(f"Failed to search messages: {e}")

        return messages

    async def search_messages_simple(
        self,
        query: str,
        folder: str = "INBOX",
        unread_only: bool = False,
        limit: int = 20
    ) -> List[EmailMessage]:
        """
        简化的邮件搜索接口
        
        Args:
            query: 搜索关键词（在主题、发件人、收件人、正文中搜索）
            folder: 搜索文件夹
            unread_only: 是否只搜索未读邮件
            limit: 返回结果数量限制
            
        Returns:
            List[EmailMessage]: 匹配的邮件列表
        """
        # 导入搜索条件模型
        from .models import EmailSearchCriteria
        
        # 创建搜索条件
        criteria = EmailSearchCriteria(
            folder=folder,
            subject=query if query else None,
            from_address=query if query else None,
            to_address=query if query else None,
            body_text=query if query else None,
            is_read=False if unread_only else None,
            limit=limit
        )
        
        return await self.search_messages(criteria)

    async def mark_as_read(self, message_id: str, folder: str = "INBOX") -> bool:
        """Mark message as read"""
        if not await self.select_folder(folder):
            return False

        try:
            status, _ = self.connection.store(message_id, '+FLAGS', '\\Seen')
            return status == 'OK'
        except Exception as e:
            print(f"Failed to mark message {message_id} as read: {e}")
            return False

    async def mark_messages_as_read(self, message_ids: List[str], folder: str = "INBOX") -> Dict[str, Any]:
        """
        批量标记多个邮件为已读
        
        Args:
            message_ids: 邮件ID列表
            folder: 文件夹名称
            
        Returns:
            Dict: 操作结果
        """
        if not message_ids:
            return {
                'success': False,
                'error': '必须提供至少一个邮件ID'
            }

        if not await self.select_folder(folder):
            return {
                'success': False,
                'error': f'无法选择文件夹: {folder}'
            }

        successful_ids = []
        failed_ids = []

        try:
            for message_id in message_ids:
                try:
                    status, _ = self.connection.store(message_id, '+FLAGS', '\\Seen')
                    if status == 'OK':
                        successful_ids.append(message_id)
                    else:
                        failed_ids.append(message_id)
                except Exception as e:
                    print(f"Failed to mark message {message_id} as read: {e}")
                    failed_ids.append(message_id)

            return {
                'success': len(failed_ids) == 0,
                'successful_count': len(successful_ids),
                'failed_count': len(failed_ids),
                'successful_ids': successful_ids,
                'failed_ids': failed_ids,
                'total_count': len(message_ids)
            }

        except Exception as e:
            error_msg = f"批量标记已读时发生错误: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'successful_count': 0,
                'failed_count': len(message_ids),
                'successful_ids': [],
                'failed_ids': message_ids,
                'total_count': len(message_ids)
            }

    async def delete_message(self, message_id: str, folder: str = "INBOX") -> bool:
        """Delete message"""
        if not await self.select_folder(folder):
            return False

        try:
            # Mark as deleted
            status, _ = self.connection.store(message_id, '+FLAGS', '\\Deleted')
            if status == 'OK':
                # Expunge to permanently delete
                self.connection.expunge()
                return True
        except Exception as e:
            print(f"Failed to delete message {message_id}: {e}")

        return False

    async def get_message_attachments(self, message_id: str, folder: str = "INBOX") -> List[Dict[str, Any]]:
        """
        获取邮件的附件列表，使用Python email模块的iter_attachments()方法来正确识别真正的文件附件
        
        Args:
            message_id: 邮件ID
            folder: 文件夹名称
            
        Returns:
            List[Dict]: 附件元数据列表，包含filename、content_type、size等信息
        """
        if not await self.select_folder(folder):
            return []
        
        try:
            # 获取完整的邮件MIME结构
            status, msg_data = self.connection.fetch(message_id, '(RFC822)')
            if status != 'OK':
                return []
            
            # 解析邮件
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email, policy=policy.default)
            
            attachments = []
            part_id = 0
            
            # 统一遍历所有parts来查找附件，避免重复检测
            processed_filenames = set()  # 防止重复处理同一个文件
            
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = part.get_content_disposition()
                filename = part.get_filename()
                part_id += 1
                
                # 跳过非附件的部分
                if not filename and content_disposition != 'attachment':
                    continue
                
                # 如果没有文件名但是attachment类型，为图片生成文件名
                if not filename and content_disposition == 'attachment' and content_type.startswith('image/'):
                    extension = content_type.split('/')[-1]
                    filename = f"image.{extension}"
                
                # 必须有文件名才处理
                if not filename:
                    continue
                
                # 防止重复处理同一个文件名
                if filename in processed_filenames:
                    continue
                processed_filenames.add(filename)
                
                # 检查是否是真正的附件（not embedded email content）
                if self._is_embedded_email_content(part, filename, content_type):
                    continue
                
                # 获取附件大小
                try:
                    payload = part.get_payload(decode=True)
                    size = len(payload) if payload else 0
                except Exception:
                    size = 0
                
                attachment_info = {
                    'filename': filename,
                    'content_type': content_type,
                    'size': size,
                    'part_id': part_id,
                    'content_disposition': str(part.get('Content-Disposition', ''))
                }
                attachments.append(attachment_info)
            
            return attachments
            
        except Exception as e:
            print(f"Failed to get attachments for message {message_id}: {e}")
            return []
    
    def _is_embedded_email_content(self, part, filename: str, content_type: str) -> bool:
        """
        判断附件是否为嵌入的邮件内容（如回复/转发邮件中的原邮件）
        
        Args:
            part: 邮件部分对象
            filename: 文件名
            content_type: 内容类型
            
        Returns:
            bool: True表示是嵌入邮件内容，应该过滤掉
        """
        # 检查文件名是否为.eml
        if not filename.lower().endswith('.eml'):
            return False
        
        # 检查content-type
        if content_type in ['message/rfc822', 'text/plain', 'application/octet-stream']:
            try:
                # 获取内容的前几行来检查是否包含邮件头
                payload = part.get_payload(decode=True)
                if payload:
                    content_str = payload.decode('utf-8', errors='ignore')[:500]  # 只检查前500个字符
                    
                    # 检查是否包含典型的邮件头
                    email_headers = ['Received:', 'Message-ID:', 'From:', 'To:', 'Subject:', 'Date:', 'X-QQ-']
                    header_count = sum(1 for header in email_headers if header in content_str)
                    
                    # 如果包含2个或以上的邮件头，很可能是嵌入的邮件内容
                    if header_count >= 2:
                        return True
                        
            except Exception:
                # 如果无法解码内容，检查其他特征
                pass
        
        return False

    async def download_attachment_payload(self, message_id: str, filename: str, folder: str = "INBOX") -> Optional[bytes]:
        """
        下载指定附件的内容
        
        Args:
            message_id: 邮件ID
            filename: 附件文件名
            folder: 文件夹名称
            
        Returns:
            Optional[bytes]: 附件内容的字节流，如果失败返回None
        """
        if not await self.select_folder(folder):
            return None
        
        try:
            # 重新获取邮件并解析，直接查找附件
            status, msg_data = self.connection.fetch(message_id, '(RFC822)')
            if status != 'OK':
                return None
            
            # 解析邮件
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email, policy=policy.default)
            
            # 遍历所有parts找到匹配的附件
            for part in email_message.walk():
                content_disposition = part.get_content_disposition()
                part_filename = part.get_filename()
                content_type = part.get_content_type()
                
                # 生成与get_message_attachments相同的文件名逻辑
                if not part_filename and content_disposition == 'attachment' and content_type.startswith('image/'):
                    extension = content_type.split('/')[-1]
                    part_filename = f"image.{extension}"
                
                # 找到匹配的文件名
                if part_filename == filename:
                    # 确保不是嵌入的邮件内容
                    if self._is_embedded_email_content(part, part_filename, content_type):
                        continue
                    
                    # 获取并解码附件内容
                    try:
                        payload = part.get_payload(decode=True)
                        return payload
                    except Exception as e:
                        print(f"Failed to decode attachment '{filename}': {e}")
                        return None
            
            print(f"Attachment '{filename}' not found in message {message_id}")
            return None
            
        except Exception as e:
            print(f"Failed to download attachment '{filename}' from message {message_id}: {e}")
            return None
