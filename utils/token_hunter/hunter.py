"""
Token Hunter 主模块
整合GitHub和本地搜索功能
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from .github_searcher import GitHubSearcher
from .local_searcher import LocalSearcher
from .validator import TokenValidator, TokenValidationResult
from .manager import TokenManager

# 加载.env文件
load_dotenv()

logger = logging.getLogger(__name__)


class TokenHunter:
    """
    Token搜索器主类
    整合所有搜索和验证功能
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        proxy: Optional[Dict[str, str]] = None,
        tokens_file: str = "data/github_tokens.txt",
        auto_save: bool = True
    ):
        """
        初始化Token Hunter
        
        Args:
            github_token: 用于GitHub搜索的token
            proxy: 代理配置（如果为None，会尝试从环境变量读取）
            tokens_file: tokens保存文件路径
            auto_save: 是否自动保存找到的有效tokens
        """
        # 如果没有提供代理配置，尝试从环境变量读取
        if proxy is None:
            proxy = self._get_proxy_from_env()
            if proxy:
                logger.info(f"🌐 从环境变量加载代理配置: {proxy['http']}")
        
        self.github_searcher = GitHubSearcher(github_token, proxy)
        self.local_searcher = LocalSearcher()
        self.validator = TokenValidator(proxy)
        self.manager = TokenManager(tokens_file)
        self.auto_save = auto_save
        
        logger.info("🎯 Token Hunter 初始化完成")
    
    def _get_proxy_from_env(self) -> Optional[Dict[str, str]]:
        """
        从环境变量或.env文件获取代理配置
        
        Returns:
            代理配置字典，如果未配置则返回None
        """
        # 尝试从PROXY环境变量读取（支持多个代理，用逗号分隔）
        proxy_str = os.getenv("PROXY", "").strip()
        
        if proxy_str:
            # 如果有多个代理，选择第一个
            proxies = [p.strip() for p in proxy_str.split(',') if p.strip()]
            if proxies:
                proxy_url = proxies[0]
                return {
                    'http': proxy_url,
                    'https': proxy_url
                }
        
        # 也支持标准的HTTP_PROXY和HTTPS_PROXY环境变量
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        
        if http_proxy or https_proxy:
            proxy_config = {}
            if http_proxy:
                proxy_config['http'] = http_proxy
            if https_proxy:
                proxy_config['https'] = https_proxy
            return proxy_config
        
        return None
    
    def hunt_tokens(
        self,
        mode: str = 'all',
        validate: bool = True,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        搜索tokens
        
        Args:
            mode: 搜索模式 ('github' | 'local' | 'all')
            validate: 是否验证找到的tokens
            max_results: 最大结果数
            
        Returns:
            搜索结果字典
        """
        logger.info(f"🏹 开始搜索tokens，模式: {mode}")
        
        results = {
            "mode": mode,
            "found_tokens": [],
            "valid_tokens": [],
            "invalid_tokens": [],
            "statistics": {}
        }
        
        all_tokens = set()
        
        # GitHub搜索
        if mode in ['github', 'all']:
            logger.info("🔍 执行GitHub搜索...")
            try:
                github_tokens = self.github_searcher.search(max_results)
                all_tokens.update(github_tokens)
                results["statistics"]["github_found"] = len(github_tokens)
                logger.info(f"✅ GitHub搜索找到 {len(github_tokens)} 个tokens")
            except Exception as e:
                logger.error(f"❌ GitHub搜索失败: {e}")
                results["statistics"]["github_error"] = str(e)
        
        # 本地搜索
        if mode in ['local', 'all']:
            logger.info("🔍 执行本地搜索...")
            try:
                local_tokens = self.local_searcher.search()
                all_tokens.update(local_tokens)
                results["statistics"]["local_found"] = len(local_tokens)
                logger.info(f"✅ 本地搜索找到 {len(local_tokens)} 个tokens")
            except Exception as e:
                logger.error(f"❌ 本地搜索失败: {e}")
                results["statistics"]["local_error"] = str(e)
        
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
    
    def _validate_tokens(self, tokens: List[str]) -> Dict[str, TokenValidationResult]:
        """
        批量验证tokens
        
        Args:
            tokens: token列表
            
        Returns:
            验证结果字典
        """
        results = {}
        
        for i, token in enumerate(tokens, 1):
            logger.info(f"验证进度: {i}/{len(tokens)}")
            result = self.validator.validate(token)
            results[token] = result
            
            # 避免触发速率限制
            if i < len(tokens):
                import time
                time.sleep(0.5)
        
        return results
    
    def _save_valid_tokens(self, tokens: List[str]) -> None:
        """
        保存有效tokens到文件
        
        Args:
            tokens: 有效token列表
        """
        logger.info(f"💾 保存 {len(tokens)} 个有效tokens...")
        
        saved_count = 0
        for token in tokens:
            if self.manager.add_token(token, validate=False):  # 已经验证过了
                saved_count += 1
        
        logger.info(f"✅ 成功保存 {saved_count} 个新tokens")
    
    def hunt_and_add(
        self,
        mode: str = 'all',
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        搜索并自动添加有效tokens到管理器
        
        Args:
            mode: 搜索模式
            max_results: 最大结果数
            
        Returns:
            操作结果
        """
        # 搜索并验证
        results = self.hunt_tokens(mode, validate=True, max_results=max_results)
        
        # 添加到管理器
        if results["valid_tokens"]:
            add_results = self.manager.add_tokens_batch(results["valid_tokens"], validate=False)
            results["add_results"] = add_results
        
        return results
    
    def search_user_tokens(self, username: str) -> List[str]:
        """
        搜索特定用户的tokens
        
        Args:
            username: GitHub用户名
            
        Returns:
            找到的token列表
        """
        logger.info(f"🔍 搜索用户 {username} 的tokens...")
        
        tokens = self.github_searcher.search_user_repos(username)
        
        if tokens:
            # 验证tokens
            valid_tokens = []
            for token in tokens:
                result = self.validator.validate(token)
                if result.valid:
                    valid_tokens.append(token)
            
            logger.info(f"✅ 找到 {len(valid_tokens)} 个有效tokens")
            
            if self.auto_save:
                self._save_valid_tokens(valid_tokens)
            
            return valid_tokens
        
        return []
    
    def search_org_tokens(self, org_name: str) -> List[str]:
        """
        搜索组织的tokens
        
        Args:
            org_name: 组织名称
            
        Returns:
            找到的token列表
        """
        logger.info(f"🔍 搜索组织 {org_name} 的tokens...")
        
        tokens = self.github_searcher.search_organization_repos(org_name)
        
        if tokens:
            # 验证tokens
            valid_tokens = []
            for token in tokens:
                result = self.validator.validate(token)
                if result.valid:
                    valid_tokens.append(token)
            
            logger.info(f"✅ 找到 {len(valid_tokens)} 个有效tokens")
            
            if self.auto_save:
                self._save_valid_tokens(valid_tokens)
            
            return valid_tokens
        
        return []
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Hunter状态
        
        Returns:
            状态信息
        """
        status = {
            "manager_status": self.manager.get_status(),
            "github_rate_limit": self.github_searcher.check_rate_limit(),
            "local_search_paths": len(self.local_searcher.search_paths),
            "auto_save": self.auto_save
        }
        
        return status
    
    def validate_existing_tokens(self) -> Dict[str, Any]:
        """
        验证管理器中的所有现有tokens
        
        Returns:
            验证结果
        """
        logger.info("🔐 验证所有现有tokens...")
        
        results = self.manager.validate_all_tokens()
        
        # 统计
        valid_count = sum(1 for r in results.values() if r.valid)
        invalid_count = len(results) - valid_count
        
        return {
            "total": len(results),
            "valid": valid_count,
            "invalid": invalid_count,
            "details": results
        }


def main():
    """测试和演示函数"""
    import json
    import os
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 从环境变量获取GitHub token（用于搜索）
    github_token = os.getenv("GITHUB_TOKEN")
    
    # 创建Hunter
    hunter = TokenHunter(
        github_token=github_token,
        tokens_file="test_tokens.txt",
        auto_save=True
    )
    
    # 显示状态
    print("\n=== Hunter状态 ===")
    status = hunter.get_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 搜索本地tokens
    print("\n=== 搜索本地tokens ===")
    local_results = hunter.hunt_tokens(mode='local', validate=True, max_results=10)
    
    print(f"找到tokens: {local_results['statistics']['total_found']}")
    print(f"有效tokens: {local_results['statistics'].get('valid_count', 0)}")
    print(f"无效tokens: {local_results['statistics'].get('invalid_count', 0)}")
    
    # 如果有GitHub token，也可以搜索GitHub
    if github_token:
        print("\n=== 搜索GitHub tokens ===")
        github_results = hunter.hunt_tokens(mode='github', validate=True, max_results=5)
        
        print(f"找到tokens: {github_results['statistics']['total_found']}")
        print(f"有效tokens: {github_results['statistics'].get('valid_count', 0)}")
    
    # 验证现有tokens
    print("\n=== 验证现有tokens ===")
    validation_results = hunter.validate_existing_tokens()
    print(f"总数: {validation_results['total']}")
    print(f"有效: {validation_results['valid']}")
    print(f"无效: {validation_results['invalid']}")


if __name__ == "__main__":
    main()