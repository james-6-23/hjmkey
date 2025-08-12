# V4 搜索器实现代码

本文档包含所有新搜索器的完整实现代码。

## 1. Web 搜索器实现

### 文件：`app/features/extended_search/web_searcher.py`

```python
"""
Web平台Token搜索器
搜索Stack Overflow、Pastebin、GitHub Gist等平台的泄露tokens
"""

import re
import requests
import time
import logging
from typing import List, Set, Dict, Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class WebSearcher:
    """Web平台Token搜索器"""
    
    # Token正则模式
    TOKEN_PATTERNS = [
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),  # GitHub Personal Access Token
        re.compile(r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}'),  # GitHub Fine-grained PAT
        re.compile(r'ghs_[a-zA-Z0-9]{36}'),  # GitHub App Token
        re.compile(r'AIzaSy[a-zA-Z0-9_-]{33}'),  # Google API Key
        re.compile(r'sk-[a-zA-Z0-9]{48}'),  # OpenAI API Key
        re.compile(r'glpat-[a-zA-Z0-9]{20}'),  # GitLab Personal Access Token
    ]
    
    def __init__(self, proxy: Optional[Dict[str, str]] = None):
        """
        初始化Web搜索器
        
        Args:
            proxy: 代理配置
        """
        self.proxy = proxy
        self.session = requests.Session()
        if proxy:
            self.session.proxies.update(proxy)
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        logger.info("✅ Web搜索器初始化完成")
    
    def search_stackoverflow(self, query: str = "github token api key", max_results: int = 50) -> List[str]:
        """
        搜索Stack Overflow
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            找到的token列表
        """
        tokens = set()
        logger.info(f"🔍 搜索Stack Overflow: {query}")
        
        try:
            # 使用Stack Exchange API
            api_url = "https://api.stackexchange.com/2.3/search/advanced"
            
            # 分页搜索
            page = 1
            while len(tokens) < max_results and page <= 5:  # 最多5页
                params = {
                    'order': 'desc',
                    'sort': 'creation',
                    'q': query,
                    'site': 'stackoverflow',
                    'pagesize': 100,
                    'page': page,
                    'filter': 'withbody'  # 包含问题和答案的内容
                }
                
                response = self.session.get(api_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    
                    if not items:
                        break
                    
                    for item in items:
                        # 搜索问题内容
                        title = item.get('title', '')
                        body = item.get('body', '')
                        content = f"{title} {body}"
                        
                        # 提取tokens
                        question_tokens = self._extract_tokens_from_text(content)
                        tokens.update(question_tokens)
                        
                        # 搜索答案
                        if 'answers' in item:
                            for answer in item['answers']:
                                answer_body = answer.get('body', '')
                                answer_tokens = self._extract_tokens_from_text(answer_body)
                                tokens.update(answer_tokens)
                    
                    # 检查是否还有更多页面
                    if not data.get('has_more', False):
                        break
                    
                    page += 1
                    time.sleep(0.5)  # 避免触发速率限制
                else:
                    logger.warning(f"Stack Overflow API返回错误: {response.status_code}")
                    break
        
        except Exception as e:
            logger.error(f"搜索Stack Overflow失败: {e}")
        
        logger.info(f"✅ Stack Overflow搜索完成，找到 {len(tokens)} 个tokens")
        return list(tokens)[:max_results]
    
    def search_pastebin_recent(self, max_results: int = 20) -> List[str]:
        """
        搜索Pastebin最近的公开内容
        
        Args:
            max_results: 最大结果数
            
        Returns:
            找到的token列表
        """
        tokens = set()
        logger.info("🔍 搜索Pastebin最近内容")
        
        try:
            # Pastebin scraping API
            api_url = "https://scrape.pastebin.com/api_scraping.php"
            params = {
                'limit': min(max_results * 5, 250)  # 获取更多以提高命中率
            }
            
            response = self.session.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                pastes = response.json()
                
                for paste in pastes[:max_results * 2]:  # 检查更多paste
                    paste_key = paste.get('key')
                    if paste_key:
                        # 获取paste内容
                        content_url = f"https://pastebin.com/raw/{paste_key}"
                        try:
                            content_response = self.session.get(content_url, timeout=5)
                            if content_response.status_code == 200:
                                # 提取tokens
                                paste_tokens = self._extract_tokens_from_text(content_response.text)
                                tokens.update(paste_tokens)
                                
                                if len(tokens) >= max_results:
                                    break
                        except:
                            continue
                        
                        # 避免被封IP
                        time.sleep(1)
            else:
                logger.warning(f"Pastebin API返回错误: {response.status_code}")
        
        except Exception as e:
            logger.error(f"搜索Pastebin失败: {e}")
        
        logger.info(f"✅ Pastebin搜索完成，找到 {len(tokens)} 个tokens")
        return list(tokens)[:max_results]
    
    def search_github_gist(self, query: str = "AIzaSy", max_results: int = 30) -> List[str]:
        """
        搜索GitHub Gist
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            找到的token列表
        """
        tokens = set()
        logger.info(f"🔍 搜索GitHub Gist: {query}")
        
        try:
            # 使用GitHub搜索API搜索Gist
            api_url = "https://api.github.com/search/code"
            
            # 构建搜索查询
            search_query = f'{query} in:file'
            
            params = {
                'q': search_query,
                'per_page': min(max_results, 100),
                'sort': 'indexed',
                'order': 'desc'
            }
            
            headers = {
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = self.session.get(api_url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                for item in items:
                    # 只处理Gist
                    if 'gist.github.com' in item.get('html_url', ''):
                        # 获取文件内容
                        file_url = item.get('url')
                        if file_url:
                            try:
                                file_response = self.session.get(file_url, headers=headers, timeout=5)
                                if file_response.status_code == 200:
                                    file_data = file_response.json()
                                    content = file_data.get('content', '')
                                    
                                    if content:
                                        # Base64解码
                                        import base64
                                        try:
                                            decoded_content = base64.b64decode(content).decode('utf-8')
                                            gist_tokens = self._extract_tokens_from_text(decoded_content)
                                            tokens.update(gist_tokens)
                                        except:
                                            pass
                            except:
                                continue
                            
                            time.sleep(0.5)  # 避免触发速率限制
            else:
                logger.warning(f"GitHub API返回错误: {response.status_code}")
        
        except Exception as e:
            logger.error(f"搜索GitHub Gist失败: {e}")
        
        logger.info(f"✅ GitHub Gist搜索完成，找到 {len(tokens)} 个tokens")
        return list(tokens)[:max_results]
    
    def search_reddit(self, subreddit: str = "programming", max_results: int = 30) -> List[str]:
        """
        搜索Reddit
        
        Args:
            subreddit: 子版块名称
            max_results: 最大结果数
            
        Returns:
            找到的token列表
        """
        tokens = set()
        logger.info(f"🔍 搜索Reddit r/{subreddit}")
        
        try:
            # Reddit JSON API
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {
                'q': 'api key OR token OR "AIzaSy" OR "ghp_"',
                'sort': 'new',
                'limit': min(max_results * 2, 100),
                'restrict_sr': 'true'
            }
            
            headers = {
                'User-Agent': 'TokenHunter/1.0'
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])
                
                for post in posts:
                    post_data = post.get('data', {})
                    
                    # 搜索标题和内容
                    title = post_data.get('title', '')
                    selftext = post_data.get('selftext', '')
                    content = f"{title} {selftext}"
                    
                    # 提取tokens
                    post_tokens = self._extract_tokens_from_text(content)
                    tokens.update(post_tokens)
                    
                    # 也搜索评论（如果有URL）
                    if post_data.get('num_comments', 0) > 0:
                        comments_url = f"https://www.reddit.com{post_data.get('permalink', '')}.json"
                        try:
                            comments_response = self.session.get(comments_url, headers=headers, timeout=5)
                            if comments_response.status_code == 200:
                                comments_data = comments_response.json()
                                # 简单处理第一层评论
                                if len(comments_data) > 1:
                                    comments = comments_data[1].get('data', {}).get('children', [])
                                    for comment in comments[:10]:  # 只看前10条评论
                                        comment_body = comment.get('data', {}).get('body', '')
                                        comment_tokens = self._extract_tokens_from_text(comment_body)
                                        tokens.update(comment_tokens)
                        except:
                            pass
                    
                    time.sleep(0.5)  # 避免触发速率限制
            else:
                logger.warning(f"Reddit API返回错误: {response.status_code}")
        
        except Exception as e:
            logger.error(f"搜索Reddit失败: {e}")
        
        logger.info(f"✅ Reddit搜索完成，找到 {len(tokens)} 个tokens")
        return list(tokens)[:max_results]
    
    def _extract_tokens_from_text(self, text: str) -> Set[str]:
        """
        从文本中提取tokens
        
        Args:
            text: 要搜索的文本
            
        Returns:
            找到的token集合
        """
        tokens = set()
        if not text:
            return tokens
        
        # 使用所有token模式进行匹配
        for pattern in self.TOKEN_PATTERNS:
            matches = pattern.findall(text)
            tokens.update(matches)
        
        # 过滤明显的占位符
        filtered_tokens = set()
        for token in tokens:
            # 检查是否是占位符
            if not any(placeholder in token.lower() for placeholder in ['xxx', 'your', 'example', 'test', 'demo']):
                # 检查是否全是重复字符
                if len(set(token[10:])) > 5:  # 前缀后的部分有足够的字符多样性
                    filtered_tokens.add(token)
        
        return filtered_tokens
    
    def search_all_platforms(self, max_results_per_platform: int = 20) -> Dict[str, List[str]]:
        """
        搜索所有平台
        
        Args:
            max_results_per_platform: 每个平台的最大结果数
            
        Returns:
            平台到token列表的映射
        """
        results = {}
        
        logger.info("🔍 开始搜索所有Web平台...")
        
        # Stack Overflow
        logger.info("搜索Stack Overflow...")
        results['stackoverflow'] = self.search_stackoverflow(max_results=max_results_per_platform)
        
        # Pastebin
        logger.info("搜索Pastebin...")
        results['pastebin'] = self.search_pastebin_recent(max_results=max_results_per_platform)
        
        # GitHub Gist
        logger.info("搜索GitHub Gist...")
        results['github_gist'] = self.search_github_gist(max_results=max_results_per_platform)
        
        # Reddit
        logger.info("搜索Reddit...")
        results['reddit'] = self.search_reddit(max_results=max_results_per_platform)
        
        # 统计结果
        total_tokens = sum(len(tokens) for tokens in results.values())
        logger.info(f"✅ Web搜索完成，共找到 {total_tokens} 个潜在tokens")
        
        for platform, tokens in results.items():
            logger.info(f"   {platform}: {len(tokens)} tokens")
        
        return results
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'session'):
            self.session.close()
```

