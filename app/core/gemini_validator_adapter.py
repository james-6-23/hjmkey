"""
Gemini Validator V2 适配器
将 utils/gemini_key_validator_v2.py 集成到 orchestrator 中
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.gemini_key_validator_v2 import (
    GeminiKeyValidatorV2, 
    ValidatorConfig, 
    KeyTier,
    ValidatedKey
)
from app.core.validator import ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class GeminiValidationResult(ValidationResult):
    """扩展的验证结果，包含更多信息"""
    tier: Optional[KeyTier] = None
    error_message: Optional[str] = None


class GeminiValidatorAdapter:
    """
    适配器类，将 GeminiKeyValidatorV2 适配到 orchestrator 的接口
    """
    
    def __init__(self, config: Optional[ValidatorConfig] = None):
        """
        初始化适配器
        
        Args:
            config: 验证器配置
        """
        # 默认配置，优化性能
        if config is None:
            config = ValidatorConfig(
                concurrency=50,  # 高并发
                timeout_sec=15,
                max_retries=2,
                enable_http2=True,
                log_level="INFO"
            )
        
        self.config = config
        self.validator = None
        logger.info(f"✅ GeminiValidatorAdapter initialized with concurrency={config.concurrency}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.validator = GeminiKeyValidatorV2(self.config)
        await self.validator.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.validator:
            await self.validator.__aexit__(exc_type, exc_val, exc_tb)
    
    def validate_batch(self, keys: List[str]) -> List[ValidationResult]:
        """
        同步批量验证（兼容旧接口）
        
        Args:
            keys: 密钥列表
            
        Returns:
            验证结果列表
        """
        # 在新的事件循环中运行异步验证
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.validate_batch_async(keys))
        finally:
            loop.close()
    
    async def validate_batch_async(self, keys: List[str]) -> List[GeminiValidationResult]:
        """
        异步批量验证密钥
        
        Args:
            keys: 密钥列表
            
        Returns:
            验证结果列表
        """
        if not self.validator:
            async with GeminiKeyValidatorV2(self.config) as validator:
                return await self._do_validation(validator, keys)
        else:
            return await self._do_validation(self.validator, keys)
    
    async def _do_validation(self, validator: GeminiKeyValidatorV2, 
                           keys: List[str]) -> List[GeminiValidationResult]:
        """
        执行实际的验证
        
        Args:
            validator: 验证器实例
            keys: 密钥列表
            
        Returns:
            验证结果列表
        """
        # 批量验证
        stats = await validator.validate_keys_batch(keys, show_progress=False)
        
        # 转换结果格式
        results = []
        for validated_key in validator.validated_keys:
            # 判断验证状态
            if validated_key.tier == KeyTier.INVALID:
                result = GeminiValidationResult(
                    key=validated_key.key,
                    is_valid=False,
                    is_rate_limited=False,
                    tier=validated_key.tier,
                    error_message=validated_key.error_message
                )
            elif validated_key.tier in [KeyTier.FREE, KeyTier.PAID]:
                # 检查是否因为速率限制而被标记为有效
                # 根据错误信息判断
                is_rate_limited = (validated_key.error_message and 
                                 "429" in str(validated_key.error_message))
                
                result = GeminiValidationResult(
                    key=validated_key.key,
                    is_valid=True,
                    is_rate_limited=is_rate_limited,
                    tier=validated_key.tier,
                    error_message=validated_key.error_message
                )
            else:
                # 默认情况
                result = GeminiValidationResult(
                    key=validated_key.key,
                    is_valid=False,
                    is_rate_limited=False,
                    tier=validated_key.tier,
                    error_message=validated_key.error_message
                )
            
            results.append(result)
        
        # 记录统计信息
        logger.info(f"📊 Validation completed: {stats['valid']}/{stats['total']} valid "
                   f"({stats['paid']} paid, {stats['free']} free) - "
                   f"{stats['keys_per_second']:.1f} keys/sec")
        
        return results
    
    def check_if_paid_key(self, key: str) -> bool:
        """
        检查是否为付费密钥（从验证结果中获取）
        
        Args:
            key: 密钥
            
        Returns:
            是否为付费密钥
        """
        # 查找已验证的密钥
        if self.validator and self.validator.validated_keys:
            for validated_key in self.validator.validated_keys:
                if validated_key.key == key:
                    return validated_key.tier == KeyTier.PAID
        
        # 如果没有找到，返回False
        return False


class OptimizedOrchestratorValidator:
    """
    为 Orchestrator 优化的验证器包装类
    提供简单的接口和自动的上下文管理
    """
    
    def __init__(self, concurrency: int = 50):
        """
        初始化优化的验证器
        
        Args:
            concurrency: 并发数
        """
        self.config = ValidatorConfig(
            concurrency=concurrency,
            timeout_sec=15,
            max_retries=2,
            enable_http2=True,
            log_level="INFO"
        )
        self.adapter = None
        self._context_manager = None
    
    async def _ensure_initialized(self):
        """确保验证器已初始化"""
        if self.adapter is None:
            self.adapter = GeminiValidatorAdapter(self.config)
            self._context_manager = await self.adapter.__aenter__()
    
    async def validate_batch_async(self, keys: List[str]) -> List[GeminiValidationResult]:
        """
        异步批量验证
        
        Args:
            keys: 密钥列表
            
        Returns:
            验证结果列表
        """
        await self._ensure_initialized()
        return await self.adapter.validate_batch_async(keys)
    
    def validate_batch(self, keys: List[str]) -> List[ValidationResult]:
        """
        同步批量验证（兼容接口）
        
        Args:
            keys: 密钥列表
            
        Returns:
            验证结果列表
        """
        # 创建临时适配器
        adapter = GeminiValidatorAdapter(self.config)
        return adapter.validate_batch(keys)
    
    async def cleanup(self):
        """清理资源"""
        if self.adapter and self._context_manager:
            await self.adapter.__aexit__(None, None, None)
            self.adapter = None
            self._context_manager = None
    
    def __del__(self):
        """析构函数，确保资源清理"""
        if self.adapter:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.cleanup())
                else:
                    loop.run_until_complete(self.cleanup())
            except:
                pass


# 便捷函数
def create_gemini_validator(concurrency: int = 50) -> OptimizedOrchestratorValidator:
    """
    创建优化的 Gemini 验证器
    
    Args:
        concurrency: 并发数
        
    Returns:
        验证器实例
    """
    return OptimizedOrchestratorValidator(concurrency=concurrency)


# 示例用法
async def example_usage():
    """示例用法"""
    # 创建验证器
    validator = create_gemini_validator(concurrency=100)
    
    # 测试密钥
    test_keys = [
        "AIzaSyA1234567890abcdefghijklmnopqrstuv",
        "AIzaSyB1234567890abcdefghijklmnopqrstuv",
        "invalid_key_format",
    ]
    
    # 异步验证
    results = await validator.validate_batch_async(test_keys)
    
    # 显示结果
    for result in results:
        status = "VALID" if result.is_valid else "INVALID"
        tier = result.tier.value if result.tier else "unknown"
        print(f"{result.key[:20]}... - {status} ({tier})")
    
    # 清理资源
    await validator.cleanup()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())