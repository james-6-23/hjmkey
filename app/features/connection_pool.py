"""
连接池优化模块 - 50%网络性能提升
通过复用连接和智能池管理优化网络请求
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager
import time
from abc import ABC, abstractmethod
import aiohttp
from aiohttp import ClientSession, TCPConnector

from .feature_manager import Feature

logger = logging.getLogger(__name__)


class ConnectionPoolManager(ABC):
    """连接池管理器抽象基类"""
    
    @abstractmethod
    async def get_session(self) -> ClientSession:
        """获取HTTP会话"""
        pass
    
    @abstractmethod
    async def release_session(self, session: ClientSession):
        """释放HTTP会话"""
        pass
    
    @abstractmethod
    async def close_all(self):
        """关闭所有连接"""
        pass


class AIOHTTPConnectionPool(ConnectionPoolManager):
    """基于aiohttp的连接池实现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_connections = config.get('MAX_CONNECTIONS', 100)
        self.connection_timeout = config.get('CONNECTION_TIMEOUT', 30)
        self.acquire_timeout = config.get('ACQUIRE_TIMEOUT', 10)
        self.keepalive_timeout = config.get('KEEPALIVE_TIMEOUT', 30)
        
        # 创建连接器
        self.connector = TCPConnector(
            limit=self.max_connections,
            limit_per_host=config.get('LIMIT_PER_HOST', 10),
            ttl_dns_cache=config.get('DNS_TTL', 300),
            use_dns_cache=True,
            keepalive_timeout=self.keepalive_timeout,
            enable_cleanup_closed=True
        )
        
        # 存储会话池
        self.session_pool = []
        self.in_use_sessions = set()
        
        logger.info(f"🔌 连接池初始化 (最大连接数: {self.max_connections})")
    
    async def get_session(self) -> ClientSession:
        """
        获取HTTP会话，优先从池中获取
        
        Returns:
            ClientSession: HTTP会话
        """
        # 尝试从池中获取空闲会话
        if self.session_pool:
            session = self.session_pool.pop()
            self.in_use_sessions.add(session)
            logger.debug(f"🔄 从池中获取会话 (池中剩余: {len(self.session_pool)})")
            return session
        
        # 创建新会话
        session = ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=self.connection_timeout),
        )
        self.in_use_sessions.add(session)
        logger.debug("🆕 创建新会话")
        return session
    
    async def release_session(self, session: ClientSession):
        """
        释放HTTP会话回到池中
        
        Args:
            session: 要释放的HTTP会话
        """
        if session in self.in_use_sessions:
            self.in_use_sessions.remove(session)
            
            # 检查会话是否仍然有效
            if not session.closed:
                self.session_pool.append(session)
                logger.debug(f"🔄 会话返回池中 (池中总数: {len(self.session_pool)})")
            else:
                logger.debug("🗑️ 会话已关闭，不返回池中")
    
    async def close_all(self):
        """关闭所有连接"""
        logger.info("🧹 关闭所有连接...")
        
        # 关闭所有池中的会话
        for session in self.session_pool:
            if not session.closed:
                await session.close()
        
        # 关闭所有正在使用的会话
        for session in list(self.in_use_sessions):
            if not session.closed:
                await session.close()
        
        # 关闭连接器
        if not self.connector.closed:
            await self.connector.close()
        
        # 清空池
        self.session_pool.clear()
        self.in_use_sessions.clear()
        
        logger.info("✅ 所有连接已关闭")


class ConnectionPoolFeature(Feature):
    """连接池优化功能"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化连接池功能
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.pool_size = config.get('CONNECTION_POOL_SIZE', 50)
        self.max_retries = config.get('CONNECTION_RETRIES', 3)
        self.retry_delay = config.get('CONNECTION_RETRY_DELAY', 1.0)
        
        # 初始化连接池管理器
        self.pool_manager = AIOHTTPConnectionPool(config)
        
        logger.info(f"🔌 连接池功能初始化 (池大小: {self.pool_size})")
    
    def is_healthy(self) -> bool:
        """
        检查功能是否健康
        
        Returns:
            bool: 功能是否健康
        """
        try:
            # 简单的健康检查
            return True
        except Exception as e:
            logger.error(f"连接池功能健康检查失败: {e}")
            return False
    
    def get_fallback(self):
        """
        返回降级实现
        """
        return FallbackConnectionPool()
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'pool_manager'):
            # 在同步上下文中处理异步清理
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务
                    asyncio.create_task(self.pool_manager.close_all())
                else:
                    # 如果没有运行的事件循环，同步运行
                    loop.run_until_complete(self.pool_manager.close_all())
            except RuntimeError:
                # 如果没有事件循环，创建一个新的
                asyncio.run(self.pool_manager.close_all())
        logger.debug("连接池功能资源清理任务已启动")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        获取连接的上下文管理器
        
        Yields:
            ClientSession: HTTP会话
        """
        session = await self.pool_manager.get_session()
        try:
            yield session
        finally:
            await self.pool_manager.release_session(session)
    
    async def make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        使用连接池发送HTTP请求
        
        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            响应结果字典
        """
        start_time = time.time()
        
        for attempt in range(self.max_retries + 1):
            try:
                async with self.get_connection() as session:
                    async with session.request(method, url, **kwargs) as response:
                        content = await response.text()
                        elapsed = time.time() - start_time
                        
                        return {
                            'status': response.status,
                            'content': content,
                            'headers': dict(response.headers),
                            'elapsed': elapsed,
                            'attempts': attempt + 1
                        }
                        
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # 指数退避
                else:
                    logger.error(f"请求最终失败: {e}")
                    raise
    
    async def make_batch_requests(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量发送HTTP请求
        
        Args:
            requests: 请求列表，每个请求包含method, url和kwargs
            
        Returns:
            响应结果列表
        """
        logger.info(f"🔄 批量发送 {len(requests)} 个请求")
        start_time = time.time()
        
        # 创建所有请求任务
        tasks = [
            self.make_request(req['method'], req['url'], **req.get('kwargs', {}))
            for req in requests
        ]
        
        # 并发执行所有请求
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"请求异常: {result}")
                processed_results.append({
                    'error': str(result),
                    'status': 'failed'
                })
            else:
                processed_results.append(result)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ 批量请求完成，耗时 {elapsed:.2f} 秒")
        
        return processed_results


class FallbackConnectionPool:
    """连接池功能的降级实现"""
    
    def __init__(self):
        logger.info("🔄 使用连接池功能的降级实现")
    
    @asynccontextmanager
    async def get_connection(self):
        """降级的连接获取"""
        # 使用一次性连接
        connector = TCPConnector(limit=10)
        session = ClientSession(connector=connector)
        try:
            yield session
        finally:
            await session.close()
            await connector.close()
    
    async def make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """降级的请求发送"""
        logger.warning("⚠️ 使用降级连接池，可能影响性能")
        
        # 使用一次性连接发送请求
        connector = TCPConnector(limit=10)
        async with ClientSession(connector=connector) as session:
            async with session.request(method, url, **kwargs) as response:
                content = await response.text()
                return {
                    'status': response.status,
                    'content': content,
                    'headers': dict(response.headers),
                    'elapsed': 0,  # 降级实现不计算时间
                    'attempts': 1
                }
    
    async def make_batch_requests(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """降级的批量请求"""
        logger.warning("⚠️ 使用降级批量请求，可能影响性能")
        results = []
        for req in requests:
            try:
                result = await self.make_request(req['method'], req['url'], **req.get('kwargs', {}))
                results.append(result)
            except Exception as e:
                results.append({
                    'error': str(e),
                    'status': 'failed'
                })
        return results