## 2. GitLab 搜索器实现

### 文件：`app/features/extended_search/gitlab_searcher.py`

```python
"""
GitLab Token搜索器
搜索GitLab公开仓库中的泄露tokens
"""

import re
import requests
import time
import logging
from typing import List, Set, Dict, Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class GitLabSearcher:
    """GitLab Token搜索器"""
    
    # GitLab实例列表
    GITLAB_INSTANCES = [
        "https://gitlab.com",  # 官方GitLab
        # 可以添加其他公开的GitLab实例
    ]
    
    # Token正则模式
    TOKEN_PATTERNS = [
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),  # GitHub token
        re.compile(r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}'),
        re.compile(r'ghs_[a-zA-Z0-9]{36}'),
        re.compile(r'AIzaSy[a-zA-Z0-9_-]{33}'),  # Google API Key
        re.compile(r'glpat-[a-zA-Z0-9]{20}'),  # GitLab Personal Access Token
        re.compile(r'gpldt-[a-zA-Z0-9]{20}'),  # GitLab Deploy Token
        re.compile(r'gldt-[a-zA-Z0-9]{20}'),  # GitLab Deploy Token (alternative)
    ]
    
    def __init__(self, access_token: Optional[str] = None, proxy: Optional[Dict] = None, gitlab_url: str = None):
        """
        初始化GitLab搜索器
        
        Args:
            access_token: GitLab访问令牌（可选，用于提高API限制）
            proxy: 代理配置
            gitlab_url: GitLab实例URL（默认使用gitlab.com）
        """
        self.access_token = access_token
        self.proxy = proxy
        self.gitlab_url = gitlab_url or self.GITLAB_INSTANCES[0]
        self.api_base = f"{self.gitlab_url}/api/v4"
        
        self.session = requests.Session()
        if proxy:
            self.session.proxies.update(proxy)
        
        # 设置请求头
        self.headers = {
            'User-Agent': 'TokenHunter/1.0'
        }
        
        if access_token:
            self.headers['Authorization'] = f'Bearer {access_token}'
        
        logger.info(f"✅ GitLab搜索器初始化完成 - {self.gitlab_url}")
    
    def search(self, query: str = "AIzaSy", max_results: int = 100) -> List[str]:
        """
        搜索GitLab公开项目
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            找到的token列表
        """
        tokens = set()
        logger.info(f"🔍 搜索GitLab: {query}")
        
        # 搜索不同的范围
        scopes = ['blobs', 'issues', 'merge_requests', 'commits']
        
        for scope in scopes:
            if len(tokens) >= max_results:
                break
            
            logger.info(f"搜索范围: {scope}")
            scope_tokens = self._search_scope(query, scope, max_results - len(tokens))
            tokens.update(scope_tokens)
        
        logger.info(f"✅ GitLab搜索完成，找到 {len(tokens)} 个tokens")
        return list(tokens)[:max_results]
    
    def _search_scope(self, query: str, scope: str, max_results: int) -> Set[str]:
        """
        在特定范围内搜索
        
        Args:
            query: 搜索查询
            scope: 搜索范围
            max_results: 最大结果数
            
        Returns:
            找到的token集合
        """
        tokens = set()
        
        try:
            # GitLab搜索API
            search_url = f"{self.api_base}/search"
            
            page = 1
            per_page = 20
            
            while len(tokens) < max_results and page <= 5:  # 最多5页
                params = {
                    'scope': scope,
                    'search': query,
                    'per_page': per_page,
                    'page': page
                }
                
                response = self.session.get(
                    search_url,
                    params=params,
                    headers=self.headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    results = response.json()
                    
                    if not results:
                        break
                    
                    # 根据不同的scope处理结果
                    if scope == 'blobs':
                        for item in results:
                            # 获取文件内容
                            file_tokens = self._extract_from_blob(item)
                            tokens.update(file_tokens)
                    
                    elif scope == 'issues':
                        for item in results:
                            # 从issue中提取
                            title = item.get('title', '')
                            description = item.get('description', '')
                            content = f"{title} {description}"
                            issue_tokens = self._extract_tokens_from_text(content)
                            tokens.update(issue_tokens)
                    
                    elif scope == 'merge_requests':
                        for item in results:
                            # 从MR中提取
                            title = item.get('title', '')
                            description = item.get('description', '')
                            content = f"{title} {description}"
                            mr_tokens = self._extract_tokens_from_text(content)
                            tokens.update(mr_tokens)
                    
                    elif scope == 'commits':
                        for item in results:
                            # 从commit消息中提取
                            message = item.get('message', '')
                            title = item.get('title', '')
                            content = f"{title} {message}"
                            commit_tokens = self._extract_tokens_from_text(content)
                            tokens.update(commit_tokens)
                    
                    page += 1
                    time.sleep(0.5)  # 避免触发速率限制
                
                elif response.status_code == 401:
                    logger.warning("GitLab API认证失败")
                    break
                elif response.status_code == 429:
                    logger.warning("GitLab API速率限制")
                    break
                else:
                    logger.warning(f"GitLab API返回错误: {response.status_code}")
                    break
        
        except Exception as e:
            logger.error(f"搜索GitLab {scope} 失败: {e}")
        
        return tokens
    
    def _extract_from_blob(self, blob_item: Dict) -> Set[str]:
        """
        从blob（文件）结果中提取tokens
        
        Args:
            blob_item: blob搜索结果项
            
        Returns:
            找到的token集合
        """
        tokens = set()
        
        try:
            # 获取项目ID和文件路径
            project_id = blob_item.get('project_id')
            file_path = blob_item.get('path')
            ref = blob_item.get('ref', 'master')
            
            if project_id and file_path:
                # 构建文件内容URL
                file_url = f"{self.api_base}/projects/{project_id}/repository/files/{quote(file_path, safe='')}/raw"
                params = {'ref': ref}
                
                response = self.session.get(
                    file_url,
                    params=params,
                    headers=self.headers,
                    timeout=5
                )
                
                if response.status_code == 200:
                    content = response.text
                    # 限制内容大小，避免处理过大的文件
                    if len(content) < 1024 * 1024:  # 1MB
                        file_tokens = self._extract_tokens_from_text(content)
                        tokens.update(file_tokens)
                
        except Exception as e:
            logger.debug(f"提取GitLab文件失败: {e}")
        
        return tokens
    
    def search_user_projects(self, username: str, max_results: int = 50) -> List[str]:
        """
        搜索特定用户的公开项目
        
        Args:
            username: GitLab用户名
            max_results: 最大结果数
            
        Returns:
            找到的token列表
        """
        tokens = set()
        logger.info(f"🔍 搜索GitLab用户 {username} 的项目")
        
        try:
            # 获取用户信息
            user_url = f"{self.api_base}/users"
            params = {'username': username}
            
            response = self.session.get(user_url, params=params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                users = response.json()
                if users:
                    user_id = users[0].get('id')
                    
                    # 获取用户的公开项目
                    projects_url = f"{self.api_base}/users/{user_id}/projects"
                    params = {'per_page': 100}
                    
                    response = self.session.get(projects_url, params=params, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        projects = response.json()
                        
                        for project in projects[:20]:  # 最多检查20个项目
                            project_id = project.get('id')
                            project_name = project.get('name')
                            
                            logger.info(f"检查项目: {project_name}")
                            
                            # 搜索项目中的文件
                            project_tokens = self._search_project_files(project_id, max_results=10)
                            tokens.update(project_tokens)
                            
                            if len(tokens) >= max_results:
                                break
        
        except Exception as e:
            logger.error(f"搜索GitLab用户项目失败: {e}")
        
        logger.info(f"✅ 用户项目搜索完成，找到 {len(tokens)} 个tokens")
        return list(tokens)[:max_results]
    
    def _search_project_files(self, project_id: int, max_results: int = 20) -> Set[str]:
        """
        搜索项目中的文件
        
        Args:
            project_id: 项目ID
            max_results: 最大结果数
            
        Returns:
            找到的token集合
        """
        tokens = set()
        
        try:
            # 获取项目的文件树
            tree_url = f"{self.api_base}/projects/{project_id}/repository/tree"
            params = {
                'recursive': 'true',
                'per_page': 100
            }
            
            response = self.session.get(tree_url, params=params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                files = response.json()
                
                # 优先检查的文件
                priority_files = ['.env', 'config.json', 'config.yml', 'settings.py', 'application.properties']
                
                # 先检查优先文件
                for file_item in files:
                    if file_item.get('type') == 'blob':
                        file_name = file_item.get('name', '').lower()
                        file_path = file_item.get('path', '')
                        
                        if any(pf in file_name for pf in priority_files):
                            # 获取文件内容
                            file_url = f"{self.api_base}/projects/{project_id}/repository/files/{quote(file_path, safe='')}/raw"
                            
                            try:
                                file_response = self.session.get(file_url, headers=self.headers, timeout=5)
                                if file_response.status_code == 200:
                                    content = file_response.text
                                    if len(content) < 100 * 1024:  # 100KB
                                        file_tokens = self._extract_tokens_from_text(content)
                                        tokens.update(file_tokens)
                            except:
                                pass
                            
                            if len(tokens) >= max_results:
                                break
                            
                            time.sleep(0.2)  # 避免触发速率限制
        
        except Exception as e:
            logger.debug(f"搜索项目文件失败: {e}")
        
        return tokens
    
    def _extract_tokens_from_text(self, text: str) -> Set[str]:
        """
        从文本中提取tokens
        
        Args:
            text: 要搜索的文本
            
        Returns:
            找到的token集合
        """
        tokens = set()
        if not text:
            return tokens
        
        # 使用所有token模式进行匹配
        for pattern in self.TOKEN_PATTERNS:
            matches = pattern.findall(text)
            tokens.update(matches)
        
        # 过滤明显的占位符
        filtered_tokens = set()
        for token in tokens:
            # 检查是否是占位符
            if not any(placeholder in token.lower() for placeholder in ['xxx', 'your', 'example', 'test', 'demo', 'sample']):
                # 检查是否全是重复字符
                if len(set(token[10:])) > 5:  # 前缀后的部分有足够的字符多样性
                    filtered_tokens.add(token)
        
        return filtered_tokens
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'session'):
            self.session.close()
```

## 3. Docker 搜索器实现

### 文件：`app/features/extended_search/docker_searcher.py`

```python
"""
Docker镜像Token搜索器
搜索Docker Hub公开镜像中的泄露tokens
"""

import re
import json
import tarfile
import tempfile
import logging
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
import docker
import requests

logger = logging.getLogger(__name__)


class DockerSearcher:
    """Docker镜像Token搜索器"""
    
    # Token正则模式
    TOKEN_PATTERNS = [
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),
        re.compile(r'github_pat_[a