"""
GitHub Token 搜索器
从GitHub公开仓库搜索泄露的tokens
"""

import re
import time
import random
from typing import List, Set, Dict, Any, Optional
import logging
import requests

logger = logging.getLogger(__name__)


class GitHubSearcher:
    """
    GitHub Token搜索器
    搜索GitHub公开仓库中泄露的tokens
    """
    
    # GitHub搜索API
    SEARCH_API = "https://api.github.com/search/code"
    
    # 搜索查询模板
    SEARCH_QUERIES = [
        'ghp_ in:file extension:env',
        'ghp_ in:file extension:yml',
        'ghp_ in:file extension:yaml',
        'ghp_ in:file extension:json',
        'ghp_ in:file extension:js',
        'ghp_ in:file extension:py',
        'github_pat_ in:file',
        '"GITHUB_TOKEN" in:file',
        '"GH_TOKEN" in:file',
        'filename:.env GITHUB',
        'filename:config github token',
        'path:.github token',
    ]
    
    # Token正则模式
    TOKEN_PATTERNS = [
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),  # Personal access token (classic)
        re.compile(r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}'),  # Fine-grained token
        re.compile(r'ghs_[a-zA-Z0-9]{36}'),  # GitHub App token
    ]
    
    # 需要排除的仓库（示例、文档等）
    EXCLUDED_REPOS = [
        'github/docs',
        'github/gitignore',
        'github-changelog-generator',
        'actions/toolkit',
    ]
    
    def __init__(self, github_token: Optional[str] = None, proxy: Optional[Dict[str, str]] = None):
        """
        初始化搜索器
        
        Args:
            github_token: 用于搜索的GitHub token（提高速率限制）
            proxy: 代理配置
        """
        self.github_token = github_token
        self.proxy = proxy
        self.session = requests.Session()
        
        if proxy:
            self.session.proxies.update(proxy)
        
        # 设置请求头
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TokenHunter/1.0"
        }
        
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
    
    def search(self, max_results: int = 100) -> List[str]:
        """
        搜索GitHub上的tokens
        
        Args:
            max_results: 最大结果数
            
        Returns:
            找到的token列表
        """
        logger.info("🔍 开始搜索GitHub公开仓库中的tokens...")
        
        all_tokens = set()
        
        for query in self.SEARCH_QUERIES:
            if len(all_tokens) >= max_results:
                break
            
            logger.info(f"执行查询: {query}")
            tokens = self._search_with_query(query, max_results - len(all_tokens))
            all_tokens.update(tokens)
            
            # 避免触发速率限制
            time.sleep(random.uniform(2, 5))
        
        logger.info(f"✅ GitHub搜索完成，找到 {len(all_tokens)} 个潜在tokens")
        return list(all_tokens)
    
    def _search_with_query(self, query: str, max_results: int = 30) -> Set[str]:
        """
        使用特定查询搜索tokens
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            找到的token集合
        """
        tokens = set()
        
        try:
            params = {
                "q": query,
                "per_page": min(30, max_results),  # GitHub限制最多100
                "sort": "indexed",  # 按最近索引排序
                "order": "desc"
            }
            
            response = self.session.get(
                self.SEARCH_API,
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 403:
                logger.warning("⚠️ GitHub API速率限制，请稍后重试或提供token")
                return tokens
            
            if response.status_code != 200:
                logger.error(f"❌ 搜索失败: HTTP {response.status_code}")
                return tokens
            
            data = response.json()
            items = data.get("items", [])
            
            logger.info(f"找到 {len(items)} 个搜索结果")
            
            for item in items:
                # 检查是否是排除的仓库
                repo_name = item.get("repository", {}).get("full_name", "")
                if any(excluded in repo_name.lower() for excluded in self.EXCLUDED_REPOS):
                    continue
                
                # 获取文件内容
                file_url = item.get("url")
                if file_url:
                    file_tokens = self._extract_tokens_from_file(file_url)
                    tokens.update(file_tokens)
                
                if len(tokens) >= max_results:
                    break
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 搜索请求失败: {e}")
        except Exception as e:
            logger.error(f"❌ 搜索过程出错: {e}")
        
        return tokens
    
    def _extract_tokens_from_file(self, file_url: str) -> Set[str]:
        """
        从文件中提取tokens
        
        Args:
            file_url: 文件API URL
            
        Returns:
            提取的token集合
        """
        tokens = set()
        
        try:
            response = self.session.get(
                file_url,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return tokens
            
            file_data = response.json()
            
            # 获取文件内容（base64编码）
            content = file_data.get("content", "")
            if content:
                # 解码base64
                import base64
                try:
                    decoded_content = base64.b64decode(content).decode('utf-8')
                    
                    # 提取tokens
                    for pattern in self.TOKEN_PATTERNS:
                        matches = pattern.findall(decoded_content)
                        tokens.update(matches)
                        
                except Exception as e:
                    logger.debug(f"解码文件内容失败: {e}")
            
        except Exception as e:
            logger.debug(f"获取文件内容失败: {e}")
        
        return tokens
    
    def search_user_repos(self, username: str) -> List[str]:
        """
        搜索特定用户的公开仓库
        
        Args:
            username: GitHub用户名
            
        Returns:
            找到的token列表
        """
        logger.info(f"🔍 搜索用户 {username} 的公开仓库...")
        
        tokens = set()
        
        # 搜索用户仓库中的tokens
        queries = [
            f'user:{username} ghp_ in:file',
            f'user:{username} github_pat_ in:file',
            f'user:{username} filename:.env',
            f'user:{username} filename:config token'
        ]
        
        for query in queries:
            query_tokens = self._search_with_query(query, max_results=20)
            tokens.update(query_tokens)
            time.sleep(2)
        
        logger.info(f"✅ 在用户 {username} 的仓库中找到 {len(tokens)} 个tokens")
        return list(tokens)
    
    def search_organization_repos(self, org_name: str) -> List[str]:
        """
        搜索组织的公开仓库
        
        Args:
            org_name: 组织名称
            
        Returns:
            找到的token列表
        """
        logger.info(f"🔍 搜索组织 {org_name} 的公开仓库...")
        
        tokens = set()
        
        # 搜索组织仓库中的tokens
        queries = [
            f'org:{org_name} ghp_ in:file',
            f'org:{org_name} github_pat_ in:file',
            f'org:{org_name} filename:.env',
        ]
        
        for query in queries:
            query_tokens = self._search_with_query(query, max_results=20)
            tokens.update(query_tokens)
            time.sleep(2)
        
        logger.info(f"✅ 在组织 {org_name} 的仓库中找到 {len(tokens)} 个tokens")
        return list(tokens)
    
    def check_rate_limit(self) -> Dict[str, Any]:
        """
        检查API速率限制
        
        Returns:
            速率限制信息
        """
        try:
            response = self.session.get(
                "https://api.github.com/rate_limit",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                search_limit = data.get("resources", {}).get("search", {})
                
                return {
                    "limit": search_limit.get("limit", 0),
                    "remaining": search_limit.get("remaining", 0),
                    "reset": search_limit.get("reset", 0)
                }
        except Exception as e:
            logger.error(f"检查速率限制失败: {e}")
        
        return {"limit": 0, "remaining": 0, "reset": 0}


def main():
    """测试函数"""
    import os
    
    # 使用环境变量中的token（如果有）
    github_token = os.getenv("GITHUB_TOKEN")
    
    # 创建搜索器
    searcher = GitHubSearcher(github_token)
    
    # 检查速率限制
    rate_limit = searcher.check_rate_limit()
    print(f"API速率限制: {rate_limit['remaining']}/{rate_limit['limit']}")
    
    if rate_limit['remaining'] > 0:
        # 搜索tokens
        tokens = searcher.search(max_results=10)
        
        print(f"\n找到 {len(tokens)} 个潜在tokens:")
        for i, token in enumerate(tokens, 1):
            print(f"{i}. {token[:20]}...")
    else:
        print("API速率限制已耗尽，请稍后重试")


if __name__ == "__main__":
    main()