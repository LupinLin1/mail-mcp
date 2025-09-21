"""
连接池管理模块
为IMAP和SMTP连接提供池化管理，提高性能和资源利用率
"""

import asyncio
import imaplib
import smtplib
import socket
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from .config import Config
from .errors import (
    NetworkError,
    AuthenticationError,
    logger,
    log_error_with_context
)


@dataclass
class ConnectionInfo:
    """连接信息"""
    connection: Union[imaplib.IMAP4, smtplib.SMTP]
    created_at: datetime
    last_used: datetime
    is_healthy: bool = True
    connection_type: str = "unknown"  # "imap" or "smtp"


class ConnectionPool:
    """连接池管理器"""
    
    def __init__(
        self,
        config: Config,
        max_imap_connections: int = 3,
        max_smtp_connections: int = 2,
        connection_timeout: int = 300,  # 5分钟超时
        health_check_interval: int = 60  # 1分钟健康检查
    ):
        self.config = config
        self.max_imap_connections = max_imap_connections
        self.max_smtp_connections = max_smtp_connections
        self.connection_timeout = connection_timeout
        self.health_check_interval = health_check_interval
        
        # 连接池
        self.imap_pool: asyncio.Queue = asyncio.Queue(maxsize=max_imap_connections)
        self.smtp_pool: asyncio.Queue = asyncio.Queue(maxsize=max_smtp_connections)
        
        # 信号量控制并发
        self.imap_semaphore = asyncio.Semaphore(max_imap_connections)
        self.smtp_semaphore = asyncio.Semaphore(max_smtp_connections)
        
        # 连接统计
        self.stats = {
            'imap_created': 0,
            'imap_reused': 0,
            'imap_expired': 0,
            'smtp_created': 0,
            'smtp_reused': 0,
            'smtp_expired': 0,
            'health_checks': 0,
            'failed_health_checks': 0
        }
        
        # 健康检查任务
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        logger.info(f"连接池初始化 - IMAP: {max_imap_connections}, SMTP: {max_smtp_connections}")
    
    async def start(self):
        """启动连接池"""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("连接池健康检查任务已启动")
    
    async def stop(self):
        """停止连接池"""
        self._shutdown = True
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有连接
        await self._close_all_connections()
        logger.info("连接池已停止")
    
    async def acquire_imap_connection(self) -> imaplib.IMAP4:
        """获取IMAP连接"""
        async with self.imap_semaphore:
            try:
                # 尝试从池中获取可用连接
                if not self.imap_pool.empty():
                    conn_info = await asyncio.wait_for(self.imap_pool.get(), timeout=1.0)
                    
                    # 检查连接是否仍然有效
                    if self._is_connection_valid(conn_info):
                        conn_info.last_used = datetime.now()
                        self.stats['imap_reused'] += 1
                        logger.debug("重用IMAP连接")
                        return conn_info.connection
                    else:
                        # 连接已失效，关闭它
                        await self._close_connection(conn_info)
                        self.stats['imap_expired'] += 1
                
                # 创建新连接
                connection = await self._create_imap_connection()
                self.stats['imap_created'] += 1
                logger.debug("创建新IMAP连接")
                return connection
                
            except asyncio.TimeoutError:
                # 创建新连接
                connection = await self._create_imap_connection()
                self.stats['imap_created'] += 1
                logger.debug("超时后创建新IMAP连接")
                return connection
            except Exception as e:
                log_error_with_context(e, context={"operation": "acquire_imap_connection"})
                raise NetworkError(
                    "获取IMAP连接失败",
                    details={"pool_size": self.imap_pool.qsize()},
                    original_exception=e
                )
    
    async def release_imap_connection(self, connection: imaplib.IMAP4):
        """释放IMAP连接回池中"""
        try:
            if not self._shutdown and self._is_connection_healthy(connection, "imap"):
                conn_info = ConnectionInfo(
                    connection=connection,
                    created_at=datetime.now(),
                    last_used=datetime.now(),
                    connection_type="imap"
                )
                
                try:
                    self.imap_pool.put_nowait(conn_info)
                    logger.debug("IMAP连接已归还到池中")
                except asyncio.QueueFull:
                    # 池已满，关闭连接
                    await self._close_connection(conn_info)
                    logger.debug("IMAP连接池已满，关闭连接")
            else:
                # 连接不健康或正在关闭，直接关闭
                try:
                    connection.logout()
                except (imaplib.IMAP4.error, OSError):
                    pass
                logger.debug("IMAP连接不健康，已关闭")
                
        except Exception as e:
            log_error_with_context(e, context={"operation": "release_imap_connection"})
    
    async def acquire_smtp_connection(self) -> smtplib.SMTP:
        """获取SMTP连接"""
        async with self.smtp_semaphore:
            try:
                # 尝试从池中获取可用连接
                if not self.smtp_pool.empty():
                    conn_info = await asyncio.wait_for(self.smtp_pool.get(), timeout=1.0)
                    
                    # 检查连接是否仍然有效
                    if self._is_connection_valid(conn_info):
                        conn_info.last_used = datetime.now()
                        self.stats['smtp_reused'] += 1
                        logger.debug("重用SMTP连接")
                        return conn_info.connection
                    else:
                        # 连接已失效，关闭它
                        await self._close_connection(conn_info)
                        self.stats['smtp_expired'] += 1
                
                # 创建新连接
                connection = await self._create_smtp_connection()
                self.stats['smtp_created'] += 1
                logger.debug("创建新SMTP连接")
                return connection
                
            except asyncio.TimeoutError:
                # 创建新连接
                connection = await self._create_smtp_connection()
                self.stats['smtp_created'] += 1
                logger.debug("超时后创建新SMTP连接")
                return connection
            except Exception as e:
                log_error_with_context(e, context={"operation": "acquire_smtp_connection"})
                raise NetworkError(
                    "获取SMTP连接失败",
                    details={"pool_size": self.smtp_pool.qsize()},
                    original_exception=e
                )
    
    async def release_smtp_connection(self, connection: smtplib.SMTP):
        """释放SMTP连接回池中"""
        try:
            if not self._shutdown and self._is_connection_healthy(connection, "smtp"):
                conn_info = ConnectionInfo(
                    connection=connection,
                    created_at=datetime.now(),
                    last_used=datetime.now(),
                    connection_type="smtp"
                )
                
                try:
                    self.smtp_pool.put_nowait(conn_info)
                    logger.debug("SMTP连接已归还到池中")
                except asyncio.QueueFull:
                    # 池已满，关闭连接
                    await self._close_connection(conn_info)
                    logger.debug("SMTP连接池已满，关闭连接")
            else:
                # 连接不健康或正在关闭，直接关闭
                try:
                    connection.quit()
                except (smtplib.SMTPException, OSError):
                    pass
                logger.debug("SMTP连接不健康，已关闭")
                
        except Exception as e:
            log_error_with_context(e, context={"operation": "release_smtp_connection"})
    
    async def _create_imap_connection(self) -> imaplib.IMAP4:
        """创建新的IMAP连接"""
        try:
            if self.config.imap.use_ssl:
                connection = imaplib.IMAP4_SSL(
                    host=self.config.imap.host,
                    port=self.config.imap.port
                )
            else:
                connection = imaplib.IMAP4(
                    host=self.config.imap.host,
                    port=self.config.imap.port
                )
            
            # 登录
            connection.login(self.config.imap.username, self.config.imap.password)
            
            return connection
            
        except imaplib.IMAP4.error as e:
            raise AuthenticationError(
                f"IMAP认证失败: {str(e)}",
                details={
                    "host": self.config.imap.host,
                    "port": self.config.imap.port,
                    "username": self.config.imap.username
                },
                original_exception=e
            )
        except socket.error as e:
            raise NetworkError(
                f"IMAP网络连接失败: {str(e)}",
                details={
                    "host": self.config.imap.host,
                    "port": self.config.imap.port
                },
                original_exception=e
            )
    
    async def _create_smtp_connection(self) -> smtplib.SMTP:
        """创建新的SMTP连接"""
        try:
            if self.config.smtp.use_ssl:
                connection = smtplib.SMTP_SSL(
                    host=self.config.smtp.host,
                    port=self.config.smtp.port
                )
            else:
                connection = smtplib.SMTP(
                    host=self.config.smtp.host,
                    port=self.config.smtp.port
                )
                if self.config.smtp.port == 587:  # STARTTLS
                    connection.starttls()
            
            # 登录
            connection.login(self.config.smtp.username, self.config.smtp.password)
            
            return connection
            
        except smtplib.SMTPAuthenticationError as e:
            raise AuthenticationError(
                f"SMTP认证失败: {str(e)}",
                details={
                    "host": self.config.smtp.host,
                    "port": self.config.smtp.port,
                    "username": self.config.smtp.username
                },
                original_exception=e
            )
        except socket.error as e:
            raise NetworkError(
                f"SMTP网络连接失败: {str(e)}",
                details={
                    "host": self.config.smtp.host,
                    "port": self.config.smtp.port
                },
                original_exception=e
            )
    
    def _is_connection_valid(self, conn_info: ConnectionInfo) -> bool:
        """检查连接是否仍然有效"""
        # 检查连接年龄
        age = datetime.now() - conn_info.created_at
        if age.total_seconds() > self.connection_timeout:
            return False
        
        # 检查连接健康状态
        return conn_info.is_healthy and self._is_connection_healthy(
            conn_info.connection, 
            conn_info.connection_type
        )
    
    def _is_connection_healthy(self, connection: Union[imaplib.IMAP4, smtplib.SMTP], conn_type: str) -> bool:
        """检查连接是否健康"""
        try:
            if conn_type == "imap":
                # IMAP健康检查
                connection.noop()
                return True
            elif conn_type == "smtp":
                # SMTP健康检查
                connection.noop()
                return True
            return False
        except (imaplib.IMAP4.error, smtplib.SMTPException, OSError):
            return False
    
    async def _close_connection(self, conn_info: ConnectionInfo):
        """关闭单个连接"""
        try:
            if conn_info.connection_type == "imap":
                conn_info.connection.logout()
            elif conn_info.connection_type == "smtp":
                conn_info.connection.quit()
        except (imaplib.IMAP4.error, smtplib.SMTPException, OSError):
            pass  # 忽略关闭时的错误
    
    async def _close_all_connections(self):
        """关闭所有连接"""
        # 关闭IMAP连接
        while not self.imap_pool.empty():
            try:
                conn_info = self.imap_pool.get_nowait()
                await self._close_connection(conn_info)
            except asyncio.QueueEmpty:
                break
        
        # 关闭SMTP连接
        while not self.smtp_pool.empty():
            try:
                conn_info = self.smtp_pool.get_nowait()
                await self._close_connection(conn_info)
            except asyncio.QueueEmpty:
                break
    
    async def _health_check_loop(self):
        """定期健康检查循环"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error_with_context(e, context={"operation": "health_check_loop"})
    
    async def _perform_health_check(self):
        """执行健康检查"""
        self.stats['health_checks'] += 1
        
        # 检查IMAP连接池
        healthy_imap = []
        while not self.imap_pool.empty():
            try:
                conn_info = self.imap_pool.get_nowait()
                if self._is_connection_valid(conn_info):
                    healthy_imap.append(conn_info)
                else:
                    await self._close_connection(conn_info)
                    self.stats['failed_health_checks'] += 1
            except asyncio.QueueEmpty:
                break
        
        # 将健康的连接放回池中
        for conn_info in healthy_imap:
            try:
                self.imap_pool.put_nowait(conn_info)
            except asyncio.QueueFull:
                await self._close_connection(conn_info)
        
        # 检查SMTP连接池
        healthy_smtp = []
        while not self.smtp_pool.empty():
            try:
                conn_info = self.smtp_pool.get_nowait()
                if self._is_connection_valid(conn_info):
                    healthy_smtp.append(conn_info)
                else:
                    await self._close_connection(conn_info)
                    self.stats['failed_health_checks'] += 1
            except asyncio.QueueEmpty:
                break
        
        # 将健康的连接放回池中
        for conn_info in healthy_smtp:
            try:
                self.smtp_pool.put_nowait(conn_info)
            except asyncio.QueueFull:
                await self._close_connection(conn_info)
        
        logger.debug(f"健康检查完成 - IMAP: {len(healthy_imap)}, SMTP: {len(healthy_smtp)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        return {
            **self.stats,
            'imap_pool_size': self.imap_pool.qsize(),
            'smtp_pool_size': self.smtp_pool.qsize(),
            'imap_max_connections': self.max_imap_connections,
            'smtp_max_connections': self.max_smtp_connections,
            'connection_timeout': self.connection_timeout,
            'health_check_interval': self.health_check_interval
        }