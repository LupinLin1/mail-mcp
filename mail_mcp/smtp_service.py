"""
SMTP service implementation for Mail MCP server
"""

import smtplib
import ssl
import socket
import os
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .imap_service import IMAPService
from datetime import datetime

from .config import Config
from .models import EmailMessage, EmailAttachment
from .utils import validate_email_address
from .errors import (
    SMTPError,
    EmailReplyError,
    NetworkError,
    ValidationError,
    FileSystemError,
    retry_on_error,
    handle_errors,
    logger
)
from .performance import timer, get_global_monitor


class SMTPService:
    """SMTP service for sending emails"""

    # 附件大小限制（25MB）
    MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25MB in bytes

    def __init__(self, config: Config, connection_pool=None):
        self.config = config
        self.connection: Optional[smtplib.SMTP] = None
        self.connected = False
        self.connection_timeout = 30
        self.last_connection_attempt: Optional[datetime] = None
        
        # 连接池和性能监控
        self.connection_pool = connection_pool
        self.performance_monitor = get_global_monitor()
        
        # 如果使用连接池，则禁用直接连接管理
        self.use_connection_pool = connection_pool is not None
        self.connection_stats = {
            'total_connections': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'last_error': None
        }

    async def connect(self) -> bool:
        """Connect to SMTP server with enhanced error handling"""
        self.connection_stats['total_connections'] += 1
        self.last_connection_attempt = datetime.now()

        try:
            # Create SSL context for secure connections
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # For compatibility with self-signed certs

            if self.config.smtp.use_ssl:
                # Use SMTP_SSL for SSL connections
                self.connection = smtplib.SMTP_SSL(
                    self.config.smtp.host,
                    self.config.smtp.port,
                    timeout=self.connection_timeout,
                    context=context
                )
            else:
                # Use regular SMTP with STARTTLS
                self.connection = smtplib.SMTP(
                    self.config.smtp.host,
                    self.config.smtp.port,
                    timeout=self.connection_timeout
                )

                # Send EHLO and start TLS
                self.connection.ehlo()
                self.connection.starttls(context=context)
                self.connection.ehlo()

            # Authenticate
            try:
                self.connection.login(self.config.smtp.username, self.config.smtp.password)
            except smtplib.SMTPAuthenticationError as e:
                self.connection_stats['last_error'] = f"Authentication failed: {str(e)}"
                self.connection_stats['failed_connections'] += 1
                print(f"SMTP authentication failed: {e}")
                await self.disconnect()
                return False

            # Test connection with NOOP command
            self.connection.noop()

            self.connected = True
            self.connection_stats['successful_connections'] += 1
            self.connection_stats['last_error'] = None
            print(f"SMTP connection established successfully to {self.config.smtp.host}:{self.config.smtp.port}")
            return True

        except smtplib.SMTPConnectError as e:
            error_msg = f"Connection failed: {str(e)}"
            self.connection_stats['last_error'] = error_msg
            self.connection_stats['failed_connections'] += 1
            print(error_msg)
            self.connected = False
            return False

        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"Server disconnected: {str(e)}"
            self.connection_stats['last_error'] = error_msg
            self.connection_stats['failed_connections'] += 1
            print(error_msg)
            self.connected = False
            return False

        except socket.timeout as e:
            error_msg = f"Connection timeout: {str(e)}"
            self.connection_stats['last_error'] = error_msg
            self.connection_stats['failed_connections'] += 1
            print(error_msg)
            self.connected = False
            return False

        except socket.gaierror as e:
            error_msg = f"DNS resolution failed: {str(e)}"
            self.connection_stats['last_error'] = error_msg
            self.connection_stats['failed_connections'] += 1
            print(error_msg)
            self.connected = False
            return False

        except Exception as e:
            error_msg = f"Unexpected SMTP error: {str(e)}"
            self.connection_stats['last_error'] = error_msg
            self.connection_stats['failed_connections'] += 1
            print(error_msg)
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from SMTP server"""
        if self.connection and self.connected:
            try:
                self.connection.quit()
            except Exception:
                pass
            finally:
                self.connection = None
                self.connected = False

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[EmailAttachment]] = None
    ) -> bool:
        """Send email"""
        if not validate_email_address(to):
            print(f"Invalid email address: {to}")
            return False

        if not self.connected:
            if not await self.connect():
                return False

        try:
            # Create message
            if attachments:
                msg = MIMEMultipart()
            else:
                msg = MIMEText(html_body or body, 'html' if html_body else 'plain')

            # Set headers
            msg['Subject'] = subject
            msg['From'] = self.config.smtp.username
            msg['To'] = to

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Add body
            if attachments:
                msg.attach(MIMEText(html_body or body, 'html' if html_body else 'plain'))

            # Add attachments
            if attachments:
                for attachment in attachments:
                    if attachment.content:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.content)
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{attachment.filename}"'
                        )
                        msg.attach(part)

            # Send email
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            self.connection.sendmail(self.config.smtp.username, recipients, msg.as_string())
            return True

        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    async def send_email_message(self, message: EmailMessage) -> bool:
        """Send EmailMessage object"""
        return await self.send_email(
            to=message.to_addresses[0] if message.to_addresses else "",
            subject=message.subject,
            body=message.body_text,
            html_body=message.body_html,
            cc=message.cc_addresses,
            attachments=message.attachments
        )

    async def test_connection(self) -> bool:
        """Test SMTP connection"""
        if not self.connected:
            return await self.connect()
        return self.connected

    async def authenticate(self) -> bool:
        """Authenticate with SMTP server"""
        if not self.connection:
            if not await self.connect():
                return False

        try:
            # Re-authenticate (some servers require this)
            self.connection.login(self.config.smtp.username, self.config.smtp.password)
            print("SMTP re-authentication successful")
            return True
        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP authentication failed: {e}")
            return False
        except Exception as e:
            print(f"SMTP authentication error: {e}")
            return False

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        stats = self.connection_stats.copy()
        stats['connected'] = self.connected
        stats['last_connection_attempt'] = self.last_connection_attempt.isoformat() if self.last_connection_attempt else None
        stats['success_rate'] = (
            stats['successful_connections'] / stats['total_connections'] * 100
            if stats['total_connections'] > 0 else 0
        )
        return stats

    def is_connection_healthy(self) -> bool:
        """Check if connection is healthy"""
        if not self.connected or not self.connection:
            return False

        try:
            # Send NOOP command to test connection
            self.connection.noop()
            return True
        except Exception:
            self.connected = False
            return False

    async def ensure_connection(self) -> bool:
        """Ensure we have a healthy connection, reconnect if necessary"""
        if self.is_connection_healthy():
            return True

        # Disconnect first to clean up
        await self.disconnect()

        # Try to connect
        return await self.connect()

    def _validate_attachment_file(self, file_path: str) -> Dict[str, Any]:
        """
        验证附件文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 包含验证结果和文件信息的字典
        """
        if not os.path.exists(file_path):
            return {
                'valid': False,
                'error': f'文件不存在: {file_path}'
            }

        if not os.path.isfile(file_path):
            return {
                'valid': False,
                'error': f'不是有效文件: {file_path}'
            }

        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_ATTACHMENT_SIZE:
            return {
                'valid': False,
                'error': f'文件大小超过限制 ({file_size} > {self.MAX_ATTACHMENT_SIZE} bytes): {file_path}'
            }

        return {
            'valid': True,
            'file_size': file_size,
            'file_path': file_path
        }

    def _create_attachment_from_file(self, file_path: str) -> Optional[MIMEBase]:
        """
        从文件路径创建MIME附件对象
        
        Args:
            file_path: 文件路径
            
        Returns:
            MIMEBase: 附件对象，如果失败则返回None
        """
        # 验证文件
        validation = self._validate_attachment_file(file_path)
        if not validation['valid']:
            print(f"附件验证失败: {validation['error']}")
            return None

        try:
            # 获取文件名
            filename = os.path.basename(file_path)

            # 猜测MIME类型
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'

            # 创建附件对象
            maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')
            attachment = MIMEBase(maintype, subtype)

            # 读取文件内容
            with open(file_path, 'rb') as file:
                attachment.set_payload(file.read())

            # Base64编码
            encoders.encode_base64(attachment)

            # 设置Content-Disposition头
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )

            return attachment

        except Exception as e:
            print(f"创建附件失败 {file_path}: {e}")
            return None

    async def send_email_with_attachments(
        self,
        to: str,
        subject: str,
        body_text: str,
        attachments: List[str],
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        发送带附件的邮件
        
        Args:
            to: 收件人邮箱地址
            subject: 邮件主题
            body_text: 邮件正文（纯文本）
            attachments: 附件文件路径列表
            body_html: 邮件正文（HTML格式，可选）
            cc: 抄送列表（可选）
            bcc: 密送列表（可选）
            
        Returns:
            Dict: 发送结果
        """
        if not validate_email_address(to):
            return {
                'success': False,
                'error': f'无效的收件人邮箱地址: {to}'
            }

        if not attachments:
            return {
                'success': False,
                'error': '必须提供至少一个附件文件'
            }

        # 验证所有附件文件
        invalid_files = []
        valid_attachments = []
        total_size = 0

        for file_path in attachments:
            validation = self._validate_attachment_file(file_path)
            if validation['valid']:
                valid_attachments.append(file_path)
                total_size += validation['file_size']
            else:
                invalid_files.append(validation['error'])

        if invalid_files:
            return {
                'success': False,
                'error': f'附件文件验证失败: {"; ".join(invalid_files)}'
            }

        # 检查连接
        if not self.connected:
            if not await self.connect():
                return {
                    'success': False,
                    'error': '无法连接到SMTP服务器'
                }

        try:
            # 创建多部分邮件
            msg = MIMEMultipart()

            # 设置邮件头
            msg['Subject'] = subject
            msg['From'] = self.config.smtp.username
            msg['To'] = to

            if cc:
                msg['Cc'] = ', '.join(cc)

            # 添加邮件正文
            if body_html:
                # 优先使用HTML正文，同时包含纯文本版本
                msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
                msg.attach(MIMEText(body_html, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

            # 添加附件
            attachment_parts = []
            for file_path in valid_attachments:
                attachment = self._create_attachment_from_file(file_path)
                if attachment:
                    msg.attach(attachment)
                    attachment_parts.append(os.path.basename(file_path))
                else:
                    return {
                        'success': False,
                        'error': f'无法创建附件: {file_path}'
                    }

            # 发送邮件
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            self.connection.sendmail(self.config.smtp.username, recipients, msg.as_string())

            print(f"邮件发送成功，包含 {len(attachment_parts)} 个附件")
            return {
                'success': True,
                'message': f'邮件发送成功到 {to}',
                'attachments': attachment_parts,
                'total_size': total_size,
                'recipient_count': len(recipients)
            }

        except Exception as e:
            error_msg = f'发送邮件失败: {str(e)}'
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @timer("smtp.reply_to_message", get_global_monitor())
    @retry_on_error(
        max_retries=2,
        delay=1.0,
        backoff_factor=1.5,
        exceptions=(SMTPError, NetworkError, smtplib.SMTPException, socket.error)
    )
    @handle_errors()
    async def reply_to_message(
        self,
        imap_service: 'IMAPService',
        message_id: str,
        body: str,
        subject: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        回复指定的邮件
        
        Args:
            imap_service: IMAP服务实例，用于获取原邮件和标记已读状态
            message_id: 原邮件的ID
            body: 回复邮件的正文
            subject: 回复邮件的主题（可选，默认使用"Re: 原主题"）
            attachments: 附件文件路径列表（可选）
            
        Returns:
            Dict: 回复结果
            
        Raises:
            EmailReplyError: 邮件回复失败
            ValidationError: 参数验证失败
            SMTPError: SMTP操作失败
            NetworkError: 网络连接失败
            
        Note:
            成功发送回复后，会自动将原邮件标记为已读状态
        """
        logger.info(f"开始回复邮件: {message_id}")
        
        # 参数验证
        if not message_id or not message_id.strip():
            raise ValidationError(
                "邮件ID不能为空",
                details={"message_id": message_id}
            )
        
        if not body or not body.strip():
            raise ValidationError(
                "回复内容不能为空",
                details={"body_length": len(body) if body else 0}
            )
        
        try:
            # 获取原邮件
            original_msg = await imap_service.get_message(message_id)
            if not original_msg:
                raise EmailReplyError(
                    f'邮件不存在: {message_id}',
                    details={"message_id": message_id}
                )
            
            # 检查原邮件发件人地址是否有效
            if not validate_email_address(original_msg.from_address):
                raise ValidationError(
                    '原邮件发件人地址无效',
                    details={
                        "from_address": original_msg.from_address,
                        "message_id": message_id
                    }
                )
            
            # 构建回复主题
            reply_subject = subject
            if not reply_subject:
                original_subject = original_msg.subject or "无主题"
                if not original_subject.lower().startswith('re:'):
                    reply_subject = f'Re: {original_subject}'
                else:
                    reply_subject = original_subject
            
            # 检测正文格式（HTML或纯文本）
            is_html = '<' in body and '>' in body and any(tag in body.lower() for tag in ['<p>', '<div>', '<br>', '<html>', '<body>'])
            
            # 检查连接
            if not self.connected:
                connect_success = await self.connect()
                if not connect_success:
                    raise NetworkError(
                        "无法连接到SMTP服务器",
                        details={
                            "host": self.config.smtp.host,
                            "port": self.config.smtp.port,
                            "use_ssl": self.config.smtp.use_ssl
                        }
                    )
            
            # 处理附件验证
            attachment_parts = []
            if attachments:
                logger.info(f"验证 {len(attachments)} 个附件")
                # 验证所有附件文件
                invalid_files = []
                valid_attachments = []
                total_size = 0
                
                for file_path in attachments:
                    validation = self._validate_attachment_file(file_path)
                    if validation['valid']:
                        valid_attachments.append(file_path)
                        total_size += validation['file_size']
                    else:
                        invalid_files.append(validation['error'])
                
                if invalid_files:
                    raise FileSystemError(
                        '附件文件验证失败',
                        details={
                            "invalid_files": invalid_files,
                            "valid_count": len(valid_attachments),
                            "total_count": len(attachments)
                        }
                    )
                
                logger.info(f"附件验证通过，总大小: {total_size} 字节")
            
            # 创建回复邮件
            if attachments:
                msg = MIMEMultipart()
                # 添加正文
                msg.attach(MIMEText(body, 'html' if is_html else 'plain', 'utf-8'))
            else:
                msg = MIMEText(body, 'html' if is_html else 'plain', 'utf-8')
            
            # 设置邮件头
            msg['Subject'] = reply_subject
            msg['From'] = self.config.smtp.username
            msg['To'] = original_msg.from_address
            
            # 设置回复头信息
            if original_msg.message_id:
                msg['In-Reply-To'] = f'<{original_msg.message_id}>'
                msg['References'] = f'<{original_msg.message_id}>'
            
            # 处理抄送地址
            cc_addresses = []
            if original_msg.cc_addresses:
                # 过滤掉当前发送者的地址
                cc_addresses = [addr for addr in original_msg.cc_addresses 
                              if addr.lower() != self.config.smtp.username.lower()]
                if cc_addresses:
                    msg['Cc'] = ', '.join(cc_addresses)
            
            # 添加附件
            if attachments:
                for file_path in valid_attachments:
                    try:
                        attachment = self._create_attachment_from_file(file_path)
                        if attachment:
                            msg.attach(attachment)
                            attachment_parts.append(os.path.basename(file_path))
                        else:
                            raise FileSystemError(
                                '无法创建附件',
                                details={"file_path": file_path}
                            )
                    except Exception as e:
                        raise FileSystemError(
                            f'处理附件失败: {file_path}',
                            details={"file_path": file_path},
                            original_exception=e
                        )
            
            # 发送邮件
            recipients = [original_msg.from_address]
            recipients.extend(cc_addresses)
            
            try:
                self.connection.sendmail(self.config.smtp.username, recipients, msg.as_string())
                logger.info(f"回复邮件发送成功到 {original_msg.from_address}")
                
                # 自动标记原邮件为已读
                try:
                    await imap_service.mark_as_read(message_id)
                    # 清除缓存以确保下次获取的是最新状态
                    if hasattr(imap_service, 'email_cache'):
                        cache_key = f"email:INBOX:{message_id}"
                        await imap_service.email_cache.email_cache.delete(cache_key)
                    logger.info(f"已自动标记原邮件 {message_id} 为已读")
                except Exception as e:
                    logger.warning(f"自动标记原邮件为已读失败: {e}")
                    # 不影响回复的成功状态，只记录警告
                
            except smtplib.SMTPException as e:
                raise SMTPError(
                    'SMTP发送失败',
                    details={
                        "recipients": recipients,
                        "subject": reply_subject,
                        "from": self.config.smtp.username
                    },
                    original_exception=e
                )
            
            # 构建成功响应
            result = {
                'success': True,
                'message': f'回复邮件发送成功到 {original_msg.from_address}',
                'original_subject': original_msg.subject,
                'reply_subject': reply_subject,
                'recipient': original_msg.from_address,
                'sent_time': datetime.now().isoformat(),
                'body_format': 'html' if is_html else 'plain',
                'marked_as_read': True  # 表示已自动标记为已读
            }
            
            if attachment_parts:
                result['attachments'] = attachment_parts
                result['attachment_count'] = len(attachment_parts)
            
            if cc_addresses:
                result['cc_recipients'] = cc_addresses
            
            return result
            
        except (smtplib.SMTPException, socket.error) as e:
            raise SMTPError(
                f'SMTP操作失败: {str(e)}',
                details={
                    "operation": "reply_to_message",
                    "message_id": message_id,
                    "smtp_host": self.config.smtp.host
                },
                original_exception=e
            )
        except Exception:
            # 其他未预期的错误会被handle_errors装饰器处理
            raise
