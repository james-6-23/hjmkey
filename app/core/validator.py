"""
密钥验证器模块
负责验证API密钥的有效性
"""

import os
import time
import random
import logging
from typing import Optional, List, Dict, Any, Protocol
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """验证状态枚举"""
    VALID = "valid"
    INVALID = "invalid"
    RATE_LIMITED = "rate_limited"
    SERVICE_DISABLED = "service_disabled"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ValidationResult:
    """验证结果数据类"""
    key: str
    status: ValidationStatus
    message: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: float = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
    
    @property
    def is_valid(self) -> bool:
        """是否为有效密钥"""
        return self.status == ValidationStatus.VALID
    
    @property
    def is_rate_limited(self) -> bool:
        """是否被限流"""
        return self.status == ValidationStatus.RATE_LIMITED


class IKeyValidator(Protocol):
    """密钥验证器接口"""
    
    def validate(self, key: str) -> ValidationResult:
        """验证单个密钥"""
        ...
    
    def validate_batch(self, keys: List[str]) -> List[ValidationResult]:
        """批量验证密钥"""
        ...


class BaseKeyValidator(ABC):
    """密钥验证器基类"""
    
    def __init__(self, delay_range: tuple = (0.5, 1.5)):
        """
        初始化验证器
        
        Args:
            delay_range: 验证延迟范围（秒）
        """
        self.delay_range = delay_range
        self.validation_count = 0
        self.error_count = 0
        
    @abstractmethod
    def validate(self, key: str) -> ValidationResult:
        """
        验证单个密钥
        
        Args:
            key: API密钥
            
        Returns:
            验证结果
        """
        pass
    
    def validate_batch(self, keys: List[str]) -> List[ValidationResult]:
        """
        批量验证密钥
        
        Args:
            keys: API密钥列表
            
        Returns:
            验证结果列表
        """
        results = []
        for key in keys:
            # 添加随机延迟以避免触发限流
            time.sleep(random.uniform(*self.delay_range))
            result = self.validate(key)
            results.append(result)
            
            # 更新统计
            self.validation_count += 1
            if result.status in [ValidationStatus.NETWORK_ERROR, ValidationStatus.UNKNOWN_ERROR]:
                self.error_count += 1
                
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        return {
            "total_validations": self.validation_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.validation_count)
        }


class GeminiKeyValidator(BaseKeyValidator):
    """
    Gemini API密钥验证器
    """
    
    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        proxy_config: Optional[Dict[str, str]] = None,
        delay_range: tuple = (0.5, 1.5)
    ):
        """
        初始化Gemini验证器
        
        Args:
            model_name: 用于验证的模型名称
            proxy_config: 代理配置
            delay_range: 验证延迟范围
        """
        super().__init__(delay_range)
        self.model_name = model_name
        self.proxy_config = proxy_config
        self.api_endpoint = "generativelanguage.googleapis.com"
        
    def validate(self, key: str) -> ValidationResult:
        """
        验证Gemini API密钥
        
        Args:
            key: API密钥
            
        Returns:
            验证结果
        """
        try:
            # 配置代理（如果有）
            if self.proxy_config and 'http' in self.proxy_config:
                os.environ['grpc_proxy'] = self.proxy_config['http']
            
            # 配置Gemini客户端
            client_options = {
                "api_endpoint": self.api_endpoint
            }
            
            genai.configure(
                api_key=key,
                client_options=client_options,
            )
            
            # 尝试使用密钥进行简单调用
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content("hi")
            
            # 如果成功，返回有效结果
            return ValidationResult(
                key=key,
                status=ValidationStatus.VALID,
                message="Key validated successfully"
            )
            
        except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated) as e:
            return ValidationResult(
                key=key,
                status=ValidationStatus.INVALID,
                message="Invalid or unauthorized key",
                error_code="AUTH_ERROR"
            )
            
        except google_exceptions.TooManyRequests as e:
            return ValidationResult(
                key=key,
                status=ValidationStatus.RATE_LIMITED,
                message="Rate limit exceeded",
                error_code="RATE_LIMIT"
            )
            
        except Exception as e:
            error_str = str(e)
            
            # 分析错误类型
            if "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower():
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.RATE_LIMITED,
                    message="Rate limit or quota exceeded",
                    error_code="RATE_LIMIT_429"
                )
            elif "403" in error_str or "SERVICE_DISABLED" in error_str or "API has not been used" in error_str:
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.SERVICE_DISABLED,
                    message="Service disabled or not enabled",
                    error_code="SERVICE_DISABLED"
                )
            elif "network" in error_str.lower() or "connection" in error_str.lower():
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.NETWORK_ERROR,
                    message=f"Network error: {error_str[:100]}",
                    error_code="NETWORK_ERROR"
                )
            else:
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.UNKNOWN_ERROR,
                    message=f"Unknown error: {error_str[:100]}",
                    error_code=e.__class__.__name__
                )
        finally:
            # 清理环境变量
            if 'grpc_proxy' in os.environ:
                del os.environ['grpc_proxy']


class MockKeyValidator(BaseKeyValidator):
    """
    模拟密钥验证器（用于测试）
    """
    
    def __init__(self, valid_keys: Optional[List[str]] = None):
        """
        初始化模拟验证器
        
        Args:
            valid_keys: 预定义的有效密钥列表
        """
        super().__init__(delay_range=(0, 0))  # 测试时无延迟
        self.valid_keys = set(valid_keys or [])
        
    def validate(self, key: str) -> ValidationResult:
        """
        模拟验证密钥
        
        Args:
            key: API密钥
            
        Returns:
            验证结果
        """
        if key in self.valid_keys:
            return ValidationResult(
                key=key,
                status=ValidationStatus.VALID,
                message="Mock validation: valid key"
            )
        else:
            return ValidationResult(
                key=key,
                status=ValidationStatus.INVALID,
                message="Mock validation: invalid key"
            )
    
    def add_valid_key(self, key: str) -> None:
        """添加有效密钥到模拟器"""
        self.valid_keys.add(key)
        
    def remove_valid_key(self, key: str) -> None:
        """从模拟器移除有效密钥"""
        self.valid_keys.discard(key)


class KeyValidatorFactory:
    """密钥验证器工厂"""
    
    _validators: Dict[str, type] = {
        "gemini": GeminiKeyValidator,
        "mock": MockKeyValidator,
    }
    
    @classmethod
    def create(cls, validator_type: str, **kwargs) -> BaseKeyValidator:
        """
        创建验证器实例
        
        Args:
            validator_type: 验证器类型
            **kwargs: 验证器配置参数
            
        Returns:
            验证器实例
            
        Raises:
            ValueError: 如果验证器类型不支持
        """
        if validator_type not in cls._validators:
            raise ValueError(f"Unsupported validator type: {validator_type}")
            
        validator_class = cls._validators[validator_type]
        return validator_class(**kwargs)
    
    @classmethod
    def register(cls, name: str, validator_class: type) -> None:
        """
        注册新的验证器类型
        
        Args:
            name: 验证器名称
            validator_class: 验证器类
        """
        cls._validators[name] = validator_class
    
    @classmethod
    def list_types(cls) -> List[str]:
        """获取支持的验证器类型列表"""
        return list(cls._validators.keys())


# 默认验证器别名
KeyValidator = GeminiKeyValidator