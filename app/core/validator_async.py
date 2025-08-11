"""
异步密钥验证器模块
实现真正的并发验证以提高性能
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from app.core.validator import ValidationResult, ValidationStatus, BaseKeyValidator

logger = logging.getLogger(__name__)


class AsyncGeminiKeyValidator(BaseKeyValidator):
    """
    异步Gemini API密钥验证器
    支持真正的并发验证
    """
    
    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",  # 使用更稳定的模型
        proxy_config: Optional[Dict[str, str]] = None,
        delay_range: tuple = (0.5, 1.0),  # 增加延迟避免限流
        max_concurrent: int = 5,  # 降低并发数避免限流
        max_retries: int = 3  # 添加重试机制
    ):
        """
        初始化异步验证器
        
        Args:
            model_name: 用于验证的模型名称
            proxy_config: 代理配置
            delay_range: 验证延迟范围
            max_concurrent: 最大并发验证数
            max_retries: 最大重试次数
        """
        super().__init__(delay_range)
        self.model_name = model_name
        self.proxy_config = proxy_config
        self.api_endpoint = "generativelanguage.googleapis.com"
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 添加速率限制跟踪
        self._last_request_time = {}
        self._min_request_interval = 0.5  # 每个密钥最小请求间隔
        
    def validate(self, key: str, retry_count: int = 0) -> ValidationResult:
        """同步验证单个密钥（保持兼容性）"""
        try:
            # 速率限制检查
            current_time = time.time()
            if key in self._last_request_time:
                elapsed = current_time - self._last_request_time[key]
                if elapsed < self._min_request_interval:
                    time.sleep(self._min_request_interval - elapsed)
            self._last_request_time[key] = current_time
            
            # 配置Gemini客户端
            genai.configure(
                api_key=key,
                client_options={"api_endpoint": self.api_endpoint}
            )
            
            # 尝试使用密钥进行简单调用
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                "Hello",  # 使用更友好的测试内容
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1,
                    temperature=0,
                    candidate_count=1
                ),
                safety_settings={
                    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
                }
            )
            
            # 检查是否是付费密钥（基于模型访问）
            is_paid = False
            try:
                # 尝试使用付费模型
                paid_model = genai.GenerativeModel("gemini-1.5-pro")
                paid_response = paid_model.generate_content(
                    "1",
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1,
                        temperature=0
                    )
                )
                is_paid = True
            except:
                pass
            
            return ValidationResult(
                key=key,
                status=ValidationStatus.VALID_PAID if is_paid else ValidationStatus.VALID,
                message="Key validated successfully" + (" (PAID)" if is_paid else " (FREE)")
            )
            
        except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated):
            return ValidationResult(
                key=key,
                status=ValidationStatus.INVALID,
                message="Invalid or unauthorized key",
                error_code="AUTH_ERROR"
            )
            
        except google_exceptions.TooManyRequests:
            # 重试机制
            if retry_count < self.max_retries:
                wait_time = (2 ** retry_count) * 1.0  # 指数退避
                logger.debug(f"Rate limited, retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self.validate(key, retry_count + 1)
            
            return ValidationResult(
                key=key,
                status=ValidationStatus.RATE_LIMITED,
                message="Rate limit exceeded after retries",
                error_code="RATE_LIMIT"
            )
            
        except Exception as e:
            error_str = str(e)
            
            # 更详细的错误分类
            if "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower():
                # 重试机制
                if retry_count < self.max_retries:
                    wait_time = (2 ** retry_count) * 1.5
                    logger.debug(f"Rate limit error, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    return self.validate(key, retry_count + 1)
                    
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.RATE_LIMITED,
                    message="Rate limit exceeded",
                    error_code="RATE_LIMIT_429"
                )
            elif "403" in error_str or "SERVICE_DISABLED" in error_str:
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.SERVICE_DISABLED,
                    message="Service disabled for this key",
                    error_code="SERVICE_DISABLED"
                )
            elif "401" in error_str or "invalid" in error_str.lower() or "unauthorized" in error_str.lower():
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.INVALID,
                    message="Invalid API key",
                    error_code="INVALID_KEY"
                )
            elif "network" in error_str.lower() or "connection" in error_str.lower():
                # 网络错误重试
                if retry_count < self.max_retries:
                    wait_time = 2.0
                    logger.debug(f"Network error, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    return self.validate(key, retry_count + 1)
                    
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.NETWORK_ERROR,
                    message=f"Network error: {error_str[:100]}",
                    error_code="NETWORK_ERROR"
                )
            else:
                logger.debug(f"Unknown error for key {key[:10]}...: {error_str}")
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.UNKNOWN_ERROR,
                    message=f"Error: {error_str[:100]}",
                    error_code=e.__class__.__name__
                )
    
    async def validate_async(self, key: str) -> ValidationResult:
        """异步验证单个密钥"""
        loop = asyncio.get_event_loop()
        
        # 使用信号量限制并发
        async with self._semaphore:
            # 在线程池中运行同步验证
            result = await loop.run_in_executor(
                self._executor,
                self.validate,
                key
            )
            
            # 动态延迟以避免过快的请求
            delay = 0.5 if result.status == ValidationStatus.VALID else 1.0
            await asyncio.sleep(delay)
            
            return result
    
    async def validate_batch_async(self, keys: List[str]) -> List[ValidationResult]:
        """
        异步批量验证密钥（真正的并发）
        
        Args:
            keys: API密钥列表
            
        Returns:
            验证结果列表
        """
        start_time = time.time()
        
        # 创建所有验证任务
        tasks = [self.validate_async(key) for key in keys]
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常情况
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 如果验证过程出错，返回错误结果
                final_results.append(ValidationResult(
                    key=keys[i],
                    status=ValidationStatus.UNKNOWN_ERROR,
                    message=f"Validation error: {str(result)}",
                    error_code="VALIDATION_ERROR"
                ))
            else:
                final_results.append(result)
                
        # 更新统计
        self.validation_count += len(keys)
        for result in final_results:
            if result.status in [ValidationStatus.NETWORK_ERROR, ValidationStatus.UNKNOWN_ERROR]:
                self.error_count += 1
        
        elapsed = time.time() - start_time
        logger.info(f"⚡ Validated {len(keys)} keys in {elapsed:.2f}s ({len(keys)/elapsed:.1f} keys/sec)")
        
        return final_results
    
    def validate_batch(self, keys: List[str]) -> List[ValidationResult]:
        """
        同步接口的批量验证（内部使用异步）
        
        Args:
            keys: API密钥列表
            
        Returns:
            验证结果列表
        """
        # 创建新的事件循环或使用现有的
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，创建任务
            task = asyncio.create_task(self.validate_batch_async(keys))
            return asyncio.run_coroutine_threadsafe(task, loop).result()
        except RuntimeError:
            # 如果没有运行的事件循环，创建新的
            return asyncio.run(self.validate_batch_async(keys))
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)


class OptimizedKeyValidator:
    """
    优化的密钥验证器包装器
    自动选择最佳验证策略
    """
    
    def __init__(self, base_validator: Optional[BaseKeyValidator] = None):
        """
        初始化优化验证器
        
        Args:
            base_validator: 基础验证器实例
        """
        self.validator = base_validator or AsyncGeminiKeyValidator()
        
    def validate(self, key: str) -> ValidationResult:
        """验证单个密钥"""
        return self.validator.validate(key)
    
    def validate_batch(self, keys: List[str]) -> List[ValidationResult]:
        """
        批量验证密钥（自动优化）
        
        Args:
            keys: API密钥列表
            
        Returns:
            验证结果列表
        """
        if len(keys) == 0:
            return []
        
        if len(keys) == 1:
            # 单个密钥直接验证
            return [self.validator.validate(keys[0])]
        
        # 多个密钥使用批量验证
        if isinstance(self.validator, AsyncGeminiKeyValidator):
            # 使用异步验证器的优化批量验证
            return self.validator.validate_batch(keys)
        else:
            # 使用基础验证器的串行验证
            return self.validator.validate_batch(keys)
    
    async def validate_batch_async(self, keys: List[str]) -> List[ValidationResult]:
        """
        异步批量验证（如果验证器支持）
        
        Args:
            keys: API密钥列表
            
        Returns:
            验证结果列表
        """
        if hasattr(self.validator, 'validate_batch_async'):
            return await self.validator.validate_batch_async(keys)
        else:
            # 降级到同步验证
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.validator.validate_batch,
                keys
            )