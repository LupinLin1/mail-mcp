"""
性能监控和指标收集模块
监控系统性能，收集指标，支持性能分析和优化
"""

import asyncio
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict, deque

from .errors import logger


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags
        }


@dataclass
class TimingResult:
    """计时结果"""
    duration: float
    success: bool
    error: Optional[str] = None


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(
        self,
        collection_interval: float = 60.0,  # 1分钟收集间隔
        max_metrics: int = 10000,  # 最大指标数量
        enable_system_metrics: bool = True
    ):
        self.collection_interval = collection_interval
        self.max_metrics = max_metrics
        self.enable_system_metrics = enable_system_metrics
        
        # 指标存储
        self.metrics: deque = deque(maxlen=max_metrics)
        self.timing_stats: Dict[str, List[float]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        
        # 系统资源监控
        self.process = psutil.Process()
        
        # 监控任务
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self._lock = threading.Lock()
        
        logger.info(f"性能监控器初始化 - 收集间隔: {collection_interval}s")
    
    async def start(self):
        """启动性能监控"""
        if self._monitor_task is None and self.enable_system_metrics:
            self._monitor_task = asyncio.create_task(self._monitoring_loop())
            logger.info("性能监控任务已启动")
    
    async def stop(self):
        """停止性能监控"""
        self._shutdown = True
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("性能监控已停止")
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """记录指标"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        
        with self._lock:
            self.metrics.append(metric)
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """增加计数器"""
        with self._lock:
            self.counters[name] += value
        
        self.record_metric(f"counter.{name}", self.counters[name], tags)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """设置计量器"""
        with self._lock:
            self.gauges[name] = value
        
        self.record_metric(f"gauge.{name}", value, tags)
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """记录计时"""
        with self._lock:
            self.timing_stats[name].append(duration)
            # 只保留最近1000个记录
            if len(self.timing_stats[name]) > 1000:
                self.timing_stats[name] = self.timing_stats[name][-1000:]
        
        self.record_metric(f"timing.{name}", duration, tags)
    
    def get_timing_stats(self, name: str) -> Dict[str, float]:
        """获取计时统计"""
        with self._lock:
            timings = self.timing_stats.get(name, [])
        
        if not timings:
            return {}
        
        return {
            'count': len(timings),
            'min': min(timings),
            'max': max(timings),
            'avg': sum(timings) / len(timings),
            'p50': self._percentile(timings, 50),
            'p95': self._percentile(timings, 95),
            'p99': self._percentile(timings, 99)
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        
        return sorted_data[index]
    
    async def _monitoring_loop(self):
        """监控循环"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.collection_interval)
                await self._collect_system_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"系统指标收集出错: {e}")
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = self.process.cpu_percent()
            self.set_gauge('system.cpu_percent', cpu_percent)
            
            # 内存使用
            memory_info = self.process.memory_info()
            self.set_gauge('system.memory_rss', memory_info.rss / 1024 / 1024)  # MB
            self.set_gauge('system.memory_vms', memory_info.vms / 1024 / 1024)  # MB
            
            # 内存使用百分比
            memory_percent = self.process.memory_percent()
            self.set_gauge('system.memory_percent', memory_percent)
            
            # 线程数
            num_threads = self.process.num_threads()
            self.set_gauge('system.num_threads', num_threads)
            
            # 文件描述符数量（Unix系统）
            try:
                num_fds = self.process.num_fds()
                self.set_gauge('system.num_fds', num_fds)
            except AttributeError:
                pass  # Windows系统不支持
            
            # 网络连接数
            try:
                connections = self.process.connections()
                self.set_gauge('system.num_connections', len(connections))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            
        except Exception as e:
            logger.error(f"收集系统指标时出错: {e}")
    
    def get_recent_metrics(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """获取最近的指标"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            recent_metrics = [
                metric.to_dict()
                for metric in self.metrics
                if metric.timestamp >= cutoff_time
            ]
        
        return recent_metrics
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = {
                'total_metrics': len(self.metrics),
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'timing_stats': {
                    name: self.get_timing_stats(name)
                    for name in self.timing_stats.keys()
                }
            }
        
        return stats


def timer(name: str, monitor: PerformanceMonitor, tags: Optional[Dict[str, str]] = None):
    """计时装饰器"""
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception:
                    success = False
                    raise
                finally:
                    duration = time.time() - start_time
                    monitor.record_timing(name, duration, tags)
                    monitor.increment_counter(f"{name}.calls", tags=tags)
                    
                    if success:
                        monitor.increment_counter(f"{name}.success", tags=tags)
                    else:
                        monitor.increment_counter(f"{name}.errors", tags=tags)
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception:
                    success = False
                    raise
                finally:
                    duration = time.time() - start_time
                    monitor.record_timing(name, duration, tags)
                    monitor.increment_counter(f"{name}.calls", tags=tags)
                    
                    if success:
                        monitor.increment_counter(f"{name}.success", tags=tags)
                    else:
                        monitor.increment_counter(f"{name}.errors", tags=tags)
            
            return sync_wrapper
    
    return decorator


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests: int, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: deque = deque()
        self._lock = asyncio.Lock()
        
        logger.info(f"速率限制器初始化 - 最大请求数: {max_requests}/{time_window}s")
    
    async def acquire(self) -> bool:
        """获取请求许可"""
        async with self._lock:
            current_time = time.time()
            
            # 清理过期的请求记录
            while self.requests and (current_time - self.requests[0]) > self.time_window:
                self.requests.popleft()
            
            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                return False
            
            # 记录当前请求
            self.requests.append(current_time)
            return True
    
    async def wait_for_permit(self, timeout: Optional[float] = None) -> bool:
        """等待获取许可"""
        start_time = time.time()
        
        while True:
            if await self.acquire():
                return True
            
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            # 短暂等待后重试
            await asyncio.sleep(0.1)
    
    def get_current_usage(self) -> Dict[str, Any]:
        """获取当前使用情况"""
        current_time = time.time()
        
        # 清理过期的请求记录
        while self.requests and (current_time - self.requests[0]) > self.time_window:
            self.requests.popleft()
        
        return {
            'current_requests': len(self.requests),
            'max_requests': self.max_requests,
            'time_window': self.time_window,
            'usage_percent': (len(self.requests) / self.max_requests) * 100
        }


# 全局性能监控器实例
global_monitor = PerformanceMonitor()


def get_global_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    return global_monitor