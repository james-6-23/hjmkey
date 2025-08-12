"""
扩展搜索管理器
统一管理所有扩展搜索功能
"""

import asyncio
import logging
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

from .web_searcher import WebSearcher
from .gitlab_searcher import GitLabSearcher
from .docker_searcher import DockerSearcher

logger = logging.getLogger(__name__)


class ExtendedSearchManager:
    """扩展搜索管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化管理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # 初始化搜索器
        proxy = self._get_proxy_config()
        
        self.web_searcher = WebSearcher(proxy=proxy)
        self.gitlab_searcher = GitLabSearcher(
            access_token=config.get("GITLAB_ACCESS_TOKEN"),
            proxy=proxy
        )
        self.docker_searcher = DockerSearcher()
        
        logger.info("✅ 扩展搜索管理器初始化完成")
    
    def _get_proxy_config(self) -> Dict[str, str]:
        """获取代理配置"""
        proxy_str = self.config.get("PROXY", "")
        if proxy_str:
            return {
                'http': proxy_str,
                'https': proxy_str
            }
        return None
    
    async def search_all_platforms(self, platforms: List[str]) -> Dict[str, List[str]]:
        """
        搜索所有指定平台
        
        Args:
            platforms: 平台列表 ['web', 'gitlab', 'docker']
            
        Returns:
            搜索结果字典
        """
        results = {}
        tasks = []
        
        if 'web' in platforms:
            tasks.append(self._search_web())
        
        if 'gitlab' in platforms:
            tasks.append(self._search_gitlab())
        
        if 'docker' in platforms:
            tasks.append(self._search_docker())
        
        # 并发执行所有搜索
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            platform_names = []
            if 'web' in platforms:
                platform_names.append('web')
            if 'gitlab' in platforms:
                platform_names.append('gitlab')
            if 'docker' in platforms:
                platform_names.append('docker')
            
            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    logger.error(f"搜索 {platform_names[i]} 失败: {result}")
                    results[platform_names[i]] = []
                else:
                    results[platform_names[i]] = result
        
        return results
    
    async def _search_web(self) -> List[str]:
        """搜索Web平台"""
        loop = asyncio.get_event_loop()
        
        # 在线程池中执行同步搜索
        web_results = await loop.run_in_executor(
            self.executor,
            self.web_searcher.search_all_platforms,
            20  # max_results_per_platform
        )
        
        # 合并所有平台的结果
        all_tokens = []
        for platform, tokens in web_results.items():
            all_tokens.extend(tokens)
        
        return all_tokens
    
    async def _search_gitlab(self) -> List[str]:
        """搜索GitLab"""
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self.executor,
            self.gitlab_searcher.search,
            "AIzaSy",  # query
            50  # max_results
        )
    
    async def _search_docker(self) -> List[str]:
        """搜索Docker镜像"""
        loop = asyncio.get_event_loop()
        
        # 搜索热门镜像
        popular_images = [
            "node:latest",
            "python:latest",
            "nginx:latest",
            "mysql:latest",
            "redis:latest"
        ]
        
        all_tokens = []
        for image in popular_images:
            try:
                tokens = await loop.run_in_executor(
                    self.executor,
                    self.docker_searcher.search_image,
                    image
                )
                all_tokens.extend(tokens)
            except Exception as e:
                logger.error(f"搜索Docker镜像 {image} 失败: {e}")
        
        return all_tokens
    
    def cleanup(self):
        """清理资源"""
        self.executor.shutdown(wait=False)