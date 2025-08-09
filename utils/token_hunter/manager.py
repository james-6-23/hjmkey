"""
GitHub Token 管理器
负责token的存储、循环使用和自动管理
"""

import os
import json
import threading
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from .validator import TokenValidator, TokenValidationResult

logger = logging.getLogger(__name__)


class NoValidTokenError(Exception):
    """没有可用token异常"""
    pass


class NoQuotaError(Exception):
    """所有token额度耗尽异常"""
    pass


class TokenManager:
    """
    GitHub Token 管理器
    实现token的循环使用、自动验证和失效管理
    """
    
    def __init__(self, tokens_file: str = "data/github_tokens.txt", auto_validate: bool = True):
        """
        初始化Token管理器
        
        Args:
            tokens_file: tokens存储文件路径
            auto_validate: 是否自动验证新添加的token
        """
        self.tokens_file = Path(tokens_file)
        self.auto_validate = auto_validate
        self.validator = TokenValidator()
        
        # 确保目录存在
        self.tokens_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Token列表和状态
        self.tokens: List[str] = []
        self.token_stats: Dict[str, Dict[str, Any]] = {}
        self.current_index = 0
        self.lock = threading.Lock()
        
        # 加载tokens
        self._load_tokens()
        
        # 统计文件路径
        self.stats_file = self.tokens_file.parent / "token_stats.json"
        self._load_stats()
        
        # 无效tokens记录文件
        self.invalid_tokens_file = self.tokens_file.parent / "invalid_tokens.txt"
        
        logger.info(f"📂 Token管理器初始化完成，加载了 {len(self.tokens)} 个tokens")
    
    def _load_tokens(self) -> None:
        """从文件加载tokens"""
        self.tokens = []
        
        if not self.tokens_file.exists():
            logger.warning(f"⚠️ Tokens文件不存在: {self.tokens_file}")
            # 创建空文件
            self.tokens_file.touch()
            return
        
        try:
            with open(self.tokens_file, 'r', encoding='utf-8') as f:
                for line in f:
                    token = line.strip()
                    # 跳过空行和注释
                    if token and not token.startswith('#'):
                        self.tokens.append(token)
            
            logger.info(f"✅ 从 {self.tokens_file} 加载了 {len(self.tokens)} 个tokens")
        except Exception as e:
            logger.error(f"❌ 加载tokens失败: {e}")
    
    def _save_tokens(self) -> None:
        """保存tokens到文件"""
        try:
            with open(self.tokens_file, 'w', encoding='utf-8') as f:
                f.write("# GitHub Tokens 列表\n")
                f.write(f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 总数: {len(self.tokens)}\n\n")
                
                for token in self.tokens:
                    f.write(f"{token}\n")
            
            logger.info(f"💾 保存了 {len(self.tokens)} 个tokens到 {self.tokens_file}")
        except Exception as e:
            logger.error(f"❌ 保存tokens失败: {e}")
    
    def _load_stats(self) -> None:
        """加载token统计信息"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.token_stats = json.load(f)
            except Exception as e:
                logger.error(f"❌ 加载统计信息失败: {e}")
                self.token_stats = {}
        else:
            self.token_stats = {}
    
    def _save_stats(self) -> None:
        """保存token统计信息"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.token_stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ 保存统计信息失败: {e}")
    
    def _update_token_stats(self, token: str, success: bool = True) -> None:
        """更新token使用统计"""
        token_key = token[:10] + "..." if len(token) > 10 else token
        
        if token_key not in self.token_stats:
            self.token_stats[token_key] = {
                "first_used": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "use_count": 0,
                "success_count": 0,
                "fail_count": 0
            }
        
        stats = self.token_stats[token_key]
        stats["last_used"] = datetime.now().isoformat()
        stats["use_count"] += 1
        
        if success:
            stats["success_count"] += 1
        else:
            stats["fail_count"] += 1
        
        # 定期保存统计
        if stats["use_count"] % 10 == 0:
            self._save_stats()
    
    def get_next_token(self) -> str:
        """
        获取下一个可用的token（循环使用）
        
        Returns:
            可用的GitHub token
            
        Raises:
            NoValidTokenError: 没有可用的token
            NoQuotaError: 所有token额度耗尽
        """
        with self.lock:
            if not self.tokens:
                raise NoValidTokenError("❌ 没有可用的GitHub tokens，请先添加tokens")
            
            # 记录尝试次数，避免无限循环
            attempts = 0
            tokens_with_quota = []
            
            while attempts < len(self.tokens):
                token = self.tokens[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.tokens)
                attempts += 1
                
                # 检查token额度
                logger.debug(f"🔍 检查token额度: {token[:10]}...")
                rate_limit = self.validator.check_rate_limit(token)
                
                if rate_limit:
                    if rate_limit.remaining > 0:
                        logger.info(f"✅ 使用token: {token[:10]}..., 剩余额度: {rate_limit.remaining}/{rate_limit.limit}")
                        self._update_token_stats(token, success=True)
                        return token
                    else:
                        logger.warning(f"⚠️ Token额度耗尽: {token[:10]}..., 重置时间: {rate_limit.reset.strftime('%Y-%m-%d %H:%M:%S')}")
                        tokens_with_quota.append((token, rate_limit.reset))
                else:
                    # Token可能无效，标记并继续
                    logger.warning(f"⚠️ Token可能无效: {token[:10]}...")
                    self._update_token_stats(token, success=False)
            
            # 所有token都没有额度
            if tokens_with_quota:
                # 找出最早恢复的token
                earliest_reset = min(tokens_with_quota, key=lambda x: x[1])
                reset_time = earliest_reset[1].strftime('%Y-%m-%d %H:%M:%S')
                raise NoQuotaError(f"❌ 所有 {len(self.tokens)} 个tokens额度已耗尽，最早将在 {reset_time} 恢复")
            else:
                raise NoValidTokenError(f"❌ 所有 {len(self.tokens)} 个tokens都无效或无法访问")
    
    def add_token(self, token: str, validate: bool = None) -> bool:
        """
        添加新token
        
        Args:
            token: GitHub token
            validate: 是否验证token（None时使用默认设置）
            
        Returns:
            是否添加成功
        """
        with self.lock:
            # 检查是否已存在
            if token in self.tokens:
                logger.info(f"ℹ️ Token已存在: {token[:10]}...")
                return False
            
            # 是否需要验证
            should_validate = validate if validate is not None else self.auto_validate
            
            if should_validate:
                logger.info(f"🔍 验证新token: {token[:10]}...")
                result = self.validator.validate(token)
                
                if not result.valid:
                    logger.warning(f"❌ Token验证失败: {result.reason}")
                    # 记录无效token
                    self._record_invalid_token(token, result.reason)
                    return False
                
                logger.info(f"✅ Token验证成功: 用户={result.user}, 额度={result.rate_limit.remaining if result.rate_limit else 'unknown'}")
            
            # 添加token
            self.tokens.append(token)
            self._save_tokens()
            
            # 初始化统计
            self._update_token_stats(token, success=True)
            
            logger.info(f"✅ 成功添加新token，当前共 {len(self.tokens)} 个tokens")
            return True
    
    def add_tokens_batch(self, tokens: List[str], validate: bool = None) -> Dict[str, bool]:
        """
        批量添加tokens
        
        Args:
            tokens: token列表
            validate: 是否验证
            
        Returns:
            添加结果字典 {token: success}
        """
        results = {}
        
        logger.info(f"📦 批量添加 {len(tokens)} 个tokens...")
        
        for token in tokens:
            results[token[:10] + "..."] = self.add_token(token, validate)
        
        # 统计结果
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"✅ 批量添加完成: {success_count}/{len(tokens)} 成功")
        
        return results
    
    def remove_token(self, token: str) -> bool:
        """
        移除token
        
        Args:
            token: 要移除的token
            
        Returns:
            是否移除成功
        """
        with self.lock:
            if token in self.tokens:
                self.tokens.remove(token)
                self._save_tokens()
                
                # 记录为无效token
                self._record_invalid_token(token, "手动移除")
                
                logger.info(f"🗑️ 移除token: {token[:10]}..., 剩余 {len(self.tokens)} 个tokens")
                return True
            
            logger.warning(f"⚠️ Token不存在: {token[:10]}...")
            return False
    
    def _record_invalid_token(self, token: str, reason: str) -> None:
        """记录无效token"""
        try:
            with open(self.invalid_tokens_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} | {token[:10]}... | {reason}\n")
        except Exception as e:
            logger.error(f"记录无效token失败: {e}")
    
    def validate_all_tokens(self) -> Dict[str, TokenValidationResult]:
        """
        验证所有tokens
        
        Returns:
            验证结果字典
        """
        logger.info(f"🔍 开始验证所有 {len(self.tokens)} 个tokens...")
        
        results = {}
        invalid_tokens = []
        
        for token in self.tokens:
            result = self.validator.validate(token)
            results[token[:10] + "..."] = result
            
            if not result.valid:
                invalid_tokens.append(token)
        
        # 移除无效tokens
        if invalid_tokens:
            logger.warning(f"⚠️ 发现 {len(invalid_tokens)} 个无效tokens，将自动移除")
            for token in invalid_tokens:
                self.remove_token(token)
        
        # 统计
        valid_count = sum(1 for r in results.values() if r.valid)
        logger.info(f"✅ 验证完成: {valid_count}/{len(results)} 个有效tokens")
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取管理器状态
        
        Returns:
            状态信息字典
        """
        status = {
            "total_tokens": len(self.tokens),
            "current_index": self.current_index,
            "tokens_file": str(self.tokens_file),
            "auto_validate": self.auto_validate,
            "stats": {}
        }
        
        # 检查每个token的额度
        for i, token in enumerate(self.tokens):
            rate_limit = self.validator.check_rate_limit(token)
            token_key = f"token_{i+1}"
            
            if rate_limit:
                status["stats"][token_key] = {
                    "remaining": rate_limit.remaining,
                    "limit": rate_limit.limit,
                    "usage": f"{rate_limit.usage_percentage:.1f}%",
                    "reset": rate_limit.reset.strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                status["stats"][token_key] = {"status": "unknown"}
        
        return status
    
    def rotate_token(self) -> str:
        """
        强制轮换到下一个token
        
        Returns:
            下一个token
        """
        with self.lock:
            if not self.tokens:
                raise NoValidTokenError("没有可用的tokens")
            
            self.current_index = (self.current_index + 1) % len(self.tokens)
            token = self.tokens[self.current_index]
            
            logger.info(f"🔄 轮换到token: {token[:10]}... (索引: {self.current_index})")
            return token
    
    def clear_all_tokens(self) -> None:
        """清空所有tokens（谨慎使用）"""
        with self.lock:
            count = len(self.tokens)
            self.tokens = []
            self.current_index = 0
            self._save_tokens()
            
            logger.warning(f"🗑️ 已清空所有 {count} 个tokens")


def main():
    """测试函数"""
    # 创建管理器
    manager = TokenManager("test_tokens.txt")
    
    # 添加测试token
    test_token = os.getenv("GITHUB_TOKEN")
    if test_token:
        success = manager.add_token(test_token)
        print(f"添加token: {'成功' if success else '失败'}")
    
    # 获取状态
    status = manager.get_status()
    print(f"管理器状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
    
    # 获取下一个token
    try:
        token = manager.get_next_token()
        print(f"获取到token: {token[:10]}...")
    except (NoValidTokenError, NoQuotaError) as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()