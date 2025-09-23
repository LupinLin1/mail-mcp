"""
Utility functions for Mail MCP server
"""

import base64
import re
import os
from typing import List, Optional
from email.header import decode_header
from email.utils import parsedate_to_datetime

from .errors import ValidationError, ErrorCode


def decode_email_header(header: str) -> str:
    """Decode email header that may contain encoded text"""
    if not header:
        return ""

    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(encoding or 'utf-8'))
            except (UnicodeDecodeError, LookupError):
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(str(part))

    return ''.join(decoded_parts)


def parse_email_addresses(address_string: str) -> List[str]:
    """Parse email addresses from address string"""
    if not address_string:
        return []

    # Simple email extraction - in real implementation, use email.utils
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, address_string)
    return [email.lower() for email in emails]


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def validate_email_address(email: str) -> bool:
    """Validate email address format"""
    if not email or not isinstance(email, str):
        return False

    email = email.strip()
    if len(email) > 254:  # RFC 5321 max length
        return False

    # Handle "Name <email@address.com>" format
    match = re.search(r'<(.+?)>', email)
    if match:
        email = match.group(1).strip()

    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    if not filename or not isinstance(filename, str):
        return 'attachment'

    # Remove or replace unsafe characters
    unsafe_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(unsafe_chars, '_', filename)

    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')

    # Limit length
    if len(sanitized) > 255:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]

    return sanitized or 'attachment'


def decode_base64_content(content: str) -> bytes:
    """Decode base64 encoded content"""
    try:
        return base64.b64decode(content)
    except Exception:
        return b''


def encode_base64_content(content: bytes) -> str:
    """Encode content to base64"""
    try:
        return base64.b64encode(content).decode('utf-8')
    except Exception:
        return ''


def parse_email_date(date_string: str) -> Optional[str]:
    """Parse email date to ISO format"""
    if not date_string:
        return None

    try:
        dt = parsedate_to_datetime(date_string)
        return dt.isoformat() if dt else None
    except Exception:
        return None


def validate_file_path(file_path: str, max_size_mb: int = 25) -> dict:
    """Validate file path and size"""
    if not file_path or not isinstance(file_path, str):
        raise ValidationError(
            "文件路径不能为空",
            details={"file_path": file_path, "error_code": ErrorCode.VALIDATION_INVALID_PARAMETER.name}
        )

    if not os.path.exists(file_path):
        raise ValidationError(
            f"文件不存在: {file_path}",
            details={"file_path": file_path, "error_code": ErrorCode.VALIDATION_FILE_NOT_FOUND.name}
        )

    if not os.path.isfile(file_path):
        raise ValidationError(
            f"不是有效文件: {file_path}",
            details={"file_path": file_path, "error_code": ErrorCode.VALIDATION_INVALID_FILE_TYPE.name}
        )

    # 检查文件大小
    max_size_bytes = max_size_mb * 1024 * 1024
    file_size = os.path.getsize(file_path)

    if file_size > max_size_bytes:
        raise ValidationError(
            f"文件大小超过限制 ({file_size} > {max_size_bytes} bytes)",
            details={
                "file_path": file_path,
                "file_size": file_size,
                "max_size": max_size_bytes,
                "error_code": ErrorCode.VALIDATION_FILE_TOO_LARGE.name
            }
        )

    return {
        "valid": True,
        "file_size": file_size,
        "file_path": file_path,
        "max_size": max_size_bytes
    }


def safe_string_operation(func):
    """安全字符串操作装饰器"""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if isinstance(result, str):
                return result
            return str(result) if result is not None else ""
        except Exception:
            # 返回空字符串而不是抛出异常
            return ""
    return wrapper


def truncate_string(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """安全地截断字符串"""
    if not text or not isinstance(text, str):
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def extract_email_domain(email: str) -> Optional[str]:
    """从邮箱地址提取域名"""
    if not validate_email_address(email):
        return None

    return email.split('@')[1].lower()