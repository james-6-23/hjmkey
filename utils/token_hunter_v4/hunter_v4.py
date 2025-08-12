"""
Token Hunter V4 主模块
扩展了原始 TokenHunter，添加了更多搜索平台
"""

from typing import Dict, Any, List, Optional
import logging
import sys
from pathlib import Path

# 添加父目录到路径以导入原始模块
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入原始 TokenHunter
from token_hunter.hunter import TokenHunter

# 导入扩展搜索功能
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.features.extended_search import WebSearcher, GitLabSearcher, DockerSearcher

logger = logging.getLogger(__name__)


class TokenHunterV4(TokenHunter):
    """
    Token Hunter V4 - 扩展版本
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        proxy: Optional[Dict[str, str]] = None,
        tokens_file: str = "data/github_tokens.txt",
        auto_save: bool = True
    ):
        """
        初始化 Token Hunter V4
        
        继承原始 TokenHunter 的所有功能，并添加新的搜索器
        """
        super().__init__(github_token, proxy, tokens_file, auto_save)
        
        # 添加新的搜索器
        self.web_searcher = WebSearcher(proxy)
        self.gitlab_searcher = GitLabSearcher(proxy=proxy)
        self.docker_searcher = DockerSearcher()
        
        logger.info("🎯 Token Hunter V4 初始化完成 - 支持扩展搜索")
    
    def hunt_tokens(
        self,
        mode: str = 'all',
        validate: bool = True,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        搜索tokens（V4 版本）
        
        支持的模式：
        - 'github': GitHub搜索
        - 'local': 本地搜索
        - 'web': Web平台搜索
        - 'gitlab': GitLab搜索
        - 'docker': Docker镜像搜索
        - 'extended': 所有扩展搜索（web + gitlab + docker）
        - 'all': 所有搜索
        
        Args:
            mode: 搜索模式
            validate: 是否验证找到的tokens
            max_results: 最大结果数
            
        Returns:
            搜索结果字典
        """
        # 如果是原始模式，调用父类方法
        if mode in ['github', 'local']:
            return super().hunt_tokens(mode, validate, max_results)
        
        logger.info(f"🏹 开始搜索tokens，模式: {mode}")
        
        results = {
            "mode": mode,
            "found_tokens": [],
            "valid_tokens": [],
            "invalid_tokens": [],
            "statistics": {}
        }
        
        all_tokens = set()
        
        # 扩展搜索模式
        if mode == 'web' or mode == 'extended' or mode == 'all':
            logger.info("🔍 执行Web平台搜索...")
            try:
                web_results = self.web_searcher.search_all_platforms(max_results_per_platform=20)
                web_tokens = []
                for platform, tokens in web_results.items():
                    web_tokens.extend(tokens)
                    logger.info(f"  {platform}: {len(tokens)} tokens")
                
                all_tokens.update(web_tokens)
                results["statistics"]["web_found"] = len(web_tokens)
                logger.info(f"✅ Web搜索找到 {len(web_tokens)} 个tokens")
            except Exception as e:
                logger.error(f"❌ Web搜索失败: {e}")
                results["statistics"]["web_error"] = str(e)
        
        if mode == 'gitlab' or mode == 'extended' or mode == 'all':
            logger.info("🔍 执行GitLab搜索...")
            try:
                gitlab_tokens = self.gitlab_searcher.search(max_results=max_results)
                all_tokens.update(gitlab_tokens)
                results["statistics"]["gitlab_found"] = len(gitlab_tokens)
                logger.info(f"✅ GitLab搜索找到 {len(gitlab_tokens)} 个tokens")
            except Exception as e:
                logger.error(f"❌ GitLab搜索失败: {e}")
                results["statistics"]["gitlab_error"] = str(e)
        
        if mode == 'docker' or mode == 'extended' or mode == 'all':
            logger.info("🔍 执行Docker搜索...")
            try:
                docker_tokens = self.docker_searcher.search_popular_images(max_images=5)
                all_tokens.update(docker_tokens)
                results["statistics"]["docker_found"] = len(docker_tokens)
                logger.info(f"✅ Docker搜索找到 {len(docker_tokens)} 个tokens")
            except Exception as e:
                logger.error(f"❌ Docker搜索失败: {e}")
                results["statistics"]["docker_error"] = str(e)
        
        # 如果是 'all' 模式，也执行原始搜索
        if mode == 'all':
            logger.info("🔍 执行GitHub和本地搜索...")
            original_results = super().hunt_tokens(mode='all', validate=False, max_results=max_results)
            original_tokens = original_results.get("found_tokens", [])
            all_tokens.update(original_tokens)
            results["statistics"]["github_found"] = original_results["statistics"].get("github_found", 0)
            results["statistics"]["local_found"] = original_results["statistics"].get("local_found", 0)
        
        results["found_tokens"] = list(all_tokens)
        results["statistics"]["total_found"] = len(all_tokens)
        
        # 验证tokens
        if validate and all_tokens:
            logger.info(f"🔐 开始验证 {len(all_tokens)} 个tokens...")
            validation_results = self._validate_tokens(list(all_tokens))
            
            for token, result in validation_results.items():
                if result.valid:
                    results["valid_tokens"].append(token)
                else:
                    results["invalid_tokens"].append({
                        "token": token[:10] + "...",
                        "reason": result.reason
                    })
            
            results["statistics"]["valid_count"] = len(results["valid_tokens"])
            results["statistics"]["invalid_count"] = len(results["invalid_tokens"])
            
            logger.info(f"✅ 验证完成: {len(results['valid_tokens'])} 个有效, {len(results['invalid_tokens'])} 个无效")
            
            # 自动保存有效tokens
            if self.auto_save and results["valid_tokens"]:
                self._save_valid_tokens(results["valid_tokens"])
        
        return results
    
    def search_all_extended_platforms(self, max_results: int = 100) -> Dict[str, List[str]]:
        """
        搜索所有扩展平台
        
        Args:
            max_results: 最大结果数
            
        Returns:
            平台到token列表的映射
        """
        results = {}
        
        # Web平台搜索
        try:
            web_results = self.web_searcher.search_all_platforms(max_results_per_platform=max_results // 4)
            results.update(web_results)
        except Exception as e:
            logger.error(f"Web平台搜索失败: {e}")
        
        # GitLab搜索
        try:
            gitlab_tokens = self.gitlab_searcher.search(max_results=max_results // 2)
            results['gitlab'] = gitlab_tokens
        except Exception as e:
            logger.error(f"GitLab搜索失败: {e}")
        
        # Docker搜索
        try:
            docker_tokens = self.docker_searcher.search_popular_images(max_images=10)
            results['docker'] = docker_tokens
        except Exception as e:
            logger.error(f"Docker搜索失败: {e}")
        
        return results
    
    def cleanup(self):
        """清理资源"""
        # 清理Docker搜索器
        if hasattr(self, 'docker_searcher'):
            self.docker_searcher.cleanup()
        
        # 清理其他资源
        logger.info("✅ Token Hunter V4 资源清理完成")