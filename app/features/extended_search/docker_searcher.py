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
from io import BytesIO

logger = logging.getLogger(__name__)


class DockerSearcher:
    """Docker镜像Token搜索器"""
    
    # Token正则模式
    TOKEN_PATTERNS = [
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),
        re.compile(r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}'),
        re.compile(r'ghs_[a-zA-Z0-9]{36}'),
        re.compile(r'AIzaSy[a-zA-Z0-9_-]{33}'),
        re.compile(r'sk-[a-zA-Z0-9]{48}'),
        re.compile(r'glpat-[a-zA-Z0-9]{20}'),
    ]
    
    # 需要检查的文件模式
    INTERESTING_FILES = [
        r'\.env$',
        r'\.env\.',
        r'config\.json$',
        r'config\.yml$',
        r'config\.yaml$',
        r'application\.properties$',
        r'settings\.py$',
        r'\.bashrc$',
        r'\.zshrc$',
        r'\.profile$',
        r'dockerfile$',
        r'docker-compose\.yml$',
    ]
    
    def __init__(self):
        """初始化Docker搜索器"""
        self.docker_client = None
        self.session = requests.Session()
        
        try:
            # 尝试连接Docker daemon
            self.docker_client = docker.from_env()
            logger.info("✅ Docker客户端初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ Docker客户端初始化失败: {e}")
            logger.info("将使用Docker Hub API进行搜索")
    
    def search_popular_images(self, max_images: int = 20) -> List[str]:
        """
        搜索流行的Docker镜像
        
        Args:
            max_images: 最大镜像数
            
        Returns:
            找到的token列表
        """
        tokens = set()
        
        # 热门镜像列表
        popular_images = [
            "node:latest",
            "node:alpine",
            "python:latest",
            "python:3.9",
            "python:alpine",
            "nginx:latest",
            "nginx:alpine",
            "mysql:latest",
            "postgres:latest",
            "redis:latest",
            "mongo:latest",
            "ubuntu:latest",
            "debian:latest",
            "alpine:latest",
            "busybox:latest",
            "wordpress:latest",
            "php:latest",
            "httpd:latest",
            "jenkins/jenkins:lts",
            "gitlab/gitlab-ce:latest"
        ]
        
        logger.info(f"🔍 开始搜索 {len(popular_images[:max_images])} 个流行Docker镜像")
        
        for i, image_name in enumerate(popular_images[:max_images], 1):
            logger.info(f"[{i}/{min(max_images, len(popular_images))}] 检查镜像: {image_name}")
            
            try:
                image_tokens = self.search_image(image_name)
                tokens.update(image_tokens)
                logger.info(f"   找到 {len(image_tokens)} 个tokens")
            except Exception as e:
                logger.error(f"   搜索失败: {e}")
        
        logger.info(f"✅ Docker镜像搜索完成，共找到 {len(tokens)} 个tokens")
        return list(tokens)
    
    def search_image(self, image_name: str) -> List[str]:
        """
        搜索指定Docker镜像中的tokens
        
        Args:
            image_name: 镜像名称
            
        Returns:
            找到的token列表
        """
        tokens = set()
        
        if self.docker_client:
            # 使用Docker客户端
            tokens.update(self._search_with_docker_client(image_name))
        else:
            # 使用Docker Hub API
            tokens.update(self._search_with_api(image_name))
        
        return list(tokens)
    
    def _search_with_docker_client(self, image_name: str) -> Set[str]:
        """
        使用Docker客户端搜索镜像
        
        Args:
            image_name: 镜像名称
            
        Returns:
            找到的token集合
        """
        tokens = set()
        
        try:
            # 拉取镜像
            logger.info(f"拉取镜像: {image_name}")
            image = self.docker_client.images.pull(image_name)
            
            # 导出镜像为tar
            with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp_file:
                # 保存镜像
                for chunk in image.save():
                    tmp_file.write(chunk)
                tmp_file.flush()
                tmp_path = tmp_file.name
            
            try:
                # 分析tar文件
                tokens.update(self._analyze_image_tar(tmp_path))
            finally:
                # 清理临时文件
                Path(tmp_path).unlink(missing_ok=True)
            
            # 检查镜像的环境变量
            tokens.update(self._check_image_env(image))
            
        except Exception as e:
            logger.error(f"Docker客户端搜索失败: {e}")
        
        return tokens
    
    def _search_with_api(self, image_name: str) -> Set[str]:
        """
        使用Docker Hub API搜索镜像
        
        Args:
            image_name: 镜像名称
            
        Returns:
            找到的token集合
        """
        tokens = set()
        
        try:
            # 解析镜像名称
            if '/' in image_name:
                namespace, repo_tag = image_name.split('/', 1)
            else:
                namespace = 'library'
                repo_tag = image_name
            
            if ':' in repo_tag:
                repo, tag = repo_tag.split(':', 1)
            else:
                repo = repo_tag
                tag = 'latest'
            
            # 获取镜像manifest
            manifest_url = f"https://registry-1.docker.io/v2/{namespace}/{repo}/manifests/{tag}"
            
            # 首先获取认证token
            auth_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{namespace}/{repo}:pull"
            auth_response = self.session.get(auth_url)
            
            if auth_response.status_code == 200:
                auth_token = auth_response.json().get('token')
                
                # 获取manifest
                headers = {
                    'Authorization': f'Bearer {auth_token}',
                    'Accept': 'application/vnd.docker.distribution.manifest.v2+json'
                }
                
                manifest_response = self.session.get(manifest_url, headers=headers)
                
                if manifest_response.status_code == 200:
                    manifest = manifest_response.json()
                    
                    # 获取配置blob
                    config_digest = manifest.get('config', {}).get('digest')
                    if config_digest:
                        config_url = f"https://registry-1.docker.io/v2/{namespace}/{repo}/blobs/{config_digest}"
                        config_response = self.session.get(config_url, headers=headers)
                        
                        if config_response.status_code == 200:
                            config_data = config_response.json()
                            
                            # 检查环境变量
                            env_vars = config_data.get('config', {}).get('Env', [])
                            for env_var in env_vars:
                                env_tokens = self._extract_tokens_from_text(env_var)
                                tokens.update(env_tokens)
                            
                            # 检查历史命令
                            history = config_data.get('history', [])
                            for entry in history:
                                created_by = entry.get('created_by', '')
                                history_tokens = self._extract_tokens_from_text(created_by)
                                tokens.update(history_tokens)
        
        except Exception as e:
            logger.error(f"Docker Hub API搜索失败: {e}")
        
        return tokens
    
    def _analyze_image_tar(self, tar_path: str) -> Set[str]:
        """
        分析Docker镜像tar文件
        
        Args:
            tar_path: tar文件路径
            
        Returns:
            找到的token集合
        """
        tokens = set()
        
        try:
            with tarfile.open(tar_path, 'r') as tar:
                # 遍历tar中的文件
                for member in tar.getmembers():
                    if member.isfile():
                        # 检查是否是layer tar文件
                        if member.name.endswith('/layer.tar'):
                            # 提取并分析layer
                            layer_tokens = self._analyze_layer(tar, member)
                            tokens.update(layer_tokens)
                        
                        # 检查manifest和config文件
                        elif member.name in ['manifest.json', 'config.json']:
                            try:
                                f = tar.extractfile(member)
                                if f:
                                    content = f.read().decode('utf-8')
                                    config_tokens = self._extract_tokens_from_text(content)
                                    tokens.update(config_tokens)
                            except:
                                pass
        
        except Exception as e:
            logger.error(f"分析镜像tar文件失败: {e}")
        
        return tokens
    
    def _analyze_layer(self, tar: tarfile.TarFile, layer_member: tarfile.TarInfo) -> Set[str]:
        """
        分析Docker层
        
        Args:
            tar: 主tar文件对象
            layer_member: layer tar成员
            
        Returns:
            找到的token集合
        """
        tokens = set()
        
        try:
            # 提取layer tar
            layer_file = tar.extractfile(layer_member)
            if layer_file:
                # 在内存中打开layer tar
                with tarfile.open(fileobj=BytesIO(layer_file.read()), mode='r') as layer_tar:
                    # 遍历layer中的文件
                    for file_member in layer_tar.getmembers():
                        if file_member.isfile() and file_member.size < 1024 * 1024:  # 1MB限制
                            # 检查是否是感兴趣的文件
                            file_name = file_member.name.lower()
                            
                            if any(re.search(pattern, file_name) for pattern in self.INTERESTING_FILES):
                                try:
                                    f = layer_tar.extractfile(file_member)
                                    if f:
                                        content = f.read().decode('utf-8', errors='ignore')
                                        file_tokens = self._extract_tokens_from_text(content)
                                        if file_tokens:
                                            logger.debug(f"在文件 {file_member.name} 中找到 {len(file_tokens)} 个tokens")
                                            tokens.update(file_tokens)
                                except:
                                    pass
        
        except Exception as e:
            logger.debug(f"分析layer失败: {e}")
        
        return tokens
    
    def _check_image_env(self, image) -> Set[str]:
        """
        检查镜像的环境变量
        
        Args:
            image: Docker镜像对象
            
        Returns:
            找到的token集合
        """
        tokens = set()
        
        try:
            # 获取镜像配置
            config = image.attrs.get('Config', {})
            
            # 检查环境变量
            env_vars = config.get('Env', [])
            for env_var in env_vars:
                env_tokens = self._extract_tokens_from_text(env_var)
                tokens.update(env_tokens)
            
            # 检查标签
            labels = config.get('Labels', {})
            for label_key, label_value in labels.items():
                if label_value:
                    label_tokens = self._extract_tokens_from_text(f"{label_key}={label_value}")
                    tokens.update(label_tokens)
        
        except Exception as e:
            logger.debug(f"检查镜像环境变量失败: {e}")
        
        return tokens
    
    def search_by_keyword(self, keyword: str = "api", max_results: int = 20) -> List[str]:
        """
        通过关键词搜索Docker Hub
        
        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            找到的token列表
        """
        tokens = set()
        logger.info(f"🔍 在Docker Hub搜索关键词: {keyword}")
        
        try:
            # Docker Hub搜索API
            search_url = "https://hub.docker.com/v2/search/repositories/"
            params = {
                'query': keyword,
                'page_size': min(max_results, 100)
            }
            
            response = self.session.get(search_url, params=params)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                logger.info(f"找到 {len(results)} 个相关镜像")
                
                for i, result in enumerate(results[:max_results], 1):
                    repo_name = result.get('repo_name')
                    if repo_name:
                        logger.info(f"[{i}/{min(max_results, len(results))}] 检查镜像: {repo_name}")
                        
                        try:
                            # 搜索这个镜像
                            image_tokens = self.search_image(f"{repo_name}:latest")
                            tokens.update(image_tokens)
                            
                            if len(tokens) >= max_results * 2:
                                break
                        except Exception as e:
                            logger.debug(f"搜索镜像 {repo_name} 失败: {e}")
        
        except Exception as e:
            logger.error(f"Docker Hub搜索失败: {e}")
        
        logger.info(f"✅ 关键词搜索完成，找到 {len(tokens)} 个tokens")
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
            if not any(placeholder in token.lower() for placeholder in ['xxx', 'your', 'example', 'test', 'demo', 'sample', 'dummy']):
                # 检查是否全是重复字符
                if len(set(token[10:])) > 5:  # 前缀后的部分有足够的字符多样性
                    filtered_tokens.add(token)
        
        return filtered_tokens
    
    def cleanup(self):
        """清理资源"""
        if self.docker_client:
            try:
                self.docker_client.close()
            except:
                pass
        
        if hasattr(self, 'session'):
            self.session.close()