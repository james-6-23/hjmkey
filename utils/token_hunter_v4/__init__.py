"""
Token Hunter V4 - 扩展版本
支持 Web、GitLab、Docker 等平台搜索
"""

from .hunter_v4 import TokenHunterV4

# 导入原始版本的组件
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from token_hunter import (
    TokenManager,
    TokenValidator,
    TokenValidationResult,
    NoValidTokenError,
    NoQuotaError
)

__all__ = [
    'TokenHunterV4',
    'TokenManager',
    'TokenValidator',
    'TokenValidationResult',
    'NoValidTokenError',
    'NoQuotaError'
]