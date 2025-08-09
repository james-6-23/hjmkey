"""
GitHub Token 验证器
用于验证token的有效性、权限和额度
"""

import requests
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """API速率限制信息"""
    limit: int
    remaining: int
    reset: datetime
    used: int
    
    @property
    def is_exhausted(self) -> bool:
        """是否已耗尽额度"""
        return self.remaining == 0
    
    @property
    def usage_percentage(self) -> float:
        """使用百分比"""
        if self.limit == 0:
            return 0
        return (self.used / self.limit) * 100


@dataclass
class TokenValidationResult:
    """Token验证结果"""
    valid: bool = False
    token: str = ""
    reason: str = ""
    permissions: List[str] = None
    scopes: List[str] = None
    rate_limit: Optional[RateLimitInfo] = None
    user: Optional[str] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.scopes is None:
            self.scopes = []


class TokenValidator:
    """
    GitHub Token 验证器
    验证token的格式、权限和额度
    """
    
    # GitHub API端点
    API_BASE = "https://api.github.com"
    USER_ENDPOINT = f"{API_BASE}/user"
    RATE_LIMIT_ENDPOINT = f"{API_BASE}/rate_limit"
    
    # Token格式正则
    TOKEN_PATTERNS = [
        r'^ghp_[a-zA-Z0-9]{36}$',  # Personal access token (classic)
        r'^github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}$',  # Fine-grained personal access token
        r'^ghs_[a-zA-Z0-9]{36}$',  # GitHub App installation access token
    ]
    
    def __init__(self, proxy: Optional[Dict[str, str]] = None):
        """
        初始化验证器
        
        Args:
            proxy: 代理配置
        """
        self.proxy = proxy
        self.session = requests.Session()
        if proxy:
            self.session.proxies.update(proxy)
    
    def validate(self, token: str) -> TokenValidationResult:
        """
        验证GitHub token
        
        Args:
            token: GitHub访问令牌
            
        Returns:
            验证结果
        """
        result = TokenValidationResult(token=token[:10] + "..." if len(token) > 10 else token)
        
        # 1. 格式检查
        if not self._check_format(token):
            result.reason = "Token格式不正确"
            logger.warning(f"❌ Token格式错误: {result.token}")
            return result
        
        # 2. 验证token有效性和权限
        try:
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # 获取用户信息（验证token是否有效）
            user_response = self.session.get(
                self.USER_ENDPOINT,
                headers=headers,
                timeout=10
            )
            
            if user_response.status_code == 401:
                result.reason = "Token无效或已过期"
                logger.warning(f"❌ Token无效: {result.token}")
                return result
            
            if user_response.status_code == 403:
                result.reason = "Token被禁用或权限不足"
                logger.warning(f"❌ Token被禁用: {result.token}")
                return result
            
            if user_response.status_code != 200:
                result.reason = f"API请求失败: {user_response.status_code}"
                logger.error(f"❌ API请求失败: {user_response.status_code}")
                return result
            
            # 解析用户信息
            user_data = user_response.json()
            result.user = user_data.get("login", "unknown")
            
            # 获取token权限范围
            scopes = user_response.headers.get("X-OAuth-Scopes", "")
            if scopes:
                result.scopes = [s.strip() for s in scopes.split(",")]
                
                # 检查是否有public_repo权限
                required_scopes = ["public_repo", "repo"]
                has_required_scope = any(scope in result.scopes for scope in required_scopes)
                
                if not has_required_scope:
                    result.reason = "缺少public_repo或repo权限"
                    logger.warning(f"⚠️ Token权限不足: {result.token}, 当前权限: {result.scopes}")
                    return result
            
            # 3. 检查API额度
            rate_limit_response = self.session.get(
                self.RATE_LIMIT_ENDPOINT,
                headers=headers,
                timeout=10
            )
            
            if rate_limit_response.status_code == 200:
                rate_data = rate_limit_response.json()
                core_rate = rate_data.get("resources", {}).get("core", {})
                
                result.rate_limit = RateLimitInfo(
                    limit=core_rate.get("limit", 0),
                    remaining=core_rate.get("remaining", 0),
                    reset=datetime.fromtimestamp(core_rate.get("reset", 0)),
                    used=core_rate.get("used", 0)
                )
                
                # 检查额度是否充足
                if result.rate_limit.remaining == 0:
                    result.reason = f"API额度已耗尽，将在 {result.rate_limit.reset.strftime('%Y-%m-%d %H:%M:%S')} 重置"
                    logger.warning(f"⚠️ Token额度耗尽: {result.token}")
                    return result
                
                if result.rate_limit.remaining < 100:
                    logger.warning(f"⚠️ Token额度不足: {result.token}, 剩余: {result.rate_limit.remaining}")
            
            # 验证通过
            result.valid = True
            result.reason = "验证成功"
            logger.info(f"✅ Token验证成功: {result.token}, 用户: {result.user}, 剩余额度: {result.rate_limit.remaining if result.rate_limit else 'unknown'}")
            
        except requests.exceptions.RequestException as e:
            result.reason = f"网络请求失败: {str(e)}"
            logger.error(f"❌ 网络请求失败: {str(e)}")
        except Exception as e:
            result.reason = f"验证过程出错: {str(e)}"
            logger.error(f"❌ 验证出错: {str(e)}")
        
        return result
    
    def _check_format(self, token: str) -> bool:
        """
        检查token格式是否正确
        
        Args:
            token: GitHub token
            
        Returns:
            格式是否正确
        """
        if not token or not isinstance(token, str):
            return False
        
        # 检查是否匹配任一已知格式
        for pattern in self.TOKEN_PATTERNS:
            if re.match(pattern, token):
                return True
        
        return False
    
    def batch_validate(self, tokens: List[str]) -> List[TokenValidationResult]:
        """
        批量验证tokens
        
        Args:
            tokens: token列表
            
        Returns:
            验证结果列表
        """
        results = []
        total = len(tokens)
        
        logger.info(f"🔍 开始批量验证 {total} 个tokens...")
        
        for i, token in enumerate(tokens, 1):
            logger.info(f"验证进度: {i}/{total}")
            result = self.validate(token)
            results.append(result)
            
            # 避免触发GitHub的速率限制
            if i < total:
                import time
                time.sleep(0.5)
        
        # 统计结果
        valid_count = sum(1 for r in results if r.valid)
        logger.info(f"✅ 批量验证完成: {valid_count}/{total} 个有效tokens")
        
        return results
    
    def check_rate_limit(self, token: str) -> Optional[RateLimitInfo]:
        """
        仅检查token的API额度
        
        Args:
            token: GitHub token
            
        Returns:
            速率限制信息，如果失败返回None
        """
        try:
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = self.session.get(
                self.RATE_LIMIT_ENDPOINT,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                rate_data = response.json()
                core_rate = rate_data.get("resources", {}).get("core", {})
                
                return RateLimitInfo(
                    limit=core_rate.get("limit", 0),
                    remaining=core_rate.get("remaining", 0),
                    reset=datetime.fromtimestamp(core_rate.get("reset", 0)),
                    used=core_rate.get("used", 0)
                )
        except Exception as e:
            logger.error(f"检查额度失败: {str(e)}")
        
        return None
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'session'):
            self.session.close()


def main():
    """测试函数"""
    import os
    
    # 从环境变量获取测试token
    test_token = os.getenv("GITHUB_TOKEN")
    if not test_token:
        print("请设置GITHUB_TOKEN环境变量进行测试")
        return
    
    # 创建验证器
    validator = TokenValidator()
    
    # 验证token
    result = validator.validate(test_token)
    
    # 打印结果
    print(f"验证结果: {'✅ 有效' if result.valid else '❌ 无效'}")
    print(f"原因: {result.reason}")
    if result.valid:
        print(f"用户: {result.user}")
        print(f"权限: {', '.join(result.scopes)}")
        if result.rate_limit:
            print(f"API额度: {result.rate_limit.remaining}/{result.rate_limit.limit}")
            print(f"使用率: {result.rate_limit.usage_percentage:.1f}%")
            print(f"重置时间: {result.rate_limit.reset.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()