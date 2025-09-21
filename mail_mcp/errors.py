"""
错误处理和日志记录模块
"""

import logging
import traceback
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import functools


class ErrorCategory(Enum):
    """错误分类枚举"""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    FILE_SYSTEM = "file_system"
    EMAIL_PARSING = "email_parsing"
    PROTOCOL = "protocol"
    UNKNOWN = "unknown"


class ErrorCode(Enum):
    """错误码枚举"""
    # 配置错误 (1000-1999)
    CONFIG_MISSING = 1001
    CONFIG_INVALID = 1002
    ENV_VAR_MISSING = 1003

    # 网络错误 (2000-2999)
    NETWORK_CONNECT_FAILED = 2001
    NETWORK_TIMEOUT = 2002
    NETWORK_DNS_FAILED = 2003
    NETWORK_CONNECTION_REFUSED = 2004

    # 认证错误 (3000-3999)
    AUTH_FAILED = 3001
    AUTH_INVALID_CREDENTIALS = 3002
    AUTH_SERVER_ERROR = 3003

    # 验证错误 (4000-4999)
    VALIDATION_INVALID_EMAIL = 4001
    VALIDATION_MISSING_PARAMETER = 4002
    VALIDATION_INVALID_PARAMETER = 4003
    VALIDATION_FILE_TOO_LARGE = 4004
    VALIDATION_FILE_NOT_FOUND = 4005
    VALIDATION_INVALID_FILE_TYPE = 4006

    # 文件系统错误 (5000-5999)
    FILE_NOT_FOUND = 5001
    FILE_PERMISSION_DENIED = 5002
    FILE_READ_ERROR = 5003
    FILE_WRITE_ERROR = 5004

    # 邮件解析错误 (6000-6999)
    EMAIL_PARSE_FAILED = 6001
    EMAIL_ENCODING_ERROR = 6002
    EMAIL_ATTACHMENT_ERROR = 6003

    # 协议错误 (7000-7999)
    PROTOCOL_IMAP_ERROR = 7001
    PROTOCOL_SMTP_ERROR = 7002
    PROTOCOL_RESPONSE_ERROR = 7003

    # 未知错误 (9000-9999)
    UNKNOWN_ERROR = 9001


class MailMCPError(Exception):
    """Mail MCP 基础异常类"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.code = code
        self.category = category
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()

        # 生成完整的错误信息
        full_message = f"[{code.name}] {message}"
        if details:
            full_message += f" (Details: {details})"
        if original_exception:
            full_message += f" (Caused by: {type(original_exception).__name__}: {str(original_exception)})"

        super().__init__(full_message)


class ConfigurationError(MailMCPError):
    """配置错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.CONFIG_INVALID,
            category=ErrorCategory.CONFIGURATION,
            details=details,
            original_exception=original_exception
        )


class NetworkError(MailMCPError):
    """网络连接错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.NETWORK_CONNECT_FAILED,
            category=ErrorCategory.NETWORK,
            details=details,
            original_exception=original_exception
        )


class AuthenticationError(MailMCPError):
    """认证错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.AUTH_FAILED,
            category=ErrorCategory.AUTHENTICATION,
            details=details,
            original_exception=original_exception
        )


class ValidationError(MailMCPError):
    """验证错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_INVALID_PARAMETER,
            category=ErrorCategory.VALIDATION,
            details=details,
            original_exception=original_exception
        )


class FileSystemError(MailMCPError):
    """文件系统错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.FILE_NOT_FOUND,
            category=ErrorCategory.FILE_SYSTEM,
            details=details,
            original_exception=original_exception
        )


class EmailParsingError(MailMCPError):
    """邮件解析错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.EMAIL_PARSE_FAILED,
            category=ErrorCategory.EMAIL_PARSING,
            details=details,
            original_exception=original_exception
        )


class ProtocolError(MailMCPError):
    """协议错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.PROTOCOL_IMAP_ERROR,
            category=ErrorCategory.PROTOCOL,
            details=details,
            original_exception=original_exception
        )


class TrustedSenderError(MailMCPError):
    """可信发件人相关错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_INVALID_PARAMETER,
            category=ErrorCategory.VALIDATION,
            details=details,
            original_exception=original_exception
        )


class EmailReplyError(MailMCPError):
    """邮件回复错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.PROTOCOL_SMTP_ERROR,
            category=ErrorCategory.PROTOCOL,
            details=details,
            original_exception=original_exception
        )


class IMAPError(MailMCPError):
    """IMAP特定错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.PROTOCOL_IMAP_ERROR,
            category=ErrorCategory.PROTOCOL,
            details=details,
            original_exception=original_exception
        )


class SMTPError(MailMCPError):
    """SMTP特定错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.PROTOCOL_SMTP_ERROR,
            category=ErrorCategory.PROTOCOL,
            details=details,
            original_exception=original_exception
        )


# 错误处理装饰器
def handle_errors(default_return=None, log_errors=True):
    """错误处理装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except MailMCPError:
                # 我们的已知错误，直接抛出
                raise
            except Exception as e:
                # 未知错误，包装为MailMCPError
                error = MailMCPError(
                    message=f"Unexpected error in {func.__name__}",
                    code=ErrorCode.UNKNOWN_ERROR,
                    original_exception=e
                )
                if log_errors:
                    logger.error(f"Unhandled exception in {func.__name__}: {error}", exc_info=True)
                raise error

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except MailMCPError:
                raise
            except Exception as e:
                error = MailMCPError(
                    message=f"Unexpected error in {func.__name__}",
                    code=ErrorCode.UNKNOWN_ERROR,
                    original_exception=e
                )
                if log_errors:
                    logger.error(f"Unhandled exception in {func.__name__}: {error}", exc_info=True)
                raise error

        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 日志配置
def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """设置日志记录"""
    logger = logging.getLogger("mail_mcp")

    # 避免重复配置
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper()))

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定了日志文件）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 全局日志器
logger = setup_logging()


def log_function_call(func_name: str, args: tuple = (), kwargs: Optional[Dict] = None):
    """记录函数调用"""
    if kwargs is None:
        kwargs = {}

    # 过滤敏感信息（如密码）
    safe_kwargs = kwargs.copy()
    if 'password' in safe_kwargs:
        safe_kwargs['password'] = '***'

    logger.debug(f"Calling {func_name} with args={args}, kwargs={safe_kwargs}")


def log_error_with_context(error: Exception, context: Optional[Dict[str, Any]] = None):
    """记录错误及上下文信息"""
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.now().isoformat()
    }

    if context:
        error_info.update(context)

    if isinstance(error, MailMCPError):
        error_info.update({
            'error_code': error.code.name,
            'error_category': error.category.value,
            'details': error.details
        })

    logger.error(f"Error occurred: {error_info}", exc_info=True)
    return error_info


def create_error_response(error: Exception, include_traceback: bool = False) -> Dict[str, Any]:
    """创建标准化的错误响应"""
    if isinstance(error, MailMCPError):
        response = {
            'success': False,
            'error': {
                'code': error.code.name,
                'category': error.category.value,
                'message': error.message,
                'details': error.details
            }
        }
    else:
        response = {
            'success': False,
            'error': {
                'code': ErrorCode.UNKNOWN_ERROR.name,
                'category': ErrorCategory.UNKNOWN.value,
                'message': str(error),
                'details': {}
            }
        }

    if include_traceback:
        response['error']['traceback'] = traceback.format_exc()

    return response


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff_factor ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        import asyncio
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}: {e}")

            # 如果所有重试都失败了，抛出最后一个异常
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff_factor ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}: {e}")

            raise last_exception

        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
