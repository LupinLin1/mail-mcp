"""
缓存管理模块
为邮件数据提供内存缓存，减少重复的IMAP操作
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import json
import hashlib

from .models import EmailMessage
from .errors import logger


@dataclass
class CacheEntry:
    """缓存条目"""
    data: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: Optional[float] = None  # 生存时间（秒）


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = asyncio.Lock()
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0,
            'total_requests': 0
        }
        
        logger.info(f"LRU缓存初始化 - 最大大小: {max_size}, 默认TTL: {default_ttl}s")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            self.stats['total_requests'] += 1
            
            if key not in self._cache:
                self.stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            current_time = time.time()
            
            # 检查是否过期
            if entry.ttl and (current_time - entry.created_at) > entry.ttl:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self.stats['expired'] += 1
                self.stats['misses'] += 1
                return None
            
            # 更新访问信息
            entry.last_accessed = current_time
            entry.access_count += 1
            
            # 更新访问顺序
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            self.stats['hits'] += 1
            return entry.data
    
    async def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值"""
        async with self._lock:
            current_time = time.time()
            
            # 如果键已存在，更新值
            if key in self._cache:
                self._cache[key].data = value
                self._cache[key].last_accessed = current_time
                self._cache[key].access_count += 1
                if ttl is not None:
                    self._cache[key].ttl = ttl
                
                # 更新访问顺序
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return
            
            # 检查是否需要清理空间
            if len(self._cache) >= self.max_size:
                await self._evict_oldest()
            
            # 添加新条目
            entry = CacheEntry(
                data=value,
                created_at=current_time,
                last_accessed=current_time,
                ttl=ttl or self.default_ttl
            )
            
            self._cache[key] = entry
            self._access_order.append(key)
    
    async def delete(self, key: str) -> bool:
        """删除缓存条目"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    async def clear(self) -> None:
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.info("缓存已清空")
    
    async def _evict_oldest(self) -> None:
        """清理最旧的条目"""
        if not self._access_order:
            return
        
        oldest_key = self._access_order.pop(0)
        if oldest_key in self._cache:
            del self._cache[oldest_key]
            self.stats['evictions'] += 1
    
    async def cleanup_expired(self) -> int:
        """清理过期条目"""
        expired_count = 0
        current_time = time.time()
        
        async with self._lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.ttl and (current_time - entry.created_at) > entry.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                expired_count += 1
            
            self.stats['expired'] += expired_count
        
        if expired_count > 0:
            logger.debug(f"清理了 {expired_count} 个过期缓存条目")
        
        return expired_count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        hit_rate = 0.0
        if self.stats['total_requests'] > 0:
            hit_rate = self.stats['hits'] / self.stats['total_requests'] * 100
        
        return {
            **self.stats,
            'cache_size': len(self._cache),
            'max_size': self.max_size,
            'hit_rate': round(hit_rate, 2),
            'default_ttl': self.default_ttl
        }


class EmailCache:
    """邮件缓存管理器"""
    
    def __init__(
        self,
        max_emails: int = 1000,
        max_message_content: int = 500,
        email_ttl: float = 1800,  # 30分钟
        content_ttl: float = 3600  # 1小时
    ):
        # 邮件元数据缓存
        self.email_cache = LRUCache(max_size=max_emails, default_ttl=email_ttl)
        
        # 邮件内容缓存
        self.content_cache = LRUCache(max_size=max_message_content, default_ttl=content_ttl)
        
        # 可信发件人检查结果缓存
        self.trusted_check_cache = LRUCache(max_size=100, default_ttl=300)  # 5分钟
        
        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        logger.info(f"邮件缓存初始化 - 邮件: {max_emails}, 内容: {max_message_content}")
    
    async def start(self):
        """启动缓存清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("缓存清理任务已启动")
    
    async def stop(self):
        """停止缓存管理器"""
        self._shutdown = True
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        await self.clear_all()
        logger.info("邮件缓存已停止")
    
    def _generate_email_key(self, message_id: str, folder: str = "INBOX") -> str:
        """生成邮件缓存键"""
        return f"email:{folder}:{message_id}"
    
    def _generate_content_key(self, message_id: str) -> str:
        """生成邮件内容缓存键"""
        return f"content:{message_id}"
    
    def _generate_trusted_check_key(self, trusted_senders: List[str]) -> str:
        """生成可信发件人检查缓存键"""
        # 对发件人列表进行排序和哈希以确保一致性
        sorted_senders = sorted([sender.lower().strip() for sender in trusted_senders])
        sender_hash = hashlib.md5(json.dumps(sorted_senders).encode()).hexdigest()
        return f"trusted_check:{sender_hash}"
    
    async def get_email(self, message_id: str, folder: str = "INBOX") -> Optional[EmailMessage]:
        """获取缓存的邮件"""
        key = self._generate_email_key(message_id, folder)
        cached_data = await self.email_cache.get(key)
        
        if cached_data:
            # 将字典转换回EmailMessage对象
            if isinstance(cached_data, dict):
                try:
                    return EmailMessage(**cached_data)
                except Exception as e:
                    logger.warning(f"邮件缓存数据格式错误: {e}")
                    await self.email_cache.delete(key)
            else:
                return cached_data
        
        return None
    
    async def cache_email(self, email: EmailMessage, folder: str = "INBOX", ttl: Optional[float] = None):
        """缓存邮件"""
        key = self._generate_email_key(email.id, folder)
        
        # 将EmailMessage转换为字典以便序列化
        email_dict = asdict(email)
        
        await self.email_cache.put(key, email_dict, ttl)
        logger.debug(f"邮件已缓存: {email.id}")
    
    async def get_email_content(self, message_id: str) -> Optional[str]:
        """获取缓存的邮件内容"""
        key = self._generate_content_key(message_id)
        return await self.content_cache.get(key)
    
    async def cache_email_content(self, message_id: str, content: str, ttl: Optional[float] = None):
        """缓存邮件内容"""
        key = self._generate_content_key(message_id)
        await self.content_cache.put(key, content, ttl)
        logger.debug(f"邮件内容已缓存: {message_id}")
    
    async def get_trusted_check_result(self, trusted_senders: List[str]) -> Optional[List[EmailMessage]]:
        """获取缓存的可信发件人检查结果"""
        key = self._generate_trusted_check_key(trusted_senders)
        cached_data = await self.trusted_check_cache.get(key)
        
        if cached_data:
            # 将字典列表转换回EmailMessage对象列表
            if isinstance(cached_data, list):
                try:
                    return [EmailMessage(**email_dict) for email_dict in cached_data]
                except Exception as e:
                    logger.warning(f"可信发件人检查缓存数据格式错误: {e}")
                    await self.trusted_check_cache.delete(key)
        
        return None
    
    async def cache_trusted_check_result(
        self, 
        trusted_senders: List[str], 
        emails: List[EmailMessage], 
        ttl: Optional[float] = None
    ):
        """缓存可信发件人检查结果"""
        key = self._generate_trusted_check_key(trusted_senders)
        
        # 将EmailMessage列表转换为字典列表
        email_dicts = [asdict(email) for email in emails]
        
        await self.trusted_check_cache.put(key, email_dicts, ttl)
        logger.debug(f"可信发件人检查结果已缓存: {len(emails)} 封邮件")
    
    async def invalidate_trusted_check(self, trusted_senders: List[str]):
        """无效化可信发件人检查缓存"""
        key = self._generate_trusted_check_key(trusted_senders)
        await self.trusted_check_cache.delete(key)
    
    async def clear_all(self):
        """清空所有缓存"""
        await self.email_cache.clear()
        await self.content_cache.clear()
        await self.trusted_check_cache.clear()
        logger.info("所有缓存已清空")
    
    async def _cleanup_loop(self):
        """定期清理过期缓存"""
        while not self._shutdown:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                
                email_expired = await self.email_cache.cleanup_expired()
                content_expired = await self.content_cache.cleanup_expired()
                trusted_expired = await self.trusted_check_cache.cleanup_expired()
                
                total_expired = email_expired + content_expired + trusted_expired
                if total_expired > 0:
                    logger.debug(f"缓存清理完成，清理了 {total_expired} 个过期条目")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"缓存清理任务出错: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取所有缓存统计信息"""
        return {
            'email_cache': self.email_cache.get_stats(),
            'content_cache': self.content_cache.get_stats(),
            'trusted_check_cache': self.trusted_check_cache.get_stats()
        }