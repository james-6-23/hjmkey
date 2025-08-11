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
    
    def __post_init__(self):
        """处理兼容性问题 - 统一参数接口"""
        # 确保所有必需的属性都存在
        if not hasattr(self, 'key'):
            self.key = None
            
        # 处理 is_valid 参数兼容性
        if hasattr(self, 'is_valid') and self.is_valid is not None:
            pass  # 已经设置了
        else:
            # 根据 tier 推断 is_valid
            self.is_valid = self.tier in [KeyTier.FREE, KeyTier.PAID] if self.tier else False
        
        # 确保 is_rate_limited 属性存在
        if not hasattr(self, 'is_rate_limited'):
            self.is_rate_limited = False
            # 从错误信息推断是否被限流
            if self.error_message:
                error_lower = str(self.error_message).lower()
                self.is_rate_limited = any(keyword in error_lower for keyword in ['429', 'rate', 'limit', 'quota'])
        
        # 添加向后兼容的属性
        if not hasattr(self, 'status'):
            # 为了兼容旧代码，添加 status 属性
            if self.is_valid:
                self.status = 'VALID_PAID' if self.tier == KeyTier.PAID else 'VALID_FREE'
            elif self.is_rate_limited:
                self.status = 'RATE_LIMITED'
            else:
                self.status = 'INVALID'
        
        # 添加 message 属性（兼容旧接口）
        if not hasattr(self, 'message'):
            if self.error_message:
                self.message = str(self.error_message)
            elif self.is_valid:
                tier_str = 'PAID' if self.tier == KeyTier.PAID else 'FREE'
                self.message = f"Valid {tier_str} key"
            else:
                self.message = "Invalid key"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于序列化）"""
        return {
            'key': self.key,
            'is_valid': self.is_valid,
            'is_rate_limited': self.is_rate_limited,
            'tier': self.tier.value if self.tier else None,
            'error_message': self.error_message,
            'status': self.status,
            'message': self.message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeminiValidationResult':
        """从字典创建实例（用于反序列化）"""
        # 处理 tier 枚举
        tier = None
        if 'tier' in data and data['tier']:
            try:
                tier = KeyTier(data['tier'])
            except:
                tier = None
        
        return cls(
            key=data.get('key'),
            is_valid=data.get('is_valid', False),
            is_rate_limited=data.get('is_rate_limited', False),
            tier=tier,
            error_message=data.get('error_message')
        )


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
        修复：每次都创建新的验证器实例，避免Session重用问题
        
        Args:
            keys: 密钥列表
            
        Returns:
            验证结果列表
        """
        # 总是创建新的验证器实例，确保Session是新的
        async with GeminiKeyValidatorV2(self.config) as validator:
            return await self._do_validation(validator, keys)
    
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
            is_valid = validated_key.tier in [KeyTier.FREE, KeyTier.PAID]
            is_rate_limited = (validated_key.error_message and
                             ("429" in str(validated_key.error_message) or
                              "rate" in str(validated_key.error_message).lower()))
            
            # 创建统一格式的验证结果
            result = GeminiValidationResult(
                key=validated_key.key,
                is_valid=is_valid,
                is_rate_limited=is_rate_limited,
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
    修复了Session管理问题
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
        self._session = None
        self._connector = None
        logger.info(f"✅ OptimizedOrchestratorValidator initialized with concurrency={concurrency}")
    
    async def _ensure_initialized(self):
        """确保验证器和Session已初始化"""
        # 每次都创建新的adapter，避免Session重用问题
        if self.adapter is None:
            self.adapter = GeminiValidatorAdapter(self.config)
    
    async def validate_batch_async(self, keys: List[str]) -> List[GeminiValidationResult]:
        """
        异步批量验证
        
        Args:
            keys: 密钥列表
            
        Returns:
            验证结果列表
        """
        # 每次验证都使用新的adapter实例，确保Session是新的
        adapter = GeminiValidatorAdapter(self.config)
        return await adapter.validate_batch_async(keys)
    
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
        results = adapter.validate_batch(keys)
        
        # 确保返回的是标准 ValidationResult 类型
        # 这样可以兼容期望基类的代码
        return [self._ensure_compatibility(r) for r in results]
    
    def _ensure_compatibility(self, result: GeminiValidationResult) -> ValidationResult:
        """
        确保结果兼容基类接口
        
        Args:
            result: Gemini验证结果
            
        Returns:
            兼容的验证结果
        """
        # 如果已经是基类，直接返回
        if type(result) == ValidationResult:
            return result
        
        # 转换为基类格式
        base_result = ValidationResult(
            key=result.key,
            is_valid=result.is_valid,
            is_rate_limited=result.is_rate_limited
        )
        
        # 复制额外属性
        if hasattr(result, 'status'):
            base_result.status = result.status
        if hasattr(result, 'message'):
            base_result.message = result.message
            
        return base_result
    
    async def cleanup(self):
        """清理资源"""
        # 清理adapter
        if self.adapter:
            try:
                if hasattr(self.adapter, '__aexit__'):
                    await self.adapter.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error cleaning up adapter: {e}")
            finally:
                self.adapter = None
        
        # 清理session
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            finally:
                self._session = None
        
        # 清理connector
        if self._connector:
            try:
                await self._connector.close()
            except Exception as e:
                logger.error(f"Error closing connector: {e}")
            finally:
                self._connector = None


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