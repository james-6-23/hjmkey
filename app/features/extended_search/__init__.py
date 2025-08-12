"""
扩展搜索功能模块
提供 Web、GitLab、Docker 等平台的搜索功能
"""

from .manager import ExtendedSearchManager
from .web_searcher import WebSearcher
from .gitlab_searcher import GitLabSearcher
from .docker_searcher import DockerSearcher

__all__ = [
    'ExtendedSearchManager',
    'WebSearcher',
    'GitLabSearcher',
    'DockerSearcher'
